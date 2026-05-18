# -*- coding: utf-8 -*-
"""
core_pipeline/physics_filter.py
================================
声学物理特征筛选引擎。

该阶段只处理廉价的声学指标，用于在 Whisper 推理前快速减少候选文件数量。
文件操作默认复制而不是移动，避免误删原始素材。
"""

import os
import shutil
import threading
from typing import Optional

import librosa
import numpy as np

from .models import PipelineConfig, StageResult, AudioFileResult, PipelineStage
from .callbacks import ProgressCallback
from .utils import ensure_directory, collect_audio_files, ManifestManager


class PhysicsFilter:
    """
    基于声学物理特征的音频粗筛引擎。

    流程：加载音频、检查时长、RMS 和频谱质心；全部通过后复制到
    `physics_passed`。这一层不做语义判断，只负责筛掉明显不可用的片段。
    """

    PASS_DIR_NAME = "physics_passed"

    def __init__(
        self,
        config: PipelineConfig,
        callback: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
    ):
        """
        初始化物理筛选引擎。

        参数:
            config:       管线配置（包含阈值、路径等全部参数）
            callback:     进度回调实例（可选，为 None 则静默运行）
            cancel_event: 取消信号（可选，UI 线程可通过 set() 中断处理）
        """
        self._config = config
        self._callback = callback
        self._cancel = cancel_event

        self._pass_dir = os.path.join(config.output_dir, self.PASS_DIR_NAME)

    def run(self) -> StageResult:
        """
        执行物理筛选阶段。

        返回:
            StageResult 结构体，包含通过/淘汰/出错的数量及每个文件的详细结果。
        """
        stage_name = PipelineStage.PHYSICS_FILTER.value
        result = StageResult(stage=PipelineStage.PHYSICS_FILTER)

        ensure_directory(self._pass_dir)

        files = collect_audio_files(self._config.source_dir)
        if not files:
            self._log("WARNING", f"源目录中未找到音频文件: {self._config.source_dir}")
            return result

        manifest: Optional[ManifestManager] = None
        if self._config.enable_resume:
            manifest = ManifestManager(self._config.output_dir, stage_name)

        total = len(files)
        self._notify_stage_start(stage_name, total)

        for idx, filename in enumerate(files, start=1):
            if self._cancel is not None and self._cancel.is_set():
                self._log("INFO", "收到取消信号，物理筛选阶段提前终止")
                break

            restored = (
                self._restore_from_manifest(manifest, filename, result)
                if manifest is not None
                else None
            )
            if restored is not None:
                self._notify_item_done(
                    stage_name,
                    idx,
                    total,
                    filename,
                    restored.accepted,
                    restored.reject_reason or "已处理",
                )
                continue

            file_path = os.path.join(self._config.source_dir, filename)
            file_result = self._process_single_file(file_path, filename)
            result.details.append(file_result)

            if file_result.accepted:
                result.accepted_count += 1
                result.accepted_files.append(filename)
            elif file_result.reject_reason and file_result.reject_reason != "ERROR":
                result.rejected_count += 1
            else:
                result.error_count += 1

            result.total_processed += 1

            if manifest is not None:
                manifest.mark_done(
                    filename,
                    file_result.accepted,
                    metadata={
                        "reject_reason": file_result.reject_reason,
                        "duration": file_result.duration,
                        "rms": file_result.rms,
                        "spectral_centroid": file_result.spectral_centroid,
                    },
                )

            detail = file_result.reject_reason or ""
            self._notify_item_done(
                stage_name, idx, total, filename, file_result.accepted, detail
            )

        stats = {
            "total_processed": result.total_processed,
            "accepted": result.accepted_count,
            "rejected": result.rejected_count,
            "errors": result.error_count,
        }
        self._notify_stage_end(stage_name, stats)

        return result

    def _process_single_file(self, file_path: str, filename: str) -> AudioFileResult:
        """
        对单个音频文件执行三重物理指标检查。

        检查顺序按计算成本递增排列，先用时长与 RMS 淘汰明显失败的文件，
        只有必要时才计算频谱质心。
        """
        try:
            y, sr = librosa.load(file_path, sr=None)

            duration = librosa.get_duration(y=y, sr=sr)
            if duration < self._config.min_duration:
                return AudioFileResult(
                    filename=filename,
                    accepted=False,
                    reject_reason=f"时长过短 ({duration:.2f}s < {self._config.min_duration}s)",
                    duration=duration,
                )

            rms = float(np.mean(librosa.feature.rms(y=y)))
            if rms < self._config.min_rms:
                return AudioFileResult(
                    filename=filename,
                    accepted=False,
                    reject_reason=f"能量过低 (RMS={rms:.4f} < {self._config.min_rms})",
                    duration=duration,
                    rms=rms,
                )

            centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
            if centroid < self._config.min_centroid:
                return AudioFileResult(
                    filename=filename,
                    accepted=False,
                    reject_reason=f"音色过闷 (质心={centroid:.0f}Hz < {self._config.min_centroid}Hz)",
                    duration=duration,
                    rms=rms,
                    spectral_centroid=centroid,
                )

            dest = os.path.join(self._pass_dir, filename)
            if self._config.destructive:
                shutil.move(file_path, dest)
            else:
                shutil.copy2(file_path, dest)

            return AudioFileResult(
                filename=filename,
                accepted=True,
                duration=duration,
                rms=rms,
                spectral_centroid=centroid,
            )

        except Exception as e:
            self._log("ERROR", f"处理文件失败 [{filename}]: {e}")
            return AudioFileResult(
                filename=filename,
                accepted=False,
                reject_reason=f"ERROR: {e}",
            )

    def _restore_from_manifest(
        self,
        manifest: ManifestManager,
        filename: str,
        result: StageResult,
    ) -> Optional[AudioFileResult]:
        record = manifest.get_record(filename)
        if record is None:
            return None

        accepted = bool(record.get("accepted"))
        file_result = AudioFileResult(
            filename=filename,
            accepted=accepted,
            reject_reason=record.get("reject_reason"),
            duration=record.get("duration"),
            rms=record.get("rms"),
            spectral_centroid=record.get("spectral_centroid"),
        )
        result.details.append(file_result)
        result.total_processed += 1
        if accepted:
            result.accepted_count += 1
            result.accepted_files.append(filename)
        elif file_result.reject_reason and file_result.reject_reason != "ERROR":
            result.rejected_count += 1
        else:
            result.error_count += 1
        return file_result

    def _log(self, level: str, message: str) -> None:
        if self._callback is not None:
            self._callback.on_log(level, message)

    def _notify_stage_start(self, stage: str, total: int) -> None:
        if self._callback is not None:
            self._callback.on_stage_start(stage, total)

    def _notify_item_done(
        self, stage: str, current: int, total: int,
        item_name: str, accepted: bool, detail: str = ""
    ) -> None:
        if self._callback is not None:
            self._callback.on_item_done(
                stage, current, total, item_name, accepted, detail
            )

    def _notify_stage_end(self, stage: str, stats: dict) -> None:
        if self._callback is not None:
            self._callback.on_stage_end(stage, stats)
