from pathlib import Path

from vocalsieve.database import Database
from vocalsieve.domain import JobStatus, PipelineConfig, ScannedFile


def test_interrupted_jobs_are_recoverable(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    database = Database(tmp_path / "state.db")
    job = database.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
    database.claim_job(job.id)
    with database.transaction() as connection:
        connection.execute("UPDATE jobs SET owner_pid = ? WHERE id = ?", (99999999, job.id))
    assert database.recover_interrupted_jobs() == 1
    assert database.get_job(job.id).status == JobStatus.CANCELLED


def test_live_jobs_are_not_recovered_by_another_connection(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    path = tmp_path / "state.db"
    first = Database(path)
    job = first.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
    first.claim_job(job.id)
    second = Database(path)
    assert second.recover_interrupted_jobs() == 0
    assert second.get_job(job.id).status == JobStatus.RUNNING


def test_file_fingerprint_invalidates_cached_result(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    database = Database(tmp_path / "state.db")
    config = PipelineConfig(str(source), str(tmp_path / "out"))
    job = database.create_job(config)
    item = ScannedFile("a.wav", source / "a.wav", 10, 1)
    database.upsert_scanned_file(job.id, item, config.cache_key)
    database.update_file(job.id, "a.wav", status="physics_rejected")
    changed = ScannedFile("a.wav", source / "a.wav", 11, 2)
    row = database.upsert_scanned_file(job.id, changed, config.cache_key)
    assert row["status"] == "pending"
