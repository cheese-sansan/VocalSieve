# -*- coding: utf-8 -*-
"""
core_pipeline/whisper_filter.py
================================
基于 Whisper 的语义特征精筛引擎。

该阶段加载 Whisper 模型并执行转录，再按语音置信度、文本长度、重复字符
和幻觉关键词做精筛。通过规则的候选会按文本长度稳定性排序，最终复制到
`final_selected`。
"""

import os
import re
import shutil
import threading
from typing import Optional

from .models import (
    PipelineConfig, StageResult, AudioFileResult, PipelineStage,
)
from .callbacks import ProgressCallback
from .utils import ensure_directory, collect_audio_files, ManifestManager


# Whisper 对纯音乐、环境音和极短片段可能产生固定模板文本，这里集中维护常见模式。
HALLUCINATION_KEYWORDS: list[str] = [
    "Subtitle",
    "字幕",
    "視聴",
    "ご視聴",
    "チャンネル登録",
    "Subscribe",
    "..",
]


def _contains_repeating_chars(text: str, threshold: int = 4) -> bool:
    """
    检测文本中是否包含连续重复的字符。

    参数:
        text:      待检测的文本
        threshold: 连续重复次数阈值
    """
    pattern = r"(.)\1{" + str(threshold - 1) + r",}"
    return re.search(pattern, text) is not None


class WhisperFilter:
    """
    基于 OpenAI Whisper 的语义特征精筛引擎。

    Whisper 推理成本高，因此该阶段只处理物理筛选通过的候选文件。
    """

    OUTPUT_DIR_NAME = "final_selected"
    LOG_FILENAME = "transcription_log.txt"

    def __init__(
        self,
        config: PipelineConfig,
        callback: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
    ):
        self._config = config
        self._callback = callback
        self._cancel = cancel_event

        # 最终输出目录：output_dir/final_selected/
        self._output_dir = os.path.join(config.output_dir, self.OUTPUT_DIR_NAME)
        self._model = None
        self._device = "cpu"

    def run(self, source_dir: str) -> StageResult:
        """
        执行 Whisper 语义精筛阶段。

        参数:
            source_dir: 待筛选文件所在目录
                        （通常是物理筛选阶段的输出目录 physics_passed/）

        返回:
            StageResult 结构体

        首次调用会加载模型权重，耗时取决于模型规格和本机缓存状态。
        """
        stage_name = PipelineStage.WHISPER_FILTER.value
        result = StageResult(stage=PipelineStage.WHISPER_FILTER)

        ensure_directory(self._output_dir)

        if not self._load_model():
            return result

        files = collect_audio_files(source_dir)
        if not files:
            self._log("WARNING", f"物理筛选输出目录中无音频文件: {source_dir}")
            return result

        manifest: Optional[ManifestManager] = None
        if self._config.enable_resume:
            manifest = ManifestManager(self._config.output_dir, stage_name)

        total = len(files)
        self._notify_stage_start(stage_name, total)

        candidates: list[AudioFileResult] = []

        for idx, filename in enumerate(files, start=1):
            if self._cancel is not None and self._cancel.is_set():
                self._log("INFO", "收到取消信号，Whisper 筛选阶段提前终止")
                break

            restored = (
                self._restore_from_manifest(manifest, filename, result, candidates)
                if manifest is not None
                else None
            )
            if restored is not None:
                detail = restored.transcription or restored.reject_reason or "已处理"
                self._notify_item_done(
                    stage_name, idx, total, filename, restored.accepted, detail
                )
                continue

            file_path = os.path.join(source_dir, filename)
            file_result = self._process_single_file(file_path, filename)
            result.details.append(file_result)
            result.total_processed += 1

            if file_result.accepted:
                candidates.append(file_result)
            elif file_result.reject_reason and "ERROR" in (file_result.reject_reason or ""):
                result.error_count += 1
            else:
                result.rejected_count += 1

            if manifest is not None:
                manifest.mark_done(
                    filename,
                    file_result.accepted,
                    metadata={
                        "reject_reason": file_result.reject_reason,
                        "transcription": file_result.transcription,
                        "no_speech_prob": file_result.no_speech_prob,
                        "detected_language": file_result.detected_language,
                    },
                )

            detail = file_result.transcription or file_result.reject_reason or ""
            self._notify_item_done(
                stage_name, idx, total, filename, file_result.accepted, detail
            )

        self._log("INFO", f"初筛合格: {len(candidates)} 个，正在排序取 Top-{self._config.top_n}")

        ideal = self._config.ideal_text_length
        candidates.sort(key=lambda x: abs(len(x.transcription or "") - ideal))

        final = candidates[:self._config.top_n]

        log_path = os.path.join(self._output_dir, self.LOG_FILENAME)
        with open(log_path, "w", encoding="utf-8") as log_f:
            for item in final:
                src = os.path.join(source_dir, item.filename)
                dst = os.path.join(self._output_dir, item.filename)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                log_f.write(f"{item.filename}: {item.transcription}\n")
                result.accepted_files.append(item.filename)

        result.accepted_count = len(final)

        stats = {
            "total_processed": result.total_processed,
            "candidates_passed_rules": len(candidates),
            "final_selected": result.accepted_count,
            "rejected": result.rejected_count,
            "errors": result.error_count,
        }
        self._notify_stage_end(stage_name, stats)

        return result

    def _load_model(self) -> bool:
        """
        加载 Whisper 模型到 GPU 或 CPU。

        返回:
            True 加载成功，False 加载失败
        """
        try:
            import torch
            import whisper
        except ImportError as e:
            self._log("ERROR", f"缺少依赖库: {e}")
            return False

        model_name = self._config.resolve_whisper_model()
        self._log("INFO", f"正在加载 Whisper 模型: {model_name}")

        if self._config.use_gpu and torch.cuda.is_available():
            device = "cuda"
            self._log("INFO", f"GPU 加速已启用: {torch.cuda.get_device_name(0)}")
        else:
            device = "cpu"
            self._log("WARNING", "将使用 CPU 运行 Whisper（速度较慢）")

        try:
            self._model = whisper.load_model(model_name, device=device)
            self._device = device
            self._log("INFO", "Whisper 模型加载完成")
            return True
        except Exception as e:
            self._log("ERROR", f"Whisper 模型加载失败: {e}")
            return False

    def _process_single_file(self, file_path: str, filename: str) -> AudioFileResult:
        """
        对单个音频文件执行 Whisper 转录并应用五重筛选规则。

        规则按常见淘汰原因排列，尽早返回可以减少后续判断成本。
        """
        try:
            transcribe_kwargs = {
                "fp16": (self._device == "cuda"),
            }
            if self._config.target_language != "auto":
                transcribe_kwargs["language"] = self._config.target_language

            result = self._model.transcribe(file_path, **transcribe_kwargs)
            text = result["text"].strip()

            segments = result.get("segments", [])
            no_speech_prob = segments[0]["no_speech_prob"] if segments else 1.0

            detected_lang = result.get("language", None)

            if no_speech_prob > self._config.no_speech_threshold:
                return AudioFileResult(
                    filename=filename, accepted=False,
                    reject_reason=f"非人声 (no_speech={no_speech_prob:.2f})",
                    no_speech_prob=no_speech_prob,
                    detected_language=detected_lang,
                )

            if len(text) < self._config.min_text_length:
                return AudioFileResult(
                    filename=filename, accepted=False,
                    reject_reason=f"文本过短 ({len(text)} 字)",
                    transcription=text,
                    no_speech_prob=no_speech_prob,
                    detected_language=detected_lang,
                )

            if len(text) > self._config.max_text_length:
                return AudioFileResult(
                    filename=filename, accepted=False,
                    reject_reason=f"文本过长 ({len(text)} 字)",
                    transcription=text,
                    no_speech_prob=no_speech_prob,
                    detected_language=detected_lang,
                )

            if _contains_repeating_chars(text, self._config.repeat_char_threshold):
                return AudioFileResult(
                    filename=filename, accepted=False,
                    reject_reason="检测到连续重复字符（疑似尖叫/杂音）",
                    transcription=text,
                    no_speech_prob=no_speech_prob,
                    detected_language=detected_lang,
                )

            for keyword in HALLUCINATION_KEYWORDS:
                if keyword in text:
                    return AudioFileResult(
                        filename=filename, accepted=False,
                        reject_reason=f"命中幻觉关键词: '{keyword}'",
                        transcription=text,
                        no_speech_prob=no_speech_prob,
                        detected_language=detected_lang,
                    )

            return AudioFileResult(
                filename=filename, accepted=True,
                transcription=text,
                no_speech_prob=no_speech_prob,
                detected_language=detected_lang,
            )

        except Exception as e:
            return AudioFileResult(
                filename=filename, accepted=False,
                reject_reason=f"ERROR: {e}",
            )

    def _restore_from_manifest(
        self,
        manifest: ManifestManager,
        filename: str,
        result: StageResult,
        candidates: list[AudioFileResult],
    ) -> Optional[AudioFileResult]:
        record = manifest.get_record(filename)
        if record is None:
            return None

        accepted = bool(record.get("accepted"))
        file_result = AudioFileResult(
            filename=filename,
            accepted=accepted,
            reject_reason=record.get("reject_reason"),
            transcription=record.get("transcription"),
            no_speech_prob=record.get("no_speech_prob"),
            detected_language=record.get("detected_language"),
        )

        result.details.append(file_result)
        result.total_processed += 1
        if accepted:
            candidates.append(file_result)
        elif file_result.reject_reason and "ERROR" in file_result.reject_reason:
            result.error_count += 1
        else:
            result.rejected_count += 1

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
