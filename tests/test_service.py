import threading
from pathlib import Path

import pytest

from vocalsieve.domain import FileStatus, JobStatus, PipelineConfig, ReviewDecision, ScannedFile
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


def test_service_cancel_is_visible_across_database_connections(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    path = tmp_path / "state.db"
    owner = VocalSieveService(path)
    job = owner.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
    owner.reserve_job(job.id)
    controller = VocalSieveService(path)
    controller.cancel_job(job.id)
    assert owner.database.cancellation_requested(job.id)
    owner.database.set_job_state(job.id, JobStatus.CANCELLED)


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


def test_service_reviews_completed_results_and_audits_changes(tmp_path: Path):
    service, job, source = make_service(tmp_path)
    audio = source / "a.wav"
    audio.write_bytes(b"audio")
    stat = audio.stat()
    service.database.upsert_scanned_file(
        job.id,
        ScannedFile("a.wav", audio, stat.st_size, stat.st_mtime_ns),
        job.config.cache_key,
    )
    service.database.update_file(job.id, "a.wav", status=FileStatus.SELECTED)
    with pytest.raises(JobStateError):
        service.review_result(job.id, "a.wav", ReviewDecision.EXCLUDE)
    service.database.set_job_state(job.id, JobStatus.COMPLETED)

    excluded = service.review_result(job.id, "a.wav", ReviewDecision.EXCLUDE, "not usable")
    assert excluded.review_decision == ReviewDecision.EXCLUDE
    assert not excluded.effective_selected
    included = service.review_result(job.id, "a.wav", ReviewDecision.INCLUDE)
    assert included.effective_selected
    automatic = service.review_result(job.id, "a.wav", None)
    assert automatic.review_decision is None
    assert automatic.effective_selected
    assert [event["type"] for event in service.database.get_events(job.id)] == [
        "review_changed",
        "review_changed",
        "review_changed",
    ]
