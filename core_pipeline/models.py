# -*- coding: utf-8 -*-
"""
core_pipeline/models.py
=======================
管线数据模型。

这里集中定义配置、阶段结果与环境报告，业务逻辑通过这些结构化对象交换数据。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class QualityPreset(Enum):
    """Whisper 模型规格预设。"""
    PERFORMANCE = "performance"
    BALANCED = "balanced"
    QUALITY = "quality"


class PipelineStage(Enum):
    """进度回调使用的阶段标识。"""
    ENVIRONMENT_CHECK = "environment_check"
    PHYSICS_FILTER = "physics_filter"
    WHISPER_FILTER = "whisper_filter"


PRESET_MODEL_MAP: dict[QualityPreset, str] = {
    QualityPreset.PERFORMANCE: "tiny",
    QualityPreset.BALANCED: "small",
    QualityPreset.QUALITY: "medium",
}

# UI 默认展示的常用语种。Whisper 仍可接受更多合法语种代码。
SUPPORTED_LANGUAGES: list[dict[str, str]] = [
    {"code": "auto", "name": "自动检测"},
    {"code": "ja",   "name": "日语"},
    {"code": "zh",   "name": "中文"},
    {"code": "en",   "name": "英语"},
    {"code": "ko",   "name": "韩语"},
    {"code": "de",   "name": "德语"},
    {"code": "fr",   "name": "法语"},
    {"code": "es",   "name": "西班牙语"},
    {"code": "ru",   "name": "俄语"},
    {"code": "it",   "name": "意大利语"},
    {"code": "pt",   "name": "葡萄牙语"},
]

AUDIO_EXTENSIONS: tuple[str, ...] = (".ogg", ".wav", ".flac", ".mp3", ".m4a")


@dataclass
class PipelineConfig:
    """
    管线配置结构体。

    source_dir 与 output_dir 由调用方显式提供，其余字段提供适合常规语料筛选的
    默认值。whisper_model 可覆盖 preset 映射。
    """

    source_dir: str
    output_dir: str

    preset: QualityPreset = QualityPreset.BALANCED

    min_rms: float = 0.015
    min_centroid: float = 1000.0
    min_duration: float = 0.4

    whisper_model: Optional[str] = None
    target_language: str = "auto"
    top_n: int = 1200
    ideal_text_length: int = 10
    no_speech_threshold: float = 0.45
    min_text_length: int = 2
    max_text_length: int = 40
    repeat_char_threshold: int = 4

    use_gpu: bool = True
    destructive: bool = False
    enable_resume: bool = True

    def resolve_whisper_model(self) -> str:
        """解析最终使用的 Whisper 模型名称。"""
        if self.whisper_model is not None:
            return self.whisper_model
        return PRESET_MODEL_MAP[self.preset]


@dataclass
class EnvironmentReport:
    """环境诊断报告。"""
    python_version: str = ""
    python_ok: bool = False
    torch_available: bool = False
    torch_version: Optional[str] = None
    cuda_available: bool = False
    gpu_name: Optional[str] = None
    gpu_vram_mb: Optional[int] = None
    whisper_available: bool = False
    ffmpeg_path: Optional[str] = None
    all_ok: bool = False
    issues: List[str] = field(default_factory=list)


@dataclass
class AudioFileResult:
    """单个音频文件的处理结果。"""
    filename: str
    accepted: bool
    reject_reason: Optional[str] = None

    duration: Optional[float] = None
    rms: Optional[float] = None
    spectral_centroid: Optional[float] = None

    transcription: Optional[str] = None
    no_speech_prob: Optional[float] = None
    detected_language: Optional[str] = None


@dataclass
class StageResult:
    """单个管线阶段的汇总结果。"""
    stage: PipelineStage
    total_processed: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    error_count: int = 0
    accepted_files: List[str] = field(default_factory=list)
    details: List[AudioFileResult] = field(default_factory=list)


@dataclass
class PipelineResult:
    """完整管线的最终输出结果。"""
    config: Optional[PipelineConfig] = None
    environment: Optional[EnvironmentReport] = None
    physics_result: Optional[StageResult] = None
    whisper_result: Optional[StageResult] = None
    final_output_dir: Optional[str] = None
    success: bool = False
    cancelled: bool = False
    error_message: Optional[str] = None
