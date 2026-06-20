from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

from vocalsieve import cli
from vocalsieve.domain import JobStatus, PipelineConfig
from vocalsieve.events import EventType, PipelineEvent


class FakeService:
    jobs: ClassVar[list] = []
    error: Exception | None = None

    def __init__(self, database=None):
        self.database = database
        self.closed = False

    def close(self):
        self.closed = True

    def list_jobs(self, limit):
        return self.jobs[:limit]

    def create_job(self, config):
        if self.error:
            raise self.error
        self.config = config
        return SimpleNamespace(id="job-1")

    def run_job(self, job_id, sink):
        return SimpleNamespace(status=JobStatus.COMPLETED)

    def resume_job(self, job_id, sink):
        return SimpleNamespace(status=JobStatus.COMPLETED)

    def export_job(self, job_id):
        return {"a.wav": "out/a.wav"}


def test_cli_doctor_and_event_output(monkeypatch, capsys):
    checks = [SimpleNamespace(ok=True, required=True, name="Python", detail="3.12")]
    monkeypatch.setattr(cli, "run_diagnostics", lambda **kwargs: checks)
    assert cli.main(["doctor", "--deep", "--device", "cpu"]) == 0
    assert "OK" in capsys.readouterr().out

    event = PipelineEvent(
        job_id="job-1",
        type=EventType.PROGRESS,
        current=1,
        total=2,
        relative_path="a.wav",
        message="done",
    )
    cli.print_event(event)
    assert "[1/2] a.wav" in capsys.readouterr().out


def test_cli_jobs_run_resume_and_export(monkeypatch, tmp_path: Path, capsys):
    source = tmp_path / "source"
    source.mkdir()
    FakeService.jobs = []
    FakeService.error = None
    monkeypatch.setattr(cli, "VocalSieveService", FakeService)
    assert cli.main(["jobs"]) == 0
    assert "No jobs" in capsys.readouterr().out

    config = PipelineConfig(str(source), str(tmp_path / "out"))
    FakeService.jobs = [
        SimpleNamespace(
            id="job-1",
            status=JobStatus.COMPLETED,
            created_at="2026-01-01",
            config=config,
        )
    ]
    assert cli.main(["jobs"]) == 0
    assert "job-1" in capsys.readouterr().out
    assert cli.main(["run", str(source), str(tmp_path / "out"), "--top-n", "5"]) == 0
    assert "Created job" in capsys.readouterr().out
    assert cli.main(["resume", "job-1"]) == 0
    assert cli.main(["export", "job-1"]) == 0
    assert "Exported 1" in capsys.readouterr().out


def test_cli_error_and_tui_paths(monkeypatch, tmp_path: Path, capsys):
    FakeService.jobs = []
    FakeService.error = ValueError("bad config")
    monkeypatch.setattr(cli, "VocalSieveService", FakeService)
    source = tmp_path / "source"
    source.mkdir()
    assert cli.main(["run", str(source), str(tmp_path / "out")]) == 1
    assert "bad config" in capsys.readouterr().err

    called = []
    monkeypatch.setattr("vocalsieve.tui.run_tui", lambda database: called.append(database))
    assert cli.main([]) == 0
    assert called == [None]


def test_cli_serve_is_loopback_only(monkeypatch, capsys):
    app = SimpleNamespace(state=SimpleNamespace(session_token="secret"))
    monkeypatch.setattr("vocalsieve.api.create_app", lambda database, session_token=None: app)
    calls = []
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: calls.append(kwargs))
    assert cli.main(["serve", "--port", "9000"]) == 0
    assert calls == [{"host": "127.0.0.1", "port": 9000, "log_level": "info"}]
    assert "secret" in capsys.readouterr().out
