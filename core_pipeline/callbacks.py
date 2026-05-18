# -*- coding: utf-8 -*-
"""
core_pipeline/callbacks.py
==========================
进度回调协议定义模块。

后端通过该协议向 CLI 或 PyWebview 前端上报阶段、文件进度和日志。
Protocol 允许调用方只实现同名方法，不需要继承具体基类。
"""

import sys
from typing import Protocol, runtime_checkable


def _safe_print(message: str = "") -> None:
    """Write CLI logs without letting console encoding errors stop a run."""
    text = f"{message}\n"
    stream = sys.stdout
    try:
        stream.write(text)
    except UnicodeEncodeError:
        encoding = stream.encoding or "utf-8"
        stream.write(text.encode(encoding, errors="replace").decode(encoding))
    stream.flush()


@runtime_checkable
class ProgressCallback(Protocol):
    """
    进度回调协议。

    实现以下方法的对象都可作为管线回调。
    """

    def on_stage_start(self, stage: str, total: int) -> None:
        """阶段开始时触发。"""
        ...

    def on_item_done(
        self,
        stage: str,
        current: int,
        total: int,
        item_name: str,
        accepted: bool,
        detail: str = "",
    ) -> None:
        """单个文件处理完成时触发。"""
        ...

    def on_stage_end(self, stage: str, stats: dict) -> None:
        """阶段结束时触发。"""
        ...

    def on_log(self, level: str, message: str) -> None:
        """输出一条日志。"""
        ...


class ConsoleCallback:
    """
    默认的控制台回调实现。

    CLI 模式下使用，保持与前端回调相同的事件粒度。
    """

    def on_stage_start(self, stage: str, total: int) -> None:
        """打印阶段开始信息。"""
        _safe_print(f"\n{'=' * 50}")
        _safe_print(f"[{stage}] 开始处理，共 {total} 个文件")
        _safe_print(f"{'=' * 50}")

    def on_item_done(
        self,
        stage: str,
        current: int,
        total: int,
        item_name: str,
        accepted: bool,
        detail: str = "",
    ) -> None:
        """打印单文件处理进度。"""
        pct = (current / total * 100) if total > 0 else 0
        status = "PASS" if accepted else "FAIL"
        suffix = f" | {detail}" if detail else ""
        _safe_print(f"  [{current}/{total}] ({pct:5.1f}%) {status} {item_name}{suffix}")

    def on_stage_end(self, stage: str, stats: dict) -> None:
        """打印阶段汇总。"""
        _safe_print(f"\n[{stage}] 阶段完成:")
        for key, value in stats.items():
            _safe_print(f"  {key}: {value}")
        _safe_print(f"{'=' * 50}")

    def on_log(self, level: str, message: str) -> None:
        """打印日志行。"""
        _safe_print(f"[{level}] {message}")

