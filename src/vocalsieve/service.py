"""Use-case facade shared by all user interfaces."""

from __future__ import annotations

import threading
from pathlib import Path

from .audio import AudioAnalyzer
from .database import Database
from .domain import FileResult, Job, JobStatus, PipelineConfig
from .errors import JobNotFoundError, JobStateError
from .events import EventSink, ignore_event
from .exporter import build_report_summary, export_selected
from .pipeline import PipelineRunner


class VocalSieveService:
    def __init__(self, database_path: str | Path | None = None):
        self.database = Database(database_path)
        self.database.recover_interrupted_jobs()
        self._cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def close(self) -> None:
        self.database.close()

    def create_job(self, config: PipelineConfig) -> Job:
        return self.database.create_job(config)

    def get_job(self, job_id: str) -> Job:
        try:
            return self.database.get_job(job_id)
        except KeyError as exc:
            raise JobNotFoundError(job_id) from exc

    def run_job(
        self,
        job_id: str,
        event_sink: EventSink = ignore_event,
        *,
        analyzer: AudioAnalyzer | None = None,
        transcriber_factory=None,
    ) -> Job:
        try:
            job = self.database.claim_job(job_id)
        except KeyError as exc:
            raise JobNotFoundError(job_id) from exc
        except RuntimeError as exc:
            raise JobStateError(str(exc)) from exc
        cancel_event = threading.Event()
        with self._lock:
            self._cancel_events[job_id] = cancel_event
        try:
            PipelineRunner(
                self.database,
                job.config,
                job_id,
                event_sink=event_sink,
                cancel_event=cancel_event,
                analyzer=analyzer,
                transcriber_factory=transcriber_factory,
            ).run()
        except KeyboardInterrupt:
            self.database.set_job_state(job_id, JobStatus.CANCELLED)
            raise
        finally:
            with self._lock:
                self._cancel_events.pop(job_id, None)
        return self.database.get_job(job_id)

    def resume_job(self, job_id: str, event_sink: EventSink = ignore_event) -> Job:
        return self.run_job(job_id, event_sink)

    def cancel_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        if job.status != JobStatus.RUNNING:
            raise JobStateError("Only a running job can be cancelled")
        self.database.set_job_state(job_id, JobStatus.CANCELLING, stage=job.current_stage)
        with self._lock:
            event = self._cancel_events.get(job_id)
        if event is not None:
            event.set()

    def list_jobs(self, limit: int = 100) -> list[Job]:
        return self.database.list_jobs(limit)

    def query_results(
        self,
        job_id: str,
        *,
        status: str | None = None,
        language: str | None = None,
        reason: str | None = None,
    ) -> list[FileResult]:
        statuses = [status] if status else None
        try:
            self.database.get_job(job_id)
        except KeyError as exc:
            raise JobNotFoundError(job_id) from exc
        return [
            FileResult.from_mapping(row)
            for row in self.database.get_files(
                job_id, statuses=statuses, language=language, reason=reason
            )
        ]

    def export_job(self, job_id: str) -> dict[str, str]:
        job = self.get_job(job_id)
        selected = self.database.get_files(job_id, statuses=["selected"])
        exported = export_selected(
            Path(job.config.source_dir).expanduser().resolve(),
            Path(job.config.output_dir).expanduser().resolve(),
            selected,
            self.database.get_files(job_id),
            job_id=job_id,
            config=job.config,
            events=self.database.get_events(job_id),
        )
        for relative_path, destination in exported.items():
            self.database.update_file(job_id, relative_path, exported_path=destination)
        return exported

    def report_job(self, job_id: str) -> dict:
        job = self.get_job(job_id)
        return build_report_summary(
            job_id,
            job.config,
            self.database.get_files(job_id),
            self.database.get_events(job_id),
        )
