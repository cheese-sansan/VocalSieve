import threading
from pathlib import Path

import pytest

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
