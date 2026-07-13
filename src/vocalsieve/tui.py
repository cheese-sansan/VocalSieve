"""Textual workbench with an English/Simplified Chinese interface."""

from __future__ import annotations

from typing import Any, cast

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from .doctor import run_diagnostics
from .domain import PipelineConfig, ReviewDecision, RuntimePolicy
from .events import EventType, PipelineEvent
from .service import VocalSieveService
from .settings import load_language, save_language

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "subtitle": "Audio corpus workbench",
        "tab_jobs": "Jobs",
        "tab_new": "New job",
        "tab_run": "Run",
        "tab_results": "Results",
        "tab_doctor": "Doctor",
        "tab_settings": "Settings",
        "refresh": "Refresh",
        "resume": "Resume",
        "view_results": "View results",
        "source": "Source directory",
        "output": "Output directory",
        "model": "Model",
        "device": "Device",
        "compute": "Compute type",
        "language": "Language",
        "top_n": "Maximum selected",
        "workers": "Physics workers",
        "create": "Create and run",
        "cancel": "Cancel",
        "no_active": "No active job",
        "waiting": "Waiting",
        "stats": "Accepted: {accepted}  Rejected: {rejected}  Errors: {errors}",
        "status_filter": "Status",
        "language_filter": "Language",
        "reason_filter": "Rejection reason",
        "apply": "Apply",
        "export": "Export again",
        "review_note": "Review note (optional)",
        "review_include": "Include",
        "review_exclude": "Exclude",
        "review_automatic": "Automatic",
        "review_updated": "Review updated",
        "select_result": "Select a result to inspect it.",
        "diagnostics": "Run diagnostics",
        "settings_text": "Database and model caches use the operating system's application data directories.\nThe source corpus is always treated as read-only.\nUp to {active} jobs may run, including {cuda} CUDA job(s).",
        "interface_language": "Interface language",
        "job": "Job {job_id}",
        "another_active": "Another job is already active",
        "exported": "Exported {count} files",
        "job_finished": "Job finished",
        "accepted": "Accepted",
        "rejected": "Rejected",
        "errors": "Errors",
        "detail_status": "Status",
        "detail_language": "Language",
        "detail_duration": "Duration",
        "detail_centroid": "Centroid",
        "detail_reason": "Reason",
        "detail_transcript": "Transcript",
        "col_id": "ID",
        "col_status": "Status",
        "col_stage": "Stage",
        "col_created": "Created",
        "col_source": "Source",
        "col_path": "Path",
        "col_language": "Language",
        "col_reason": "Reason",
        "col_score": "Score",
        "col_review": "Review",
        "col_selected": "Final",
        "stage_scan": "Scanning source files",
        "stage_physics": "Analyzing acoustic features",
        "stage_transcription": "Transcribing eligible files",
        "stage_ranking": "Ranking eligible files",
        "stage_export": "Exporting selected files",
        "job_started": "Job started",
        "job_completed": "Job completed",
        "job_cancelled": "Job cancelled",
        "file_accepted": "Accepted {path}",
        "file_rejected": "Rejected {path}",
        "progress": "Progress {current}/{total}",
    },
    "zh": {
        "subtitle": "音频语料工作台",
        "tab_jobs": "任务",
        "tab_new": "新建任务",
        "tab_run": "运行",
        "tab_results": "结果",
        "tab_doctor": "环境诊断",
        "tab_settings": "设置",
        "refresh": "刷新",
        "resume": "恢复运行",
        "view_results": "查看结果",
        "source": "源语料目录",
        "output": "输出目录",
        "model": "模型",
        "device": "运行设备",
        "compute": "计算精度",
        "language": "语料语言",
        "top_n": "最大保留数量",
        "workers": "声学分析线程",
        "create": "创建并运行",
        "cancel": "取消任务",
        "no_active": "当前没有运行中的任务",
        "waiting": "等待中",
        "stats": "通过：{accepted}  淘汰：{rejected}  错误：{errors}",
        "status_filter": "状态",
        "language_filter": "语言",
        "reason_filter": "淘汰原因",
        "apply": "应用筛选",
        "export": "重新导出",
        "review_note": "复核备注（可选）",
        "review_include": "人工选入",
        "review_exclude": "人工排除",
        "review_automatic": "恢复自动",
        "review_updated": "复核结果已更新",
        "select_result": "选择一条结果以查看详情。",
        "diagnostics": "重新诊断",
        "settings_text": "数据库与模型缓存使用操作系统的应用数据目录。\n源语料始终按只读方式处理。\n最多同时运行 {active} 个任务，其中 CUDA 任务最多 {cuda} 个。",
        "interface_language": "界面语言",
        "job": "任务 {job_id}",
        "another_active": "已有其他任务正在运行",
        "exported": "已导出 {count} 个文件",
        "job_finished": "任务已结束",
        "accepted": "通过",
        "rejected": "淘汰",
        "errors": "错误",
        "detail_status": "状态",
        "detail_language": "语言",
        "detail_duration": "时长",
        "detail_centroid": "频谱质心",
        "detail_reason": "原因",
        "detail_transcript": "转录文本",
        "col_id": "编号",
        "col_status": "状态",
        "col_stage": "阶段",
        "col_created": "创建时间",
        "col_source": "源目录",
        "col_path": "文件路径",
        "col_language": "语言",
        "col_reason": "原因",
        "col_score": "评分",
        "col_review": "人工复核",
        "col_selected": "最终选中",
        "stage_scan": "正在扫描源文件",
        "stage_physics": "正在分析声学特征",
        "stage_transcription": "正在转录候选文件",
        "stage_ranking": "正在排序候选文件",
        "stage_export": "正在导出入选文件",
        "job_started": "任务已开始",
        "job_completed": "任务已完成",
        "job_cancelled": "任务已取消",
        "file_accepted": "已通过 {path}",
        "file_rejected": "已淘汰 {path}",
        "progress": "进度 {current}/{total}",
    },
}

STATUS_ZH = {
    "pending": "等待中",
    "running": "运行中",
    "cancelling": "正在取消",
    "cancelled": "已取消",
    "completed": "已完成",
    "failed": "失败",
    "physics_passed": "声学通过",
    "physics_rejected": "声学淘汰",
    "transcription_passed": "转录通过",
    "transcription_rejected": "转录淘汰",
    "selected": "已入选",
    "error": "错误",
}
STAGE_ZH = {
    "scan": "扫描",
    "physics": "声学分析",
    "transcription": "语音转录",
    "ranking": "排序",
    "export": "导出",
}
REASON_ZH = {
    "duration_too_short": "时长过短",
    "energy_too_low": "能量过低",
    "spectral_centroid_too_low": "频谱质心过低",
    "no_speech": "未检测到有效语音",
    "text_too_short": "文本过短",
    "text_too_long": "文本过长",
    "repeated_characters": "连续重复字符",
    "hallucination_keyword": "疑似幻觉文本",
    "physics_error": "声学分析错误",
    "transcription_error": "转录错误",
}


class LanguagePicker(ModalScreen[str]):
    """Blocking language choice shown before the workbench is initialized."""

    CSS = """
    LanguagePicker {
        align: center middle;
        background: #000000 75%;
    }
    #language-dialog {
        width: 48;
        height: 12;
        padding: 1 2;
        background: #171717;
        border: tall #7a7a7a;
    }
    #language-title {
        width: 100%;
        height: 3;
        content-align: center middle;
        color: #ffffff;
        text-style: bold;
    }
    #language-hint {
        width: 100%;
        height: 2;
        content-align: center middle;
        color: #b3b3b3;
    }
    #language-actions { align: center middle; height: 4; }
    #language-actions Button { width: 16; margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="language-dialog"):
            yield Label("VocalSieve", id="language-title")
            yield Label("Choose language / 选择语言", id="language-hint")
            with Horizontal(id="language-actions"):
                yield Button("EN", id="lang-en", variant="primary")
                yield Button("CH (简体)", id="lang-zh")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "lang-en":
            self.dismiss("en")
        elif event.button.id == "lang-zh":
            self.dismiss("zh")


class PipelineMessage(Message):
    def __init__(self, event: PipelineEvent):
        super().__init__()
        self.event = event


class JobFinished(Message):
    def __init__(self, job_id: str, error: str | None = None):
        super().__init__()
        self.job_id = job_id
        self.error = error


class VocalSieveApp(App):
    TITLE = "VocalSieve"
    SUB_TITLE = "Audio corpus workbench"
    CSS = """
    Screen { background: #0c0c0c; color: #f2f2f2; }
    Header { background: #171717; color: #ffffff; }
    Footer { background: #171717; color: #b3b3b3; }
    TabbedContent { background: #0c0c0c; }
    Tabs { background: #171717; color: #b3b3b3; }
    Tab { background: #171717; color: #b3b3b3; padding: 0 2; }
    Tab:hover { background: #2d2d2d; color: #ffffff; }
    Tab.-active { background: #3a3a3a; color: #ffffff; text-style: bold; }
    TabPane { padding: 1 2; background: #0c0c0c; }
    .toolbar { height: 3; margin-bottom: 1; }
    .toolbar Button { margin-right: 1; }
    .form-row { height: 3; }
    .form-row Label { width: 20; padding-top: 1; color: #d6d6d6; }
    .form-row Input, .form-row Select { width: 1fr; }
    Input, Select {
        background: #171717;
        color: #ffffff;
        border: tall #5f5f5f;
    }
    Input:focus, Select:focus { border: tall #ffffff; }
    Button {
        background: #3a3a3a;
        color: #ffffff;
        border: none;
        min-width: 12;
    }
    Button:hover, Button:focus { background: #5a5a5a; text-style: bold; }
    Button.-success { background: #16825d; }
    Button.-error { background: #c50f1f; }
    Button.-primary { background: #4a4a4a; }
    DataTable {
        height: 1fr;
        background: #171717;
        color: #f2f2f2;
        border: tall #5f5f5f;
    }
    DataTable > .datatable--header { background: #2d2d2d; color: #ffffff; text-style: bold; }
    DataTable > .datatable--cursor { background: #4a4a4a; color: #ffffff; }
    #run-log {
        height: 1fr;
        background: #000000;
        color: #f2f2f2;
        border: tall #5f5f5f;
    }
    #run-progress { margin: 1 0; color: #16825d; }
    #result-detail {
        height: 9;
        background: #171717;
        border: tall #5f5f5f;
        padding: 1;
    }
    #doctor-output { padding: 1; color: #d6d6d6; }
    #settings-text { padding: 1; color: #d6d6d6; }
    #settings-language-title { height: 2; color: #ffffff; text-style: bold; }
    #settings-language-actions { height: 4; }
    #settings-language-actions Button { margin-right: 1; }
    .muted { color: #9b9b9b; }
    """

    def __init__(
        self,
        database_path: str | None = None,
        settings_path: str | None = None,
        runtime_policy: RuntimePolicy | None = None,
    ):
        super().__init__()
        self.service = VocalSieveService(database_path, runtime_policy)
        self.settings_path = settings_path
        self.language = load_language(settings_path) or "en"
        self._has_saved_language = load_language(settings_path) is not None
        self.selected_job_id: str | None = None
        self.active_job_ids: set[str] = set()
        self.selected_result_path: str | None = None
        self._workbench_ready = False

    def tr(self, key: str, **values: Any) -> str:
        return TEXT[self.language][key].format(**values)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="jobs"):
            with TabPane("Jobs", id="jobs"):
                with Horizontal(classes="toolbar"):
                    yield Button("Refresh", id="refresh-jobs")
                    yield Button("Resume", id="resume-job", variant="primary")
                    yield Button("View results", id="view-results")
                yield DataTable(id="job-table", cursor_type="row")
            with TabPane("New job", id="new-job"):
                yield self._form_row(
                    "Source directory", Input(id="source", placeholder="C:\\audio\\raw"), "source"
                )
                yield self._form_row(
                    "Output directory",
                    Input(id="output", placeholder="C:\\audio\\selected"),
                    "output",
                )
                yield self._form_row("Model", Input("small", id="model"), "model")
                yield self._form_row(
                    "Device",
                    Select(
                        [("Auto", "auto"), ("CPU", "cpu"), ("CUDA", "cuda")],
                        value="auto",
                        id="device",
                    ),
                    "device",
                )
                yield self._form_row("Compute type", Input("auto", id="compute-type"), "compute")
                yield self._form_row("Language", Input("auto", id="language"), "language")
                yield self._form_row("Top N", Input("1200", id="top-n", type="integer"), "top-n")
                yield self._form_row(
                    "Physics workers", Input("4", id="workers", type="integer"), "workers"
                )
                yield Static("", id="form-error")
                yield Button("Create and run", id="create-job", variant="success")
            with TabPane("Run", id="run"):
                with Horizontal(classes="toolbar"):
                    yield Button("Cancel", id="cancel-job", variant="error")
                yield Label("No active job", id="run-title")
                yield Label("Waiting", id="run-stage", classes="muted")
                yield ProgressBar(total=100, show_eta=False, id="run-progress")
                yield Label("Accepted: 0  Rejected: 0  Errors: 0", id="run-stats")
                yield RichLog(id="run-log", wrap=True, markup=True)
            with TabPane("Results", id="results"):
                with Horizontal(classes="toolbar"):
                    yield Input(placeholder="Status", id="filter-status")
                    yield Input(placeholder="Language", id="filter-language")
                    yield Input(placeholder="Rejection reason", id="filter-reason")
                    yield Button("Apply", id="apply-filter")
                    yield Button("Export again", id="export-job")
                with Horizontal(classes="toolbar"):
                    yield Input(placeholder="Review note (optional)", id="review-note")
                    yield Button("Include", id="review-include", variant="success")
                    yield Button("Exclude", id="review-exclude", variant="error")
                    yield Button("Automatic", id="review-automatic")
                yield DataTable(id="result-table", cursor_type="row")
                yield Static("Select a result to inspect it.", id="result-detail")
            with TabPane("Doctor", id="doctor"):
                yield Button("Run diagnostics", id="run-doctor")
                yield Static("", id="doctor-output")
            with TabPane("Settings", id="settings"):
                yield Label("Interface language", id="settings-language-title")
                with Horizontal(id="settings-language-actions"):
                    yield Button("EN", id="settings-en")
                    yield Button("CH (简体)", id="settings-zh")
                yield Static("", id="settings-text")
        yield Footer()

    @staticmethod
    def _form_row(label: str, control: Any, key: str) -> Horizontal:
        return Horizontal(Label(label, id=f"label-{key}"), control, classes="form-row")

    def on_mount(self) -> None:
        if self._has_saved_language:
            self._activate_language(self.language, persist=False)
        else:
            self.push_screen(LanguagePicker(), self._language_selected)

    def _language_selected(self, language: str | None) -> None:
        self._activate_language(language or "en", persist=True)

    def _activate_language(self, language: str, *, persist: bool) -> None:
        rebuild_tables = self._workbench_ready
        self.language = language
        if persist:
            save_language(language, self.settings_path)
            self._has_saved_language = True
        self.sub_title = self.tr("subtitle")
        self._apply_static_text()
        if rebuild_tables:
            self.query_one("#job-table", DataTable).clear(columns=True)
            self.query_one("#result-table", DataTable).clear(columns=True)
            self._workbench_ready = False
        self._initialize_tables()
        self.refresh_jobs()
        self.refresh_results()
        self.show_diagnostics()
        self._workbench_ready = True

    def _apply_static_text(self) -> None:
        tab_keys = {
            "jobs": "tab_jobs",
            "new-job": "tab_new",
            "run": "tab_run",
            "results": "tab_results",
            "doctor": "tab_doctor",
            "settings": "tab_settings",
        }
        for pane_id, key in tab_keys.items():
            pane = cast(Any, self.query_one(f"#{pane_id}", TabPane))
            pane.title = self.tr(key)
        labels = {
            "label-source": "source",
            "label-output": "output",
            "label-model": "model",
            "label-device": "device",
            "label-compute": "compute",
            "label-language": "language",
            "label-top-n": "top_n",
            "label-workers": "workers",
        }
        for widget_id, key in labels.items():
            self.query_one(f"#{widget_id}", Label).update(self.tr(key))
        buttons = {
            "refresh-jobs": "refresh",
            "resume-job": "resume",
            "view-results": "view_results",
            "create-job": "create",
            "cancel-job": "cancel",
            "apply-filter": "apply",
            "export-job": "export",
            "review-include": "review_include",
            "review-exclude": "review_exclude",
            "review-automatic": "review_automatic",
            "run-doctor": "diagnostics",
        }
        for widget_id, key in buttons.items():
            self.query_one(f"#{widget_id}", Button).label = self.tr(key)
        placeholders = {
            "filter-status": "status_filter",
            "filter-language": "language_filter",
            "filter-reason": "reason_filter",
            "review-note": "review_note",
        }
        for widget_id, key in placeholders.items():
            self.query_one(f"#{widget_id}", Input).placeholder = self.tr(key)
        self.query_one("#run-title", Label).update(self.tr("no_active"))
        self.query_one("#run-stage", Label).update(self.tr("waiting"))
        self.query_one("#run-stats", Label).update(
            self.tr("stats", accepted=0, rejected=0, errors=0)
        )
        self.query_one("#result-detail", Static).update(self.tr("select_result"))
        self.query_one("#settings-text", Static).update(
            self.tr(
                "settings_text",
                active=self.service.runtime_policy.max_active_jobs,
                cuda=self.service.runtime_policy.max_cuda_jobs,
            )
        )
        self.query_one("#settings-language-title", Label).update(self.tr("interface_language"))
        self.query_one("#settings-en", Button).disabled = self.language == "en"
        self.query_one("#settings-zh", Button).disabled = self.language == "zh"

    def _initialize_tables(self) -> None:
        if self._workbench_ready:
            return
        self.query_one("#job-table", DataTable).add_columns(
            self.tr("col_id"),
            self.tr("col_status"),
            self.tr("col_stage"),
            self.tr("col_created"),
            self.tr("col_source"),
        )
        self.query_one("#result-table", DataTable).add_columns(
            self.tr("col_path"),
            self.tr("col_status"),
            self.tr("col_language"),
            self.tr("col_reason"),
            self.tr("col_score"),
            self.tr("col_review"),
            self.tr("col_selected"),
        )

    def local_status(self, value: str) -> str:
        return STATUS_ZH.get(value, value) if self.language == "zh" else value

    def local_stage(self, value: str | None) -> str:
        if not value:
            return "-"
        return STAGE_ZH.get(value, value) if self.language == "zh" else value

    def local_reason(self, value: str | None) -> str:
        if not value:
            return "-"
        return REASON_ZH.get(value, value) if self.language == "zh" else value

    def refresh_jobs(self) -> None:
        table = self.query_one("#job-table", DataTable)
        table.clear()
        for job in self.service.list_jobs():
            table.add_row(
                job.id[:10],
                self.local_status(job.status.value),
                self.local_stage(job.current_stage),
                job.created_at[:19],
                job.config.source_dir,
                key=job.id,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "job-table":
            self.selected_job_id = str(event.row_key.value)
            self.show_job_run(self.selected_job_id)
        elif event.data_table.id == "result-table":
            self.selected_result_path = str(event.row_key.value)
            self.show_result_detail(self.selected_result_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "refresh-jobs":
            self.refresh_jobs()
        elif button_id == "create-job":
            self.create_job_from_form()
        elif button_id == "resume-job" and self.selected_job_id:
            self.start_job(self.selected_job_id)
        elif button_id == "view-results" and self.selected_job_id:
            self.query_one(TabbedContent).active = "results"
            self.refresh_results()
        elif button_id == "cancel-job" and self.selected_job_id:
            try:
                self.service.cancel_job(self.selected_job_id)
            except RuntimeError as exc:
                self.notify(str(exc), severity="warning")
        elif button_id == "apply-filter":
            self.refresh_results()
        elif button_id == "export-job" and self.selected_job_id:
            exported = self.service.export_job(self.selected_job_id)
            self.notify(self.tr("exported", count=len(exported)))
        elif button_id in {"review-include", "review-exclude", "review-automatic"}:
            self.apply_review(button_id)
        elif button_id == "run-doctor":
            self.show_diagnostics()
        elif button_id == "settings-en":
            self._activate_language("en", persist=True)
        elif button_id == "settings-zh":
            self._activate_language("zh", persist=True)

    def create_job_from_form(self) -> None:
        try:
            config = PipelineConfig(
                source_dir=self.query_one("#source", Input).value,
                output_dir=self.query_one("#output", Input).value,
                model_size=self.query_one("#model", Input).value,
                device=str(self.query_one("#device", Select).value),
                compute_type=self.query_one("#compute-type", Input).value,
                language=self.query_one("#language", Input).value,
                top_n=int(self.query_one("#top-n", Input).value),
                physics_workers=int(self.query_one("#workers", Input).value),
            )
            job = self.service.create_job(config)
        except (ValueError, OSError) as exc:
            self.query_one("#form-error", Static).update(f"[red]{exc}[/red]")
            return
        self.query_one("#form-error", Static).update("")
        self.selected_job_id = job.id
        self.refresh_jobs()
        self.start_job(job.id)

    def start_job(self, job_id: str) -> None:
        try:
            self.service.reserve_job(job_id)
        except RuntimeError as exc:
            self.notify(str(exc), severity="warning")
            return
        self.active_job_ids.add(job_id)
        self.query_one(TabbedContent).active = "run"
        self.query_one("#run-title", Label).update(self.tr("job", job_id=job_id))
        self.query_one("#run-log", RichLog).clear()
        self.query_one("#run-progress", ProgressBar).update(total=100, progress=0)
        self.run_job_worker(job_id)

    def show_job_run(self, job_id: str) -> None:
        job = self.service.get_job(job_id)
        self.query_one("#run-title", Label).update(self.tr("job", job_id=job_id))
        self.query_one("#run-stage", Label).update(self.local_stage(job.current_stage))
        log = self.query_one("#run-log", RichLog)
        log.clear()
        events = self.service.database.get_events(job_id)
        for event in events[-100:]:
            log.write(f"[dim]{event['timestamp'][11:19]}[/dim] {event['type']}: {event['message']}")
        progress = next(
            (
                event["data"]
                for event in reversed(events)
                if event["data"].get("current") is not None and event["data"].get("total")
            ),
            None,
        )
        if progress:
            self.query_one("#run-progress", ProgressBar).update(
                total=progress["total"], progress=progress["current"]
            )

    @work(thread=True, exclusive=False)
    def run_job_worker(self, job_id: str) -> None:
        error = None
        try:

            def sink(event: PipelineEvent) -> None:
                self.call_from_thread(self.post_message, PipelineMessage(event))

            self.service.run_reserved_job(job_id, sink)
        except Exception as exc:
            error = str(exc)
        self.call_from_thread(self.post_message, JobFinished(job_id, error))

    def _event_text(self, event: PipelineEvent) -> str:
        if event.type == EventType.STAGE_STARTED and event.stage:
            return self.tr(f"stage_{event.stage}")
        if event.type == EventType.JOB_STARTED:
            return self.tr("job_started")
        if event.type == EventType.JOB_COMPLETED:
            return self.tr("job_completed")
        if event.type == EventType.CANCELLED:
            return self.tr("job_cancelled")
        if event.type == EventType.FILE_COMPLETED:
            key = "file_accepted" if event.accepted else "file_rejected"
            return self.tr(key, path=event.relative_path or "")
        if (
            event.type == EventType.PROGRESS
            and event.current is not None
            and event.total is not None
        ):
            return self.tr("progress", current=event.current, total=event.total)
        return event.message

    def on_pipeline_message(self, message: PipelineMessage) -> None:
        event = message.event
        if event.job_id != self.selected_job_id:
            return
        self.query_one("#run-stage", Label).update(
            self.local_stage(event.stage) if event.stage else event.type.value
        )
        self.query_one("#run-log", RichLog).write(
            f"[dim]{event.timestamp[11:19]}[/dim] {self._event_text(event)}"
        )
        if event.current is not None and event.total:
            self.query_one("#run-progress", ProgressBar).update(
                total=event.total, progress=event.current
            )
        if event.type == EventType.FILE_COMPLETED:
            rows = self.service.query_results(event.job_id)
            accepted = sum(
                row.status.value in {"physics_passed", "transcription_passed", "selected"}
                for row in rows
            )
            rejected = sum("rejected" in row.status.value for row in rows)
            errors = sum(row.status.value == "error" for row in rows)
            self.query_one("#run-stats", Label).update(
                self.tr("stats", accepted=accepted, rejected=rejected, errors=errors)
            )

    def on_job_finished(self, message: JobFinished) -> None:
        self.active_job_ids.discard(message.job_id)
        if self.selected_job_id is None:
            self.selected_job_id = message.job_id
        self.refresh_jobs()
        self.refresh_results()
        self.notify(
            message.error if message.error else self.tr("job_finished"),
            severity="error" if message.error else "information",
        )

    def refresh_results(self) -> None:
        if not self.selected_job_id:
            return
        status = self.query_one("#filter-status", Input).value.strip() or None
        language = self.query_one("#filter-language", Input).value.strip() or None
        reason = self.query_one("#filter-reason", Input).value.strip() or None
        rows = self.service.query_results(
            self.selected_job_id, status=status, language=language, reason=reason
        )
        table = self.query_one("#result-table", DataTable)
        table.clear()
        for row in rows:
            table.add_row(
                row.relative_path,
                self.local_status(row.status.value),
                row.language or "-",
                self.local_reason(row.reject_code),
                str(row.score if row.score is not None else "-"),
                row.review_decision.value if row.review_decision else "automatic",
                "yes" if row.effective_selected else "no",
                key=row.relative_path,
            )

    def apply_review(self, button_id: str) -> None:
        if not self.selected_job_id or not self.selected_result_path:
            self.notify(self.tr("select_result"), severity="warning")
            return
        decisions = {
            "review-include": ReviewDecision.INCLUDE,
            "review-exclude": ReviewDecision.EXCLUDE,
            "review-automatic": None,
        }
        try:
            self.service.review_result(
                self.selected_job_id,
                self.selected_result_path,
                decisions[button_id],
                self.query_one("#review-note", Input).value,
            )
        except (KeyError, RuntimeError, ValueError) as exc:
            self.notify(str(exc), severity="warning")
            return
        self.refresh_results()
        self.show_result_detail(self.selected_result_path)
        self.notify(self.tr("review_updated"))

    def show_result_detail(self, relative_path: str) -> None:
        if not self.selected_job_id:
            return
        row = next(
            (
                item
                for item in self.service.query_results(self.selected_job_id)
                if item.relative_path == relative_path
            ),
            None,
        )
        if row:
            self.query_one("#result-detail", Static).update(
                f"[b]{row.relative_path}[/b]\n"
                f"{self.tr('detail_status')}: {self.local_status(row.status.value)}  "
                f"{self.tr('detail_language')}: {row.language or '-'}\n"
                f"{self.tr('detail_duration')}: {row.duration or '-'}  RMS: {row.rms or '-'}  "
                f"{self.tr('detail_centroid')}: {row.spectral_centroid or '-'}\n"
                f"{self.tr('detail_reason')}: {self.local_reason(row.reject_code)} "
                f"{row.reject_detail or ''}\n"
                f"Review: {row.review_decision.value if row.review_decision else 'automatic'}  "
                f"Final: {'yes' if row.effective_selected else 'no'}\n"
                f"{self.tr('detail_transcript')}: {row.transcription or '-'}"
            )

    def show_diagnostics(self) -> None:
        lines = []
        for check in run_diagnostics():
            state = (
                "[green]OK[/green]"
                if check.ok
                else ("[grey70]WARN[/grey70]" if not check.required else "[red]FAIL[/red]")
            )
            lines.append(f"{state:15} {check.name:18} {check.detail}")
        self.query_one("#doctor-output", Static).update("\n".join(lines))

    def on_unmount(self) -> None:
        self.service.close()


def run_tui(
    database_path: str | None = None,
    runtime_policy: RuntimePolicy | None = None,
) -> None:
    VocalSieveApp(database_path, runtime_policy=runtime_policy).run()
