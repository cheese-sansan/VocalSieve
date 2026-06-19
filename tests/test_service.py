import threading
from pathlib import Path

import pytest

from vocalsieve.domain import FileStatus, JobStatus, PipelineConfig, ScannedFile
from vocalsieve.errors import JobNotFoundError, JobStateError
from vocalsieve.service import VocalSieveService


def make_service(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    service = VocalSieveService(tmp_path / "state.db")
    job = service.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
    return service, job, source


def test_service_maps_missing_and_invalid_states(tmp_path: Path):
    service, job, _ = make_service(tmp_path)
    with pytest.raises(JobNotFoundError):
        service.get_job("missing")
    with pytest.raises(JobNotFoundError):
        service.run_job("missing")
    with pytest.raises(JobNotFoundError):
        service.query_results("missing")
    with pytest.raises(JobStateError):
        service.cancel_job(job.id)

    service.database.claim_job(job.id)
    with pytest.raises(JobStateError):
        service.run_job(job.id)


def test_service_cancel_sets_live_event(tmp_path: Path):
    service, job, _ = make_service(tmp_path)
    service.database.claim_job(job.id)
    event = threading.Event()
    service._cancel_events[job.id] = event
    service.cancel_job(job.id)
    assert event.is_set()
    assert service.get_job(job.id).status == JobStatus.CANCELLING


def test_service_exports_selected_file_and_filters_results(tmp_path: Path):
    service, job, source = make_service(tmp_path)
    audio = source / "speaker" / "a.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"audio")
    stat = audio.stat()
    service.database.upsert_scanned_file(
        job.id,
        ScannedFile("speaker/a.wav", audio, stat.st_size, stat.st_mtime_ns),
        job.config.cache_key,
    )
    service.database.update_file(
        job.id,
        "speaker/a.wav",
        status=FileStatus.SELECTED,
        language="en",
        reject_code=None,
    )
    results = service.query_results(job.id, status="selected", language="en")
    assert results[0].status == FileStatus.SELECTED
    exported = service.export_job(job.id)
    assert Path(exported["speaker/a.wav"]).is_file()
    assert service.query_results(job.id)[0].exported_path is not None


def test_service_resume_empty_cancelled_job(tmp_path: Path):
    service, job, _ = make_service(tmp_path)
    service.database.set_job_state(job.id, JobStatus.CANCELLED)
    result = service.resume_job(job.id)
    assert result.status == JobStatus.COMPLETED
