# -*- coding: utf-8 -*-
"""
core_pipeline/environment.py
=============================
环境诊断模块。

返回结构化的依赖与硬件诊断结果，供 CLI 和前端复用。
"""

import importlib.util
import subprocess
import sys

from .models import EnvironmentReport, QualityPreset
from .utils import find_ffmpeg


class EnvironmentChecker:
    """
    环境与硬件可用性诊断器。

    检测 Python、PyTorch、Whisper、FFmpeg 和可选 CUDA GPU。GPU 不可用时仍允许
    继续执行，只是会推荐更保守的预设。
    """

    def check(self) -> EnvironmentReport:
        """
        执行全套环境诊断，返回结构化报告。
        """
        report = EnvironmentReport()
        issues: list[str] = []

        report.python_version = sys.version.split()[0]
        report.python_ok = sys.version_info >= (3, 10)
        if not report.python_ok:
            issues.append(
                f"Python 版本为 {report.python_version}，建议使用 3.10 或更高版本"
            )

        if importlib.util.find_spec("torch") is not None:
            report.torch_available = True
            report.torch_version = "已安装 (未载入内存)"
        else:
            issues.append("PyTorch 未安装，请先安装 PyTorch (带 CUDA 支持)")

        report.cuda_available = False
        report.gpu_vram_mb = None
        report.gpu_name = "CPU"

        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            output = result.stdout.strip().split("\n")[0]
            if output and "," in output:
                name, vram_str = output.split(",", 1)
                report.gpu_name = name.strip()
                try:
                    report.gpu_vram_mb = int(vram_str.strip())
                    report.cuda_available = True
                except ValueError:
                    pass
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            issues.append("未检测到可用的 CUDA GPU 或 NVIDIA 驱动异常，Whisper 将以 CPU 模式运行（速度较慢）")

        if importlib.util.find_spec("whisper") is not None:
            report.whisper_available = True
        else:
            report.whisper_available = False
            issues.append("OpenAI Whisper 未安装，请执行: pip install openai-whisper")

        ffmpeg_path = find_ffmpeg()
        report.ffmpeg_path = ffmpeg_path
        if ffmpeg_path is None:
            issues.append(
                "未找到 FFmpeg 可执行文件，"
                "请将 ffmpeg.exe 放置在程序目录下或将其加入系统 PATH"
            )

        report.issues = issues
        report.all_ok = (
            report.python_ok
            and report.torch_available
            and report.whisper_available
            and report.ffmpeg_path is not None
        )

        return report

    @staticmethod
    def recommend_preset(report: EnvironmentReport) -> QualityPreset:
        """
        根据硬件配置自动推荐质量预设。

        推荐仅基于可用显存容量；缺少 GPU 时回退到性能优先。
        """
        if not report.cuda_available or report.gpu_vram_mb is None:
            return QualityPreset.PERFORMANCE

        vram = report.gpu_vram_mb
        if vram < 2048:
            return QualityPreset.PERFORMANCE
        if vram < 6144:
            return QualityPreset.BALANCED
        return QualityPreset.QUALITY
