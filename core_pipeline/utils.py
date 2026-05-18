# -*- coding: utf-8 -*-
"""
core_pipeline/utils.py
======================
管线基础工具。

这里放置跨阶段共享的小型基础能力：FFmpeg 定位、目录创建、音频文件收集
以及断点清单管理。业务阶段只依赖这些稳定接口，避免重复处理文件系统细节。
"""

import os
import sys
import json
import shutil
import time
from pathlib import Path
from typing import Any, Optional

from .models import AUDIO_EXTENSIONS


# ---------------------------------------------------------------------------
# FFmpeg 定位
# ---------------------------------------------------------------------------

def find_ffmpeg() -> Optional[str]:
    """
    查找 FFmpeg 可执行文件。

    优先使用随应用打包或放在项目根目录的 `ffmpeg.exe`，找不到时再回退到
    系统 PATH。返回 None 表示调用方需要给出明确的依赖错误。
    """
    if hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.isfile(bundled):
            return bundled

    package_parent = Path(__file__).resolve().parent.parent
    local_ffmpeg = package_parent / "ffmpeg.exe"
    if local_ffmpeg.is_file():
        return str(local_ffmpeg)

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg is not None:
        return system_ffmpeg

    return None


def ensure_ffmpeg_in_path() -> Optional[str]:
    """
    将 FFmpeg 所在目录注入当前进程 PATH。

    返回:
        FFmpeg 的完整路径，如果未找到则返回 None。
    """
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path is None:
        return None

    ffmpeg_dir = os.path.dirname(os.path.abspath(ffmpeg_path))
    current_path = os.environ.get("PATH", "")
    path_parts = [
        os.path.normcase(os.path.abspath(item))
        for item in current_path.split(os.pathsep)
        if item
    ]
    if os.path.normcase(ffmpeg_dir) not in path_parts:
        os.environ["PATH"] = os.pathsep.join([ffmpeg_dir, current_path])

    return ffmpeg_path


# ---------------------------------------------------------------------------
# 目录操作
# ---------------------------------------------------------------------------

def ensure_directory(path: str) -> str:
    """
    确保目录存在并返回绝对路径。

    参数:
        path: 目标目录路径
    """
    abs_path = os.path.abspath(path)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def collect_audio_files(directory: str) -> list[str]:
    """
    收集目录第一层的受支持音频文件名。

    参数:
        directory: 要扫描的目录路径
    """
    if not os.path.isdir(directory):
        return []

    files = [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
        and os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS
    ]
    files.sort()
    return files


# ---------------------------------------------------------------------------
# 断点续传清单管理器
# ---------------------------------------------------------------------------

class ManifestManager:
    """
    断点续传清单管理器。

    每个阶段维护一个 JSONL 文件。追加写入可以降低崩溃时损坏整份清单的风险，
    读取时保留 accepted 与元数据，便于续跑时恢复阶段统计。
    """

    # 清单文件名，以点号开头表示隐藏文件
    MANIFEST_FILENAME = ".pipeline_manifest.jsonl"

    def __init__(self, output_dir: str, stage: str):
        """
        初始化清单管理器。

        参数:
            output_dir: 输出目录路径（清单文件将存储在此目录中）
            stage:      当前管线阶段名称（用于区分不同阶段的记录）
        """
        self._stage = stage
        filename = f".manifest_{stage}.jsonl"
        self._path = os.path.join(output_dir, filename)
        self._records: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """
        从磁盘加载已有的清单记录。

        最后一行可能在进程中断时没有写完整，解析失败时直接跳过该行。
        """
        if not os.path.isfile(self._path):
            return

        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    filename = record["filename"]
                    if isinstance(filename, str):
                        self._records[filename] = record
                except (json.JSONDecodeError, KeyError):
                    continue

    def is_processed(self, filename: str) -> bool:
        """检查某个文件是否已在之前的运行中处理过。"""
        return filename in self._records

    def get_record(self, filename: str) -> Optional[dict[str, Any]]:
        """返回某个文件的清单记录副本。"""
        record = self._records.get(filename)
        return record.copy() if record is not None else None

    def mark_done(
        self,
        filename: str,
        accepted: bool,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        标记一个文件为已处理，并立即追加写入磁盘。

        参数:
            filename: 已处理的文件名
            accepted: 该文件是否通过了筛选
            metadata: 可选的阶段细节，例如淘汰原因或转录文本
        """
        if filename in self._records:
            return

        record = {
            "filename": filename,
            "stage": self._stage,
            "accepted": accepted,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if metadata:
            record.update(metadata)

        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        self._records[filename] = record

    def get_processed_set(self) -> set[str]:
        """返回已处理文件名的集合（副本）。"""
        return set(self._records)

    def clear(self) -> None:
        """清空清单（用于用户主动选择"从头开始"时）。"""
        self._records.clear()
        if os.path.isfile(self._path):
            os.remove(self._path)
