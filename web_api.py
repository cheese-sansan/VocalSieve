# -*- coding: utf-8 -*-
"""
web_api.py
==========
前端与后端的桥接层 (Web API)。

`VocalSieveApi` 暴露给 PyWebview 前端调用；`WebViewCallback` 负责把后端
进度事件转发给浏览器环境中的回调函数。
"""

import json
import os
import threading
from typing import Dict, Any, Optional

import webview

from core_pipeline import (
    Pipeline,
    PipelineConfig,
    QualityPreset,
    EnvironmentChecker,
    SUPPORTED_LANGUAGES,
)


class WebViewCallback:
    """将管线进度事件转发给前端 JS 回调。"""

    def __init__(self, window: webview.Window):
        self.window = window

    def _emit(self, handler: str, *args: Any) -> None:
        args_json = ", ".join(json.dumps(arg, ensure_ascii=False) for arg in args)
        script = f"if (window.{handler}) window.{handler}({args_json});"
        self.window.evaluate_js(script)

    def on_stage_start(self, stage: str, total: int) -> None:
        self._emit("onStageStart", stage, total)

    def on_item_done(
        self, stage: str, current: int, total: int,
        item_name: str, accepted: bool, detail: str = ""
    ) -> None:
        self._emit("onItemDone", stage, current, total, item_name, accepted, detail)

    def on_stage_end(self, stage: str, stats: dict) -> None:
        self._emit("onStageEnd", stage, stats)

    def on_log(self, level: str, message: str) -> None:
        self._emit("onLog", level, message)


class VocalSieveApi:
    """暴露给前端的 Python API 对象。"""

    def __init__(self):
        self.window: Optional[webview.Window] = None
        self._pipeline: Optional[Pipeline] = None
        self._pipeline_thread: Optional[threading.Thread] = None

    def set_window(self, window: webview.Window) -> None:
        self.window = window

    def select_directory(self) -> str:
        """打开 Windows 原生目录选择对话框。"""
        import ctypes
        from ctypes import wintypes
        
        class BROWSEINFO(ctypes.Structure):
            _fields_ = [("hwndOwner", wintypes.HWND),
                        ("pidlRoot", wintypes.LPCVOID),
                        ("pszDisplayName", wintypes.LPWSTR),
                        ("lpszTitle", wintypes.LPWSTR),
                        ("ulFlags", wintypes.UINT),
                        ("lpfn", wintypes.LPCVOID),
                        ("lParam", wintypes.LPARAM),
                        ("iImage", ctypes.c_int)]

        BIF_RETURNONLYFSDIRS = 0x0001
        BIF_NEWDIALOGSTYLE = 0x0040

        ctypes.windll.ole32.CoInitialize(None)
        try:
            bi = BROWSEINFO()
            bi.lpszTitle = "请选择音频文件夹"
            bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE

            pidl = ctypes.windll.shell32.SHBrowseForFolderW(ctypes.byref(bi))
            if not pidl:
                return ""

            try:
                path = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
                if ctypes.windll.shell32.SHGetPathFromIDListW(pidl, path):
                    return path.value
            finally:
                ctypes.windll.ole32.CoTaskMemFree(pidl)
            return ""
        finally:
            ctypes.windll.ole32.CoUninitialize()

    def get_supported_languages(self) -> list:
        return SUPPORTED_LANGUAGES

    def get_environment(self) -> Dict[str, Any]:
        """获取系统环境信息。"""
        checker = EnvironmentChecker()
        report = checker.check()
        preset = checker.recommend_preset(report)
        return {
            "python_ok": report.python_ok,
            "python_version": report.python_version,
            "torch_available": report.torch_available,
            "cuda_available": report.cuda_available,
            "gpu_name": report.gpu_name or "CPU",
            "whisper_available": report.whisper_available,
            "ffmpeg_found": report.ffmpeg_path is not None,
            "all_ok": report.all_ok,
            "issues": report.issues,
            "recommended_preset": preset.value
        }

    def start_pipeline(self, config_dict: Dict[str, Any]) -> str:
        """启动筛选任务。"""
        if self._pipeline_thread and self._pipeline_thread.is_alive():
            return "Task is already running"
        
        try:
            preset_str = config_dict.get("preset", "balanced")
            preset_map = {
                "performance": QualityPreset.PERFORMANCE,
                "balanced": QualityPreset.BALANCED,
                "quality": QualityPreset.QUALITY,
            }
            preset = preset_map.get(preset_str, QualityPreset.BALANCED)

            config = PipelineConfig(
                source_dir=config_dict.get("source_dir", ""),
                output_dir=config_dict.get("output_dir", ""),
                preset=preset,
                target_language=config_dict.get("target_language", "auto"),
                min_rms=float(config_dict.get("min_rms", 0.015)),
                min_centroid=float(config_dict.get("min_centroid", 1000.0)),
                min_duration=float(config_dict.get("min_duration", 0.4)),
                top_n=int(config_dict.get("top_n", 1200))
            )
        except Exception as e:
            return f"Invalid configuration: {e}"

        callback = WebViewCallback(self.window) if self.window else None
        self._pipeline = Pipeline(config, callback=callback)

        def run_task():
            if callback:
                callback.on_log("INFO", "=== Pipeline Execution Started ===")
            result = self._pipeline.run()

            if self.window:
                res_dict = {
                    "success": result.success,
                    "cancelled": result.cancelled,
                    "error_message": result.error_message,
                    "final_output_dir": result.final_output_dir
                }
                res_json = json.dumps(res_dict, ensure_ascii=False)
                self.window.evaluate_js(f"if (window.onPipelineComplete) window.onPipelineComplete({res_json});")

        self._pipeline_thread = threading.Thread(target=run_task, daemon=True)
        self._pipeline_thread.start()
        return "started"

    def cancel_pipeline(self) -> str:
        """触发取消信号。"""
        if self._pipeline:
            self._pipeline.cancel()
            return "cancel_signaled"
        return "not_running"

    def copy_to_clipboard(self, text: str) -> bool:
        """将内容复制到系统剪贴板。"""
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except ImportError:
            try:
                import ctypes
                ctypes.windll.user32.OpenClipboard(0)
                ctypes.windll.user32.EmptyClipboard()
                text_len = len(text) + 1
                hCd = ctypes.windll.kernel32.GlobalAlloc(0x2000 | 0x0002, text_len * 2)
                pchData = ctypes.windll.kernel32.GlobalLock(hCd)
                ctypes.cdll.msvcrt.wcscpy(ctypes.c_wchar_p(pchData), text)
                ctypes.windll.kernel32.GlobalUnlock(hCd)
                ctypes.windll.user32.SetClipboardData(13, hCd)
                ctypes.windll.user32.CloseClipboard()
                return True
            except Exception:
                return False

    def export_logs(self, text: str) -> str:
        """打开 Windows 原生保存对话框并写入日志文件。"""
        import ctypes
        from ctypes import wintypes
        
        class OPENFILENAMEW(ctypes.Structure):
            _fields_ = [("lStructSize", wintypes.DWORD),
                        ("hwndOwner", wintypes.HWND),
                        ("hInstance", wintypes.HINSTANCE),
                        ("lpstrFilter", wintypes.LPCWSTR),
                        ("lpstrCustomFilter", wintypes.LPWSTR),
                        ("nMaxCustFilter", wintypes.DWORD),
                        ("nFilterIndex", wintypes.DWORD),
                        ("lpstrFile", wintypes.LPWSTR),
                        ("nMaxFile", wintypes.DWORD),
                        ("lpstrFileTitle", wintypes.LPWSTR),
                        ("nMaxFileTitle", wintypes.DWORD),
                        ("lpstrInitialDir", wintypes.LPCWSTR),
                        ("lpstrTitle", wintypes.LPCWSTR),
                        ("Flags", wintypes.DWORD),
                        ("nFileOffset", wintypes.WORD),
                        ("nFileExtension", wintypes.WORD),
                        ("lpstrDefExt", wintypes.LPCWSTR),
                        ("lCustData", wintypes.LPARAM),
                        ("lpfnHook", wintypes.LPCVOID),
                        ("lpTemplateName", wintypes.LPCWSTR),
                        ("pvReserved", wintypes.LPCVOID),
                        ("dwReserved", wintypes.DWORD),
                        ("FlagsEx", wintypes.DWORD)]

        ofn = OPENFILENAMEW()
        ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
        ofn.lpstrFilter = "Text Files\0*.txt\0All Files\0*.*\0"
        ofn.nMaxFile = 1024
        file_buffer = ctypes.create_unicode_buffer(ofn.nMaxFile)
        ofn.lpstrFile = file_buffer
        ofn.lpstrInitialDir = os.path.expanduser("~\\Documents")
        ofn.lpstrTitle = "导出日志文件"
        ofn.lpstrDefExt = "txt"
        ofn.Flags = 0x2

        if ctypes.windll.comdlg32.GetSaveFileNameW(ctypes.byref(ofn)):
            file_path = file_buffer.value
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                return file_path
            except Exception as e:
                return f"ERROR: {e}"
        return ""
