"""Background worker state for API-triggered jobs."""

from __future__ import annotations

import logging
import threading
from contextlib import suppress

from .domain import JobStatus
from .errors import JobNotFoundError, JobStateError
from .service import VocalSieveService

logger = logging.getLogger(__name__)


class WorkerStartError(RuntimeError):
    """Raised when a reserved API job cannot start its background thread."""


class WorkerState:
    def __init__(self, service: VocalSieveService):
        self._service = service
        self._workers: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def start_reserved(self, job_id: str) -> None:
        worker = self._make_worker(job_id)
        with self._lock:
            if job_id in self._workers:
                raise WorkerStartError(f"Job {job_id} already has an API worker")
            self._workers[job_id] = worker
        try:
            worker.start()
        except RuntimeError as exc:
            with self._lock:
                self._workers.pop(job_id, None)
            self._service.database.set_job_state(job_id, JobStatus.FAILED, error=str(exc))
            raise WorkerStartError(str(exc)) from exc

    def shutdown(self) -> None:
        with self._lock:
            active = list(self._workers.items())
        for job_id, _worker in active:
            with suppress(JobNotFoundError, JobStateError):
                self._service.cancel_job(job_id)
        for _job_id, worker in active:
            worker.join(timeout=5)

    def _make_worker(self, job_id: str) -> threading.Thread:
        def target() -> None:
            try:
                self._service.run_reserved_job(job_id)
                job = self._service.get_job(job_id)
                if job.status in {JobStatus.RUNNING, JobStatus.CANCELLING}:
                    self._service.database.set_job_state(
                        job_id,
                        JobStatus.FAILED,
                        error="Background worker exited before the job reached a terminal state",
                    )
            except Exception as exc:
                logger.exception("Background job %s failed", job_id)
                with suppress(JobNotFoundError):
                    job = self._service.get_job(job_id)
                    if job.status in {JobStatus.RUNNING, JobStatus.CANCELLING}:
                        self._service.database.set_job_state(
                            job_id,
                            JobStatus.FAILED,
                            error=str(exc),
                        )
            finally:
                with self._lock:
                    self._workers.pop(job_id, None)

        return threading.Thread(target=target, name=f"vocalsieve-{job_id[:8]}", daemon=True)
