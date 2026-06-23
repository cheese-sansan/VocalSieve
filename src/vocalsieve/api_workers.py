"""Background worker state for API-triggered jobs."""

from __future__ import annotations

import threading
from collections.abc import Callable

from .domain import Job
from .service import VocalSieveService


class WorkerState:
    def __init__(self, service: VocalSieveService):
        self._service = service
        self._workers: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def create_and_start(self, create: Callable[[], Job]) -> Job:
        with self._lock:
            if self._workers:
                raise RuntimeError("Another job is already active")
            job = create()
            worker = self._make_worker(job.id, resume=False)
            self._workers[job.id] = worker
        worker.start()
        return job

    def start(self, job_id: str, *, resume: bool = False) -> None:
        worker = self._make_worker(job_id, resume=resume)
        with self._lock:
            if self._workers:
                raise RuntimeError("Another job is already active")
            self._workers[job_id] = worker
        worker.start()

    def _make_worker(self, job_id: str, *, resume: bool) -> threading.Thread:
        def target() -> None:
            try:
                if resume:
                    self._service.resume_job(job_id)
                else:
                    self._service.run_job(job_id)
            finally:
                with self._lock:
                    self._workers.pop(job_id, None)

        return threading.Thread(target=target, name=f"vocalsieve-{job_id[:8]}", daemon=True)
