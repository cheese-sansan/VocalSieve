import sqlite3
from pathlib import Path

import pytest

from vocalsieve.database import Database
from vocalsieve.domain import JobStatus, PipelineConfig, RuntimePolicy, ScannedFile
from vocalsieve.errors import ResourceCapacityError


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
    assert database.runtime_status()["active_jobs"] == 0


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


def test_resource_policy_coordinates_connections_and_limits_capacity(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    path = tmp_path / "state.db"
    first = Database(path)
    jobs = [
        first.create_job(PipelineConfig(str(source), str(tmp_path / f"out-{index}")))
        for index in range(3)
    ]
    policy = RuntimePolicy(max_active_jobs=2, max_cuda_jobs=1)
    first.claim_job(jobs[0].id, policy=policy)
    second = Database(path)
    second.claim_job(jobs[1].id, policy=policy)
    with pytest.raises(ResourceCapacityError, match="capacity is full"):
        second.claim_job(jobs[2].id, policy=policy)
    assert first.runtime_status(policy)["active_jobs"] == 2


def test_resource_policy_limits_cuda_and_rejects_path_conflicts(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    database = Database(tmp_path / "state.db")
    policy = RuntimePolicy(max_active_jobs=3, max_cuda_jobs=1)
    first = database.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
    database.claim_job(first.id, policy=policy, device_class="cuda")

    cuda = database.create_job(PipelineConfig(str(source), str(tmp_path / "cuda-out")))
    with pytest.raises(ResourceCapacityError) as cuda_error:
        database.claim_job(cuda.id, policy=policy, device_class="cuda")
    assert cuda_error.value.resource == "cuda_jobs"

    nested = database.create_job(PipelineConfig(str(source), str(tmp_path / "out" / "nested")))
    with pytest.raises(ResourceCapacityError) as path_error:
        database.claim_job(nested.id, policy=policy)
    assert path_error.value.resource == "paths"


def test_v2_database_is_backed_up_and_migrated_to_v3(tmp_path: Path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO schema_meta(key, value) VALUES('version', '2');
            CREATE TABLE jobs (
                id TEXT PRIMARY KEY, status TEXT NOT NULL, config_json TEXT NOT NULL,
                cache_key TEXT NOT NULL, current_stage TEXT, error TEXT, owner_pid INTEGER,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                relative_path TEXT NOT NULL, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
                cache_key TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                reject_code TEXT, reject_detail TEXT, duration REAL, rms REAL,
                spectral_centroid REAL, transcription TEXT, language TEXT,
                no_speech_prob REAL, score REAL, exported_path TEXT,
                updated_at TEXT NOT NULL, UNIQUE(job_id, relative_path)
            );
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL, stage TEXT, message TEXT NOT NULL,
                data_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """
        )
    database = Database(path)
    with database._lock:
        version = database._connection.execute(
            "SELECT value FROM schema_meta WHERE key = 'version'"
        ).fetchone()["value"]
        columns = {row["name"] for row in database._connection.execute("PRAGMA table_info(files)")}
    assert version == "3"
    assert {"review_decision", "review_note", "reviewed_at"} <= columns
    assert (tmp_path / "legacy.db.pre-v3.bak").is_file()
