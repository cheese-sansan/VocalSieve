"""Application-independent pipeline orchestration."""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .audio import AudioAnalyzer, LibrosaAudioAnalyzer
from .database import Database
from .domain import FileStatus, JobStatus, PipelineConfig, ScannedFile, Stage
from .events import EventSink, EventType, PipelineEvent, ignore_event
from .exporter import export_selected
from .rules import evaluate_physics, evaluate_transcript, rank_score
from .scanner import scan_audio_files
from .transcription import FasterWhisperTranscriber, Transcriber


class PipelineRunner:
    def __init__(
        self,
        database: Database,
        config: PipelineConfig,
        job_id: str,
        *,
        event_sink: EventSink = ignore_event,
        cancel_event: threading.Event | None = None,
        analyzer: AudioAnalyzer | None = None,
        transcriber_factory: Callable[[PipelineConfig], Transcriber] | None = None,
    ):
        self.database = database
        self.config = config
        self.job_id = job_id
        self.event_sink = event_sink
        self.cancel_event = cancel_event or threading.Event()
        self.analyzer = analyzer or LibrosaAudioAnalyzer()
        self.transcriber_factory = transcriber_factory or FasterWhisperTranscriber

    def run(self) -> None:
        self.config.validate()
        self._emit(EventType.JOB_STARTED, "Job started")
        try:
            scanned = self._scan()
            if self._cancelled():
                return
            self._physics(scanned)
            if self._cancelled():
                return
            self._transcribe(scanned)
            if self._cancelled():
                return
            self._rank_and_export()
            if self._cancelled():
                return
            self.database.set_job_state(self.job_id, JobStatus.COMPLETED)
            selected = self.database.get_files(self.job_id, statuses=[FileStatus.SELECTED])
            self._emit(
                EventType.JOB_COMPLETED,
                f"Job completed with {len(selected)} selected files",
                data={"selected": len(selected)},
            )
        except Exception as exc:
            self.database.set_job_state(self.job_id, JobStatus.FAILED, error=str(exc))
            self._emit(EventType.ERROR, f"Job failed: {exc}")
            raise

    def _scan(self) -> list[ScannedFile]:
        self._start_stage(Stage.SCAN, "Scanning source files")
        files = scan_audio_files(self.config.source_dir, self.config.output_dir)
        paths = {item.relative_path for item in files}
        for item in files:
            self.database.upsert_scanned_file(self.job_id, item, self.config.cache_key)
        self.database.prune_files(self.job_id, paths)
        self._emit(
            EventType.PROGRESS,
            f"Found {len(files)} supported audio files",
            stage=Stage.SCAN,
            current=len(files),
            total=len(files),
        )
        return files

    def _physics(self, scanned: list[ScannedFile]) -> None:
        self._start_stage(Stage.PHYSICS, "Analyzing acoustic features")
        rows = {row["relative_path"]: row for row in self.database.get_files(self.job_id)}
        pending = [
            item
            for item in scanned
            if rows[item.relative_path]["status"] in {FileStatus.PENDING, FileStatus.ERROR}
        ]
        total = len(pending)
        if not pending:
            self._emit(
                EventType.PROGRESS,
                "Acoustic analysis is already complete",
                stage=Stage.PHYSICS,
                current=0,
                total=0,
            )
            return
        with ThreadPoolExecutor(max_workers=self.config.physics_workers) as executor:
            futures = {
                executor.submit(self.analyzer.analyze, item.absolute_path): item for item in pending
            }
            for current, future in enumerate(as_completed(futures), start=1):
                item = futures[future]
                if self.cancel_event.is_set():
                    for remaining in futures:
                        remaining.cancel()
                    break
                try:
                    metrics = future.result()
                    decision = evaluate_physics(metrics, self.config)
                    status = (
                        FileStatus.PHYSICS_PASSED
                        if decision.accepted
                        else FileStatus.PHYSICS_REJECTED
                    )
                    self.database.update_file(
                        self.job_id,
                        item.relative_path,
                        status=status,
                        reject_code=decision.code,
                        reject_detail=decision.detail,
                        duration=metrics.duration,
                        rms=metrics.rms,
                        spectral_centroid=metrics.spectral_centroid,
                    )
                    self._file_event(
                        Stage.PHYSICS,
                        item.relative_path,
                        decision.accepted,
                        current,
                        total,
                        decision.detail,
                    )
                except Exception as exc:
                    self.database.update_file(
                        self.job_id,
                        item.relative_path,
                        status=FileStatus.ERROR,
                        reject_code="physics_error",
                        reject_detail=str(exc),
                    )
                    self._file_event(
                        Stage.PHYSICS, item.relative_path, False, current, total, str(exc)
                    )

    def _transcribe(self, scanned: list[ScannedFile]) -> None:
        self._start_stage(Stage.TRANSCRIPTION, "Transcribing eligible files")
        rows = {row["relative_path"]: row for row in self.database.get_files(self.job_id)}
        pending = [
            item
            for item in scanned
            if rows[item.relative_path]["status"] == FileStatus.PHYSICS_PASSED
        ]
        total = len(pending)
        if not pending:
            self._emit(
                EventType.PROGRESS,
                "No files require transcription",
                stage=Stage.TRANSCRIPTION,
                current=0,
                total=0,
            )
            return
        transcriber = self.transcriber_factory(self.config)
        prepare = getattr(transcriber, "prepare", None)
        if prepare is not None:
            prepare()
        effective_device = getattr(transcriber, "effective_device", self.config.device)
        effective_compute_type = getattr(
            transcriber, "effective_compute_type", self.config.compute_type
        )
        fallback_reason = getattr(transcriber, "fallback_reason", None)
        fallback_occurred = getattr(transcriber, "fallback_occurred", fallback_reason is not None)
        if fallback_occurred:
            self._emit(
                EventType.WARNING,
                f"Inference fell back from {self.config.device} to {effective_device}",
                stage=Stage.TRANSCRIPTION,
                data={
                    "backend_fallback": True,
                    "requested_device": self.config.device,
                    "effective_device": effective_device,
                    "effective_compute_type": effective_compute_type,
                    "reason_code": fallback_reason,
                },
            )
        elif effective_device not in {self.config.device, "unknown"}:
            self._emit(
                EventType.PROGRESS,
                f"Inference backend selected {effective_device}",
                stage=Stage.TRANSCRIPTION,
                data={
                    "backend_selected": True,
                    "requested_device": self.config.device,
                    "effective_device": effective_device,
                    "effective_compute_type": effective_compute_type,
                },
            )
        for current, item in enumerate(pending, start=1):
            if self.cancel_event.is_set():
                break
            try:
                transcript = transcriber.transcribe(item.absolute_path)
                decision = evaluate_transcript(transcript, self.config)
                status = (
                    FileStatus.TRANSCRIPTION_PASSED
                    if decision.accepted
                    else FileStatus.TRANSCRIPTION_REJECTED
                )
                self.database.update_file(
                    self.job_id,
                    item.relative_path,
                    status=status,
                    reject_code=decision.code,
                    reject_detail=decision.detail,
                    transcription=transcript.text,
                    language=transcript.language,
                    no_speech_prob=transcript.no_speech_prob,
                )
                self._file_event(
                    Stage.TRANSCRIPTION,
                    item.relative_path,
                    decision.accepted,
                    current,
                    total,
                    decision.detail or transcript.text,
                )
            except Exception as exc:
                self.database.update_file(
                    self.job_id,
                    item.relative_path,
                    status=FileStatus.ERROR,
                    reject_code="transcription_error",
                    reject_detail=str(exc),
                )
                self._file_event(
                    Stage.TRANSCRIPTION, item.relative_path, False, current, total, str(exc)
                )

    def _rank_and_export(self) -> None:
        self._start_stage(Stage.RANKING, "Ranking eligible files")
        self.database.reset_selection(self.job_id)
        candidates = self.database.get_files(
            self.job_id, statuses=[FileStatus.TRANSCRIPTION_PASSED]
        )
        candidates.sort(
            key=lambda row: (
                rank_score(row["transcription"] or "", self.config.ideal_text_length),
                row["relative_path"].casefold(),
            )
        )
        selected = candidates[: self.config.top_n]
        for row in selected:
            score = rank_score(row["transcription"] or "", self.config.ideal_text_length)
            self.database.update_file(
                self.job_id, row["relative_path"], status=FileStatus.SELECTED, score=score
            )

        self._start_stage(Stage.EXPORT, "Exporting selected files")
        selected = self.database.get_files(self.job_id, statuses=[FileStatus.SELECTED])
        all_results = self.database.get_files(self.job_id)
        exported = export_selected(
            Path(self.config.source_dir).expanduser().resolve(),
            Path(self.config.output_dir).expanduser().resolve(),
            selected,
            all_results,
            job_id=self.job_id,
            config=self.config,
            events=self.database.get_events(self.job_id),
        )
        for relative_path, destination in exported.items():
            self.database.update_file(self.job_id, relative_path, exported_path=destination)
        self._emit(
            EventType.PROGRESS,
            f"Exported {len(exported)} files",
            stage=Stage.EXPORT,
            current=len(exported),
            total=len(exported),
        )

    def _cancelled(self) -> bool:
        if not self.cancel_event.is_set():
            return False
        self.database.set_job_state(self.job_id, JobStatus.CANCELLED)
        self._emit(EventType.CANCELLED, "Job cancelled")
        return True

    def _start_stage(self, stage: Stage, message: str) -> None:
        self.database.set_job_stage(self.job_id, stage)
        self._emit(EventType.STAGE_STARTED, message, stage=stage)

    def _file_event(
        self, stage: Stage, path: str, accepted: bool, current: int, total: int, detail: str | None
    ) -> None:
        self._emit(
            EventType.FILE_COMPLETED,
            detail or ("Accepted" if accepted else "Rejected"),
            stage=stage,
            current=current,
            total=total,
            relative_path=path,
            accepted=accepted,
        )

    def _emit(
        self,
        event_type: EventType,
        message: str,
        *,
        stage: Stage | str | None = None,
        current: int | None = None,
        total: int | None = None,
        relative_path: str | None = None,
        accepted: bool | None = None,
        data: dict | None = None,
    ) -> None:
        event = PipelineEvent(
            job_id=self.job_id,
            type=event_type,
            message=message,
            stage=str(stage) if stage else None,
            current=current,
            total=total,
            relative_path=relative_path,
            accepted=accepted,
            data=data or {},
        )
        self.database.add_event(event)
        self.event_sink(event)
