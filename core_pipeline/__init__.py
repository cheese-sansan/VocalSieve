# -*- coding: utf-8 -*-
"""
core_pipeline/__init__.py
==========================
核心管线库的包入口。

只暴露 CLI 与 UI 需要使用的顶层 API，阶段内部实现保持在包内。
"""

from .models import (
    PipelineConfig,
    PipelineResult,
    QualityPreset,
    PipelineStage,
    EnvironmentReport,
    StageResult,
    AudioFileResult,
    PRESET_MODEL_MAP,
    SUPPORTED_LANGUAGES,
    AUDIO_EXTENSIONS,
)
from .callbacks import ProgressCallback, ConsoleCallback
from .pipeline import Pipeline
from .environment import EnvironmentChecker

__all__ = [
    # 核心 API
    "Pipeline",
    "PipelineConfig",
    "PipelineResult",
    # 枚举与常量
    "QualityPreset",
    "PipelineStage",
    "PRESET_MODEL_MAP",
    "SUPPORTED_LANGUAGES",
    "AUDIO_EXTENSIONS",
    # 结果结构体
    "EnvironmentReport",
    "StageResult",
    "AudioFileResult",
    # 回调
    "ProgressCallback",
    "ConsoleCallback",
    # 工具
    "EnvironmentChecker",
]
