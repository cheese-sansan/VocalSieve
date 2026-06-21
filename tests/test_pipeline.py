import hashlib
import json
import threading
from pathlib import Path

import pytest

from tests.fixtures.audio_factory import generated_corpus
from vocalsieve.domain import AudioMetrics, JobStatus, PipelineConfig, Transcript
from vocalsieve.pipeline import PipelineRunner
from vocalsieve.service import VocalSieveService


class FakeAnalyzer:
    def analyze(self, path: Path) -> AudioMetrics:
        if path.name.startswith("bad"):
            return AudioMetrics(duration=0.1, rms=0.5, spectral_centroid=2000)
        return AudioMetrics(duration=1.0, rms=0.5, spectral_centroid=2000)


class FakeTranscriber:
    effective_device = "cpu"

    def prepare(self) -> None:
        return None

    def transcribe(self, path: Path) -> Transcript:
        return Transcript(text=f"voice {path.stem}", language="en", no_speech_prob=0.1)


def fake_factory(config: PipelineConfig) -> FakeTranscriber:
    return FakeTranscriber()


def test_end_to_end_preserves_relative_paths_and_source(tmp_path: Path):
    source = tmp_path / "source"
    nested = source / "speaker"
    nested.mkdir(parents=True)
    good = nested / "good.wav"
    bad = source / "bad.wav"
    good.write_bytes(b"good")
    bad.write_bytes(b"bad")
    output = tmp_path / "output"
    service = VocalSieveService(tmp_path / "state.db")
    config = PipelineConfig(str(source), str(output), top_n=1)
    job = service.create_job(config)
    result = service.run_job(job.id, analyzer=FakeAnalyzer(), transcriber_factory=fake_factory)
    assert result.status.value == "completed"
    assert good.read_bytes() == b"good"
    assert bad.read_bytes() == b"bad"
    assert (output / "final_selected" / "speaker" / "good.wav").is_file()
    assert (output / "vocalsieve-report.csv").is_file()
    rows = service.query_results(job.id)
    assert {row.status.value for row in rows} == {"physics_rejected", "selected"}
    backend_events = [
        event
        for event in service.database.get_events(job.id)
        if event["data"].get("backend_selected")
    ]
    assert backend_events[0]["data"]["effective_device"] == "cpu"
    assert not any(
        event["data"].get("backend_fallback") for event in service.database.get_events(job.id)
    )


def test_completed_files_are_reused_after_resume(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    audio = source / "one.wav"
    audio.write_bytes(b"audio")
    service = VocalSieveService(tmp_path / "state.db")
    job = service.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
    service.database.claim_job(job.id)
    service.database.set_job_state(job.id, JobStatus.CANCELLED)
    first = service.run_job(job.id, analyzer=FakeAnalyzer(), transcriber_factory=fake_factory)
    assert first.status.value == "completed"


def test_pipeline_records_file_errors_and_can_cancel(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "good.wav").write_bytes(b"audio")

    class BrokenAnalyzer:
        def analyze(self, path: Path) -> AudioMetrics:
            raise RuntimeError("decoder failed")

    service = VocalSieveService(tmp_path / "state.db")
    job = service.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
    completed = service.run_job(job.id, analyzer=BrokenAnalyzer(), transcriber_factory=fake_factory)
    assert completed.status is JobStatus.COMPLETED
    result = service.query_results(job.id)[0]
    assert result.status.value == "error"
    assert result.reject_code == "physics_error"

    cancelled_job = service.create_job(PipelineConfig(str(source), str(tmp_path / "cancelled-out")))
    cancel_event = threading.Event()
    cancel_event.set()
    service.database.claim_job(cancelled_job.id)
    PipelineRunner(
        service.database,
        cancelled_job.config,
        cancelled_job.id,
        analyzer=FakeAnalyzer(),
        transcriber_factory=fake_factory,
        cancel_event=cancel_event,
    ).run()
    assert service.get_job(cancelled_job.id).status is JobStatus.CANCELLED


def test_pipeline_marks_job_failed_on_stage_error(tmp_path: Path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    service = VocalSieveService(tmp_path / "state.db")
    job = service.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
    monkeypatch.setattr(
        "vocalsieve.pipeline.scan_audio_files",
        lambda *_: (_ for _ in ()).throw(RuntimeError("scan failed")),
    )
    with pytest.raises(RuntimeError, match="scan failed"):
        service.run_job(job.id, analyzer=FakeAnalyzer(), transcriber_factory=fake_factory)
    assert service.get_job(job.id).status is JobStatus.FAILED


def test_real_audio_lightweight_end_to_end(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    files = generated_corpus(source)
    before = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}

    class FixtureTranscriber:
        effective_device = "cpu"
        effective_compute_type = "int8"
        fallback_reason = "cuda_runtime_unavailable"
        fallback_occurred = True

        def prepare(self) -> None:
            return None

        def transcribe(self, path: Path) -> Transcript:
            if path.stem == "noise":
                return Transcript("", "en", 0.99)
            return Transcript("clear voice", "en", 0.01)

    output = tmp_path / "output"
    service = VocalSieveService(tmp_path / "state.db")
    job = service.create_job(PipelineConfig(str(source), str(output), top_n=1))
    completed = service.run_job(job.id, transcriber_factory=lambda _: FixtureTranscriber())
    assert completed.status is JobStatus.COMPLETED

    results = {row.relative_path: row for row in service.query_results(job.id)}
    assert results["speaker/normal.wav"].status.value == "selected"
    assert results["short.wav"].reject_code == "duration_too_short"
    assert results["quiet.wav"].reject_code == "energy_too_low"
    assert results["silence.wav"].reject_code == "energy_too_low"
    assert results["noise.wav"].reject_code == "no_speech"
    assert results["broken.wav"].reject_code == "physics_error"
    assert (output / "final_selected" / "speaker" / "normal.wav").is_file()

    after = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}
    assert after == before
    report = json.loads((output / "vocalsieve-report.json").read_text(encoding="utf-8"))
    summary = json.loads((output / "vocalsieve-summary.json").read_text(encoding="utf-8"))
    assert len(report) == 6
    assert summary["total_scanned"] == 6
    assert summary["candidate_count"] == 1
    assert summary["selected_count"] == 1
    assert summary["rejected_count"] == 4
    assert summary["error_count"] == 1
    assert summary["backend"]["fallback"] is True
