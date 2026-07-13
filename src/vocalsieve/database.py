"""SQLite persistence for jobs, per-file state, and event history."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from platformdirs import user_data_path

from .domain import (
    FileStatus,
    Job,
    JobStatus,
    PipelineConfig,
    ReviewDecision,
    RuntimePolicy,
    ScannedFile,
)
from .errors import ResourceCapacityError
from .events import PipelineEvent

SCHEMA_VERSION = 3


def default_database_path() -> Path:
    return user_data_path("VocalSieve", appauthor=False) / "vocalsieve.db"


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                yield self._connection
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def _migrate(self) -> None:
        with self._lock:
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self._connection.commit()
            row = self._connection.execute(
                "SELECT value FROM schema_meta WHERE key = 'version'"
            ).fetchone()
        version = int(row["value"]) if row else 0
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema {version} is newer than supported {SCHEMA_VERSION}"
            )
        if 0 < version < SCHEMA_VERSION:
            self._backup_before_migration()
        with self.transaction() as connection:
            if version < 1:
                self._create_schema(connection)
            elif version < 2:
                connection.execute("ALTER TABLE jobs ADD COLUMN owner_pid INTEGER")
            if 0 < version < 3:
                connection.execute("ALTER TABLE files ADD COLUMN review_decision TEXT")
                connection.execute("ALTER TABLE files ADD COLUMN review_note TEXT")
                connection.execute("ALTER TABLE files ADD COLUMN reviewed_at TEXT")
                self._create_resource_leases(connection)
                active_rows = connection.execute(
                    "SELECT id, owner_pid, config_json, updated_at FROM jobs WHERE status IN (?, ?)",
                    (JobStatus.RUNNING, JobStatus.CANCELLING),
                ).fetchall()
                for active in active_rows:
                    config = PipelineConfig.from_dict(json.loads(active["config_json"]))
                    device_class = "cpu" if config.device == "cpu" else "cuda"
                    connection.execute(
                        """
                        INSERT INTO resource_leases(job_id, owner_pid, device_class, acquired_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            active["id"],
                            active["owner_pid"] or 0,
                            device_class,
                            active["updated_at"],
                        ),
                    )
            if version < SCHEMA_VERSION:
                connection.execute(
                    "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('version', ?)",
                    (str(SCHEMA_VERSION),),
                )

    def _backup_before_migration(self) -> None:
        backup_path = self.path.with_name(f"{self.path.name}.pre-v{SCHEMA_VERSION}.bak")
        if backup_path.exists():
            return
        with sqlite3.connect(backup_path) as backup, self._lock:
            self._connection.backup(backup)

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                config_json TEXT NOT NULL,
                cache_key TEXT NOT NULL,
                current_stage TEXT,
                error TEXT,
                owner_pid INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX jobs_status_idx ON jobs(status);

            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                relative_path TEXT NOT NULL,
                size INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                cache_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reject_code TEXT,
                reject_detail TEXT,
                duration REAL,
                rms REAL,
                spectral_centroid REAL,
                transcription TEXT,
                language TEXT,
                no_speech_prob REAL,
                score REAL,
                exported_path TEXT,
                review_decision TEXT,
                review_note TEXT,
                reviewed_at TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(job_id, relative_path)
            );
            CREATE INDEX files_job_status_idx ON files(job_id, status);

            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                stage TEXT,
                message TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX events_job_idx ON events(job_id, id);
            """
        )
        Database._create_resource_leases(connection)

    @staticmethod
    def _create_resource_leases(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE resource_leases (
                job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
                owner_pid INTEGER NOT NULL,
                device_class TEXT NOT NULL,
                acquired_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX resource_leases_device_idx ON resource_leases(device_class)"
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def recover_interrupted_jobs(self) -> int:
        with self.transaction() as connection:
            return self._recover_interrupted_jobs(connection)

    def _recover_interrupted_jobs(self, connection: sqlite3.Connection) -> int:
        rows = connection.execute(
            "SELECT id, owner_pid FROM jobs WHERE status IN (?, ?)",
            (JobStatus.RUNNING, JobStatus.CANCELLING),
        ).fetchall()
        stale = [row["id"] for row in rows if not self._process_is_alive(row["owner_pid"])]
        connection.executemany(
            """
            UPDATE jobs SET status = ?, error = ?, owner_pid = NULL, updated_at = ?
            WHERE id = ?
            """,
            [
                (
                    JobStatus.CANCELLED,
                    "The previous process exited before the job finished",
                    self._now(),
                    job_id,
                )
                for job_id in stale
            ],
        )
        connection.executemany(
            "DELETE FROM resource_leases WHERE job_id = ?",
            [(job_id,) for job_id in stale],
        )
        connection.execute(
            """
            DELETE FROM resource_leases
            WHERE job_id IN (
                SELECT id FROM jobs WHERE status NOT IN (?, ?)
            )
            """,
            (JobStatus.RUNNING, JobStatus.CANCELLING),
        )
        return len(stale)

    @staticmethod
    def _process_is_alive(pid: int | None) -> bool:
        if not pid or pid <= 0:
            return False
        if os.name == "nt":
            import ctypes

            process_query_limited_information = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                process_query_limited_information, False, pid
            )
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def create_job(self, config: PipelineConfig) -> Job:
        config.validate()
        job_id = uuid.uuid4().hex
        now = self._now()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO jobs(id, status, config_json, cache_key, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    JobStatus.PENDING,
                    json.dumps(config.to_dict(), sort_keys=True),
                    config.cache_key,
                    now,
                    now,
                ),
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> Job:
        with self._lock:
            row = self._connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown job: {job_id}")
        return self._row_to_job(row)

    def list_jobs(self, limit: int = 100) -> list[Job]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            status=JobStatus(row["status"]),
            config=PipelineConfig.from_dict(json.loads(row["config_json"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            current_stage=row["current_stage"],
            error=row["error"],
        )

    @staticmethod
    def _paths_overlap(first: Path, second: Path) -> bool:
        return first == second or first in second.parents or second in first.parents

    def claim_job(
        self,
        job_id: str,
        *,
        policy: RuntimePolicy | None = None,
        device_class: str = "cpu",
    ) -> Job:
        runtime_policy = policy or RuntimePolicy()
        runtime_policy.validate()
        if device_class not in {"cpu", "cuda"}:
            raise ValueError("device_class must be cpu or cuda")
        with self.transaction() as connection:
            self._recover_interrupted_jobs(connection)
            row = connection.execute(
                "SELECT status, config_json FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown job: {job_id}")
            allowed = {JobStatus.PENDING, JobStatus.CANCELLED, JobStatus.FAILED}
            if JobStatus(row["status"]) not in allowed:
                raise RuntimeError(f"Job cannot be started from status {row['status']}")
            leases = connection.execute(
                """
                SELECT resource_leases.job_id, resource_leases.device_class, jobs.config_json
                FROM resource_leases JOIN jobs ON jobs.id = resource_leases.job_id
                WHERE resource_leases.job_id != ?
                """,
                (job_id,),
            ).fetchall()
            if len(leases) >= runtime_policy.max_active_jobs:
                raise ResourceCapacityError(
                    f"Runtime capacity is full ({runtime_policy.max_active_jobs} active jobs)",
                    resource="active_jobs",
                )
            cuda_jobs = sum(lease["device_class"] == "cuda" for lease in leases)
            if device_class == "cuda" and cuda_jobs >= runtime_policy.max_cuda_jobs:
                raise ResourceCapacityError(
                    f"CUDA capacity is full ({runtime_policy.max_cuda_jobs} active CUDA jobs)",
                    resource="cuda_jobs",
                )
            config = PipelineConfig.from_dict(json.loads(row["config_json"]))
            source = Path(config.source_dir).expanduser().resolve()
            output = Path(config.output_dir).expanduser().resolve()
            for lease in leases:
                active_config = PipelineConfig.from_dict(json.loads(lease["config_json"]))
                active_source = Path(active_config.source_dir).expanduser().resolve()
                active_output = Path(active_config.output_dir).expanduser().resolve()
                if (
                    self._paths_overlap(output, active_output)
                    or self._paths_overlap(output, active_source)
                    or self._paths_overlap(source, active_output)
                ):
                    raise ResourceCapacityError(
                        f"Job paths conflict with active job {lease['job_id']}",
                        resource="paths",
                    )
            now = self._now()
            connection.execute(
                """
                INSERT INTO resource_leases(job_id, owner_pid, device_class, acquired_at)
                VALUES (?, ?, ?, ?)
                """,
                (job_id, os.getpid(), device_class, now),
            )
            connection.execute(
                "UPDATE jobs SET status = ?, error = NULL, owner_pid = ?, updated_at = ? WHERE id = ?",
                (JobStatus.RUNNING, os.getpid(), now, job_id),
            )
        return self.get_job(job_id)

    def delete_pending_job(self, job_id: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                "DELETE FROM jobs WHERE id = ? AND status = ?", (job_id, JobStatus.PENDING)
            )

    def runtime_status(self, policy: RuntimePolicy | None = None) -> dict[str, Any]:
        runtime_policy = policy or RuntimePolicy()
        runtime_policy.validate()
        with self.transaction() as connection:
            self._recover_interrupted_jobs(connection)
            rows = connection.execute(
                "SELECT job_id, device_class, acquired_at FROM resource_leases ORDER BY acquired_at"
            ).fetchall()
        leases = [dict(row) for row in rows]
        return {
            "max_active_jobs": runtime_policy.max_active_jobs,
            "active_jobs": len(leases),
            "max_cuda_jobs": runtime_policy.max_cuda_jobs,
            "active_cuda_jobs": sum(row["device_class"] == "cuda" for row in leases),
            "leases": leases,
        }

    def set_job_state(
        self,
        job_id: str,
        status: JobStatus,
        *,
        stage: str | None = None,
        error: str | None = None,
    ) -> None:
        owner_pid = (
            None
            if status
            in {JobStatus.PENDING, JobStatus.CANCELLED, JobStatus.COMPLETED, JobStatus.FAILED}
            else os.getpid()
        )
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE jobs SET status = ?, current_stage = ?, error = ?, owner_pid = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, stage, error, owner_pid, self._now(), job_id),
            )
            if owner_pid is None:
                connection.execute("DELETE FROM resource_leases WHERE job_id = ?", (job_id,))

    def set_job_stage(self, job_id: str, stage: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                "UPDATE jobs SET current_stage = ?, updated_at = ? WHERE id = ?",
                (stage, self._now(), job_id),
            )

    def cancellation_requested(self, job_id: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT status FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return bool(row and row["status"] == JobStatus.CANCELLING)

    def upsert_scanned_file(self, job_id: str, scanned: ScannedFile, cache_key: str) -> sqlite3.Row:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM files WHERE job_id = ? AND relative_path = ?",
                (job_id, scanned.relative_path),
            ).fetchone()
            unchanged = row and (
                row["size"] == scanned.size
                and row["mtime_ns"] == scanned.mtime_ns
                and row["cache_key"] == cache_key
            )
            if not unchanged:
                connection.execute(
                    """
                    INSERT INTO files(
                        job_id, relative_path, size, mtime_ns, cache_key, status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(job_id, relative_path) DO UPDATE SET
                        size=excluded.size, mtime_ns=excluded.mtime_ns,
                        cache_key=excluded.cache_key, status=excluded.status,
                        reject_code=NULL, reject_detail=NULL, duration=NULL, rms=NULL,
                        spectral_centroid=NULL, transcription=NULL, language=NULL,
                        no_speech_prob=NULL, score=NULL, exported_path=NULL,
                        review_decision=NULL, review_note=NULL, reviewed_at=NULL,
                        updated_at=excluded.updated_at
                    """,
                    (
                        job_id,
                        scanned.relative_path,
                        scanned.size,
                        scanned.mtime_ns,
                        cache_key,
                        FileStatus.PENDING,
                        self._now(),
                    ),
                )
            return connection.execute(
                "SELECT * FROM files WHERE job_id = ? AND relative_path = ?",
                (job_id, scanned.relative_path),
            ).fetchone()

    def update_file(self, job_id: str, relative_path: str, **values: Any) -> None:
        allowed = {
            "status",
            "reject_code",
            "reject_detail",
            "duration",
            "rms",
            "spectral_centroid",
            "transcription",
            "language",
            "no_speech_prob",
            "score",
            "exported_path",
            "review_decision",
            "review_note",
            "reviewed_at",
        }
        invalid = set(values) - allowed
        if invalid:
            raise ValueError(f"Unsupported file fields: {sorted(invalid)}")
        values["updated_at"] = self._now()
        assignments = ", ".join(f"{name} = ?" for name in values)
        parameters = [*values.values(), job_id, relative_path]
        with self.transaction() as connection:
            connection.execute(
                f"UPDATE files SET {assignments} WHERE job_id = ? AND relative_path = ?",
                parameters,
            )

    def prune_files(self, job_id: str, relative_paths: set[str]) -> None:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT relative_path FROM files WHERE job_id = ?", (job_id,)
            ).fetchall()
            stale = [
                row["relative_path"] for row in rows if row["relative_path"] not in relative_paths
            ]
            connection.executemany(
                "DELETE FROM files WHERE job_id = ? AND relative_path = ?",
                [(job_id, path) for path in stale],
            )

    def get_files(
        self,
        job_id: str,
        *,
        statuses: Sequence[str] | None = None,
        language: str | None = None,
        reason: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["job_id = ?"]
        parameters: list[Any] = [job_id]
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            clauses.append(f"status IN ({placeholders})")
            parameters.extend(statuses)
        if language:
            clauses.append("language = ?")
            parameters.append(language)
        if reason:
            clauses.append("(reject_code LIKE ? OR reject_detail LIKE ?)")
            parameters.extend([f"%{reason}%", f"%{reason}%"])
        query = "SELECT * FROM files WHERE " + " AND ".join(clauses)
        query += " ORDER BY relative_path"
        with self._lock:
            rows = self._connection.execute(query, parameters).fetchall()
        results = [dict(row) for row in rows]
        for row in results:
            row["effective_selected"] = row["review_decision"] == ReviewDecision.INCLUDE or (
                row["review_decision"] is None and row["status"] == FileStatus.SELECTED
            )
        return results

    def review_file(
        self,
        job_id: str,
        relative_path: str,
        decision: ReviewDecision | None,
        note: str | None = None,
    ) -> dict[str, Any]:
        cleaned_note = note.strip() if note else None
        if cleaned_note and len(cleaned_note) > 500:
            raise ValueError("Review note cannot exceed 500 characters")
        with self.transaction() as connection:
            job = connection.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if job is None:
                raise KeyError(f"Unknown job: {job_id}")
            if JobStatus(job["status"]) != JobStatus.COMPLETED:
                raise RuntimeError("Only completed jobs can be reviewed")
            row = connection.execute(
                "SELECT review_decision FROM files WHERE job_id = ? AND relative_path = ?",
                (job_id, relative_path),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown result: {relative_path}")
            connection.execute(
                """
                UPDATE files
                SET review_decision = ?, review_note = ?, reviewed_at = ?, updated_at = ?
                WHERE job_id = ? AND relative_path = ?
                """,
                (
                    decision.value if decision else None,
                    cleaned_note if decision else None,
                    self._now() if decision else None,
                    self._now(),
                    job_id,
                    relative_path,
                ),
            )
        return next(row for row in self.get_files(job_id) if row["relative_path"] == relative_path)

    def reset_selection(self, job_id: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE files SET status = ?, score = NULL, exported_path = NULL,
                    updated_at = ?
                WHERE job_id = ? AND status = ?
                """,
                (
                    FileStatus.TRANSCRIPTION_PASSED,
                    self._now(),
                    job_id,
                    FileStatus.SELECTED,
                ),
            )

    def add_event(self, event: PipelineEvent) -> None:
        data = {
            "current": event.current,
            "total": event.total,
            "relative_path": event.relative_path,
            "accepted": event.accepted,
            **event.data,
        }
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO events(job_id, event_type, stage, message, data_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.job_id,
                    event.type,
                    event.stage,
                    event.message,
                    json.dumps(data, ensure_ascii=True),
                    event.timestamp,
                ),
            )

    def get_events(self, job_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, event_type, stage, message, data_json, created_at
                FROM events WHERE job_id = ? AND id > ? ORDER BY id
                """,
                (job_id, after_id),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "job_id": job_id,
                "type": row["event_type"],
                "stage": row["stage"],
                "message": row["message"],
                "data": json.loads(row["data_json"]),
                "timestamp": row["created_at"],
            }
            for row in rows
        ]
