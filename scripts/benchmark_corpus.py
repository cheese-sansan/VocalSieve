"""Run reproducible private-corpus performance and recovery benchmarks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from vocalsieve.domain import AUDIO_EXTENSIONS, JobStatus, PipelineConfig, RuntimePolicy, Stage
from vocalsieve.events import EventType, PipelineEvent
from vocalsieve.service import VocalSieveService


@dataclass(slots=True)
class BenchmarkResult:
    file_count: int
    elapsed_seconds: float
    peak_rss_bytes: int
    database_bytes: int
    total_audio_seconds: float
    files_per_second: float
    selected_count: int
    error_count: int
    source_hashes_unchanged: bool | None
    resume_verified: bool | None
    stage_seconds: dict[str, float]


def discover_audio_files(source: Path) -> list[Path]:
    files = [
        path
        for path in source.rglob("*")
        if path.is_file() and path.suffix.casefold() in AUDIO_EXTENSIONS
    ]
    return sorted(
        files,
        key=lambda path: hashlib.sha256(
            path.relative_to(source).as_posix().encode("utf-8")
        ).hexdigest(),
    )


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def current_rss_bytes() -> int:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        process = ctypes.windll.kernel32.GetCurrentProcess()  # pyright: ignore[reportAttributeAccessIssue]
        success = ctypes.windll.psapi.GetProcessMemoryInfo(  # pyright: ignore[reportAttributeAccessIssue]
            process, ctypes.byref(counters), counters.cb
        )
        return int(counters.WorkingSetSize) if success else 0

    import resource

    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def stage_files(source: Path, files: list[Path], staging: Path) -> None:
    for source_path in files:
        destination = staging / source_path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(source_path, destination)
        except OSError:
            shutil.copy2(source_path, destination)


def database_size(path: Path) -> int:
    return sum(
        candidate.stat().st_size
        for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm"))
        if candidate.is_file()
    )


def run_screening(
    service: VocalSieveService,
    config: PipelineConfig,
    *,
    cancel_at: float | None = None,
) -> tuple[str, float, int, dict[str, float], bool]:
    job = service.create_job(config)
    stop = threading.Event()
    peak = current_rss_bytes()
    stage_started: tuple[str, float] | None = None
    stage_seconds: dict[str, float] = {}
    cancel_requested = False

    def sample_memory() -> None:
        nonlocal peak
        while not stop.wait(0.1):
            peak = max(peak, current_rss_bytes())

    def sink(event: PipelineEvent) -> None:
        nonlocal cancel_requested, stage_started
        if event.type == EventType.STAGE_STARTED and event.stage:
            now = time.perf_counter()
            if stage_started:
                stage_seconds[stage_started[0]] = now - stage_started[1]
            stage_started = (str(event.stage), now)
        if (
            cancel_at is not None
            and not cancel_requested
            and event.stage == Stage.PHYSICS
            and event.current is not None
            and event.total
            and event.current / event.total >= cancel_at
        ):
            cancel_requested = True
            service.cancel_job(job.id)

    sampler = threading.Thread(target=sample_memory, daemon=True)
    sampler.start()
    started = time.perf_counter()
    try:
        completed = service.run_job(job.id, sink)
        resumed = False
        if cancel_requested and completed.status == JobStatus.CANCELLED:
            completed = service.resume_job(job.id, sink)
            resumed = True
        if completed.status != JobStatus.COMPLETED:
            raise RuntimeError(f"Benchmark job ended in {completed.status.value}")
        finished = time.perf_counter()
        if stage_started:
            stage_seconds[stage_started[0]] = finished - stage_started[1]
        return job.id, finished - started, peak, stage_seconds, resumed
    finally:
        stop.set()
        sampler.join(timeout=2)


def selected_paths(service: VocalSieveService, job_id: str) -> set[str]:
    return {
        result.relative_path
        for result in service.query_results(job_id)
        if result.effective_selected
    }


def safe_remove_staging(staging: Path, run_root: Path) -> None:
    resolved = staging.resolve()
    root = run_root.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"Refusing to remove staging outside benchmark run: {resolved}")
    shutil.rmtree(resolved)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sizes", type=int, nargs="+", default=[1_000, 10_000, 50_000])
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--language", default="auto")
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--physics-workers", type=int, default=4)
    parser.add_argument("--skip-source-hashes", action="store_true")
    parser.add_argument("--verify-resume", action="store_true")
    parser.add_argument("--keep-staging", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"Source directory does not exist: {source}")
    sizes = sorted(set(args.sizes))
    if not sizes or sizes[0] < 1:
        raise SystemExit("Benchmark sizes must be positive")
    files = discover_audio_files(source)
    if len(files) < sizes[-1]:
        raise SystemExit(f"Need {sizes[-1]} audio files, found {len(files)}")

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_root = output / f"benchmark-{run_id}"
    run_root.mkdir(parents=True, exist_ok=False)
    results: list[BenchmarkResult] = []
    for size in sizes:
        chosen = files[:size]
        manifest = [path.relative_to(source).as_posix() for path in chosen]
        (run_root / f"private-manifest-{size}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        before = {path: file_digest(path) for path in chosen} if not args.skip_source_hashes else {}
        staging = run_root / "staging" / str(size)
        stage_files(source, chosen, staging)
        database_path = run_root / f"state-{size}.db"
        service = VocalSieveService(database_path, RuntimePolicy(1, 1))
        config = PipelineConfig(
            source_dir=str(staging),
            output_dir=str(run_root / "results" / str(size) / "main"),
            model_size=args.model,
            device=args.device,
            compute_type=args.compute_type,
            language=args.language,
            top_n=args.top_n,
            physics_workers=args.physics_workers,
        )
        try:
            job_id, elapsed, peak, stage_seconds, _ = run_screening(service, config)
            main_selected = selected_paths(service, job_id)
            resume_verified: bool | None = None
            if args.verify_resume and size == sizes[0]:
                recovery_config = PipelineConfig(
                    **{
                        **config.to_dict(),
                        "output_dir": str(run_root / "results" / str(size) / "recovery"),
                    }
                )
                recovery_id, _, recovery_peak, _, resumed = run_screening(
                    service, recovery_config, cancel_at=0.25
                )
                peak = max(peak, recovery_peak)
                resume_verified = resumed and selected_paths(service, recovery_id) == main_selected
            rows = service.query_results(job_id)
            unchanged = (
                all(file_digest(path) == digest for path, digest in before.items())
                if before
                else None
            )
            total_audio_seconds = sum(result.duration or 0.0 for result in rows)
            results.append(
                BenchmarkResult(
                    file_count=size,
                    elapsed_seconds=elapsed,
                    peak_rss_bytes=peak,
                    database_bytes=database_size(database_path),
                    total_audio_seconds=total_audio_seconds,
                    files_per_second=size / elapsed if elapsed else 0.0,
                    selected_count=len(main_selected),
                    error_count=sum(result.status.value == "error" for result in rows),
                    source_hashes_unchanged=unchanged,
                    resume_verified=resume_verified,
                    stage_seconds=stage_seconds,
                )
            )
        finally:
            service.close()
            if not args.keep_staging:
                safe_remove_staging(staging, run_root)

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "private_corpus": True,
        "hardware": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": sys.version.split()[0],
        },
        "config": {
            "model": args.model,
            "device": args.device,
            "compute_type": args.compute_type,
            "language": args.language,
            "top_n": args.top_n,
            "physics_workers": args.physics_workers,
        },
        "results": [asdict(result) for result in results],
    }
    (run_root / "benchmark-aggregate.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (run_root / "benchmark-aggregate.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "file_count",
                "elapsed_seconds",
                "peak_rss_bytes",
                "database_bytes",
                "total_audio_seconds",
                "files_per_second",
                "selected_count",
                "error_count",
                "source_hashes_unchanged",
                "resume_verified",
            ],
        )
        writer.writeheader()
        writer.writerows(
            {key: value for key, value in asdict(result).items() if key != "stage_seconds"}
            for result in results
        )
    print(run_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
