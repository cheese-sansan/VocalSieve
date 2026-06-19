"""Command-line interface for automation and diagnostics."""

from __future__ import annotations

import argparse
import os
import sys

from .doctor import run_diagnostics
from .domain import PipelineConfig
from .events import PipelineEvent
from .runtime import configure_runtime
from .service import VocalSieveService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vocalsieve", description="Local-first audio corpus screening workbench"
    )
    parser.add_argument("--database", help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="Create and run a screening job")
    run.add_argument("source")
    run.add_argument("output")
    run.add_argument("--model", default="small")
    run.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    run.add_argument("--compute-type", default="auto")
    run.add_argument("--language", default="auto")
    run.add_argument("--top-n", type=int, default=1200)
    run.add_argument("--physics-workers", type=int, default=4)

    resume = subparsers.add_parser("resume", help="Resume a cancelled or failed job")
    resume.add_argument("job_id")

    doctor = subparsers.add_parser("doctor", help="Check runtime dependencies")
    doctor.add_argument("--deep", action="store_true", help="Run a real inference probe")
    doctor.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    doctor.add_argument("--model", default="tiny")
    jobs = subparsers.add_parser("jobs", help="List recent jobs")
    jobs.add_argument("--limit", type=int, default=20)

    export = subparsers.add_parser("export", help="Export a completed job again")
    export.add_argument("job_id")
    serve = subparsers.add_parser("serve", help="Start the loopback-only HTTP API")
    serve.add_argument("--port", type=int, default=8765)
    return parser


def print_event(event: PipelineEvent) -> None:
    progress = ""
    if event.current is not None and event.total is not None:
        progress = f" [{event.current}/{event.total}]"
    path = f" {event.relative_path}" if event.relative_path else ""
    print(f"{event.type.value:16}{progress}{path} - {event.message}")


def main(argv: list[str] | None = None) -> int:
    configure_runtime()
    args = build_parser().parse_args(argv)
    if args.command is None:
        from .tui import run_tui

        run_tui(args.database)
        return 0
    if args.command == "doctor":
        checks = run_diagnostics(deep=args.deep, device=args.device, model_size=args.model)
        for check in checks:
            state = "OK" if check.ok else ("WARN" if not check.required else "FAIL")
            print(f"{state:4} {check.name:16} {check.detail}")
        return 0 if all(check.ok for check in checks if check.required) else 1
    if args.command == "serve":
        try:
            import uvicorn

            from .api import create_app
        except ImportError:
            print("Error: install VocalSieve with the 'api' extra", file=sys.stderr)
            return 1
        app = create_app(args.database, session_token=os.environ.get("VOCALSIEVE_SESSION_TOKEN"))
        container_mode = os.environ.get("VOCALSIEVE_CONTAINER") == "1"
        host = "0.0.0.0" if container_mode else "127.0.0.1"
        print(f"VocalSieve API: http://127.0.0.1:{args.port}")
        print(f"Session token: {app.state.session_token}")
        uvicorn.run(app, host=host, port=args.port, log_level="info")
        return 0

    service = VocalSieveService(args.database)
    try:
        if args.command == "jobs":
            jobs = service.list_jobs(args.limit)
            if not jobs:
                print("No jobs found.")
            for job in jobs:
                print(f"{job.id}  {job.status.value:11}  {job.created_at}  {job.config.source_dir}")
            return 0
        if args.command == "run":
            config = PipelineConfig(
                source_dir=args.source,
                output_dir=args.output,
                model_size=args.model,
                device=args.device,
                compute_type=args.compute_type,
                language=args.language,
                top_n=args.top_n,
                physics_workers=args.physics_workers,
            )
            job = service.create_job(config)
            print(f"Created job {job.id}")
            result = service.run_job(job.id, print_event)
            return 0 if result.status.value == "completed" else 1
        if args.command == "resume":
            result = service.resume_job(args.job_id, print_event)
            return 0 if result.status.value == "completed" else 1
        if args.command == "export":
            exported = service.export_job(args.job_id)
            print(f"Exported {len(exported)} files.")
            return 0
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        service.close()
    return 0
