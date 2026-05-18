# -*- coding: utf-8 -*-
"""
core_pipeline/pipeline.py
==========================
管线编排器。

调用方只需要创建 Pipeline 并执行 run()。内部按固定顺序完成环境诊断、
声学粗筛和 Whisper 精筛，并把阶段结果汇总为 PipelineResult。
"""

import os
import threading
from typing import Optional

from .models import PipelineConfig, PipelineResult, PipelineStage
from .callbacks import ProgressCallback, ConsoleCallback
from .environment import EnvironmentChecker
from .physics_filter import PhysicsFilter
from .whisper_filter import WhisperFilter
from .utils import ensure_directory, ensure_ffmpeg_in_path


class Pipeline:
    """
    音频筛选管线编排器。

    使用方式:
        config = PipelineConfig(source_dir="...", output_dir="...")
        pipeline = Pipeline(config)
        result = pipeline.run()          # 同步阻塞执行
        pipeline.cancel()                # 从另一个线程调用以中断

    run() 应在工作线程中调用；cancel() 可从 UI 主线程触发。
    """

    def __init__(
        self,
        config: PipelineConfig,
        callback: Optional[ProgressCallback] = None,
    ):
        """
        初始化管线编排器。

        参数:
            config:   管线配置
            callback: 进度回调（为 None 时自动使用 ConsoleCallback）
        """
        self._config = config
        self._callback = callback if callback is not None else ConsoleCallback()
        self._cancel_event = threading.Event()

    def run(self) -> PipelineResult:
        """
        执行完整的音频筛选管线。

        执行顺序：
        1. 环境诊断 -- 检查所有依赖是否就绪
        2. 物理粗筛 -- 按声学特征快速淘汰明显不合格的文件
        3. Whisper 精筛 -- 对物理通过的文件做语义分析，取 Top-N

        返回:
            PipelineResult 结构体，包含全部阶段的结果

        业务错误会写入 PipelineResult.error_message，不直接向 UI 层抛出。
        """
        result = PipelineResult(config=self._config)

        try:
            self._callback.on_log("INFO", "开始环境诊断...")
            checker = EnvironmentChecker()
            env_report = checker.check()
            result.environment = env_report

            if not env_report.all_ok:
                for issue in env_report.issues:
                    self._callback.on_log("WARNING", issue)
                if not env_report.torch_available or not env_report.whisper_available:
                    result.error_message = "核心依赖缺失，无法继续"
                    self._callback.on_log("ERROR", result.error_message)
                    return result
                if env_report.ffmpeg_path is None:
                    result.error_message = "FFmpeg 未找到，Whisper 无法解码音频"
                    self._callback.on_log("ERROR", result.error_message)
                    return result

            ensure_ffmpeg_in_path()

            if not os.path.isdir(self._config.source_dir):
                result.error_message = f"源目录不存在: {self._config.source_dir}"
                self._callback.on_log("ERROR", result.error_message)
                return result

            ensure_directory(self._config.output_dir)

            if self._cancel_event.is_set():
                result.cancelled = True
                return result

            self._callback.on_log("INFO", "启动物理筛选阶段...")
            physics = PhysicsFilter(
                self._config, self._callback, self._cancel_event
            )
            physics_result = physics.run()
            result.physics_result = physics_result

            if self._cancel_event.is_set():
                result.cancelled = True
                return result

            if physics_result.accepted_count == 0:
                result.error_message = "物理筛选阶段未通过任何文件，无法进入 Whisper 阶段"
                self._callback.on_log("WARNING", result.error_message)
                return result

            self._callback.on_log("INFO", "启动 Whisper 语义筛选阶段...")

            physics_output = os.path.join(
                self._config.output_dir, PhysicsFilter.PASS_DIR_NAME
            )
            whisper = WhisperFilter(
                self._config, self._callback, self._cancel_event
            )
            whisper_result = whisper.run(source_dir=physics_output)
            result.whisper_result = whisper_result

            if self._cancel_event.is_set():
                result.cancelled = True
                return result

            result.final_output_dir = os.path.join(
                self._config.output_dir, WhisperFilter.OUTPUT_DIR_NAME
            )
            result.success = True
            self._callback.on_log(
                "INFO",
                f"管线执行完毕，最终选取 {whisper_result.accepted_count} 个文件 "
                f"-> {result.final_output_dir}"
            )

        except Exception as e:
            result.error_message = f"管线执行过程中发生未预期的异常: {e}"
            self._callback.on_log("ERROR", result.error_message)

        return result

    def cancel(self) -> None:
        """
        发送取消信号，中断当前正在执行的管线。

        当前文件处理结束后，阶段循环会检查该信号并退出。
        """
        self._cancel_event.set()
        self._callback.on_log("INFO", "取消信号已发送，等待当前文件处理完毕后退出...")
