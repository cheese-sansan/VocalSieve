import asyncio
from pathlib import Path

from textual.widgets import Button, TabbedContent

from vocalsieve.domain import FileStatus, JobStatus, PipelineConfig, ScannedFile
from vocalsieve.tui import LanguagePicker, VocalSieveApp


def test_tui_mounts_and_shows_english_navigation(tmp_path: Path):
    async def run() -> None:
        app = VocalSieveApp(str(tmp_path / "state.db"), str(tmp_path / "settings.json"))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.screen.query_one("#language-dialog") is not None
            await pilot.click("#lang-en")
            await pilot.pause()
            assert app.title == "VocalSieve"
            assert app.sub_title == "Local speech dataset curation"
            assert app.query_one("#job-table") is not None
            assert "Python" in str(app.query_one("#doctor-output").render())

    asyncio.run(run())


def test_tui_supports_simplified_chinese(tmp_path: Path):
    async def run() -> None:
        app = VocalSieveApp(str(tmp_path / "state-zh.db"), str(tmp_path / "settings-zh.json"))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#lang-zh")
            await pilot.pause()
            assert app.language == "zh"
            assert app.sub_title == "本地语音数据集整理"
            assert str(app.query_one("#create-job", Button).label) == "创建并运行"
            assert "源语料" in str(app.query_one("#label-source").render())

    asyncio.run(run())


def test_saved_language_skips_picker_and_can_change_in_settings(tmp_path: Path):
    settings = tmp_path / "settings.json"

    async def choose_once() -> None:
        app = VocalSieveApp(str(tmp_path / "first.db"), str(settings))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#lang-en")
            await pilot.pause()

    async def reopen_and_change() -> None:
        app = VocalSieveApp(str(tmp_path / "second.db"), str(settings))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert not isinstance(app.screen, LanguagePicker)
            assert app.language == "en"
            app.query_one(TabbedContent).active = "settings"
            await pilot.pause()
            await pilot.click("#settings-zh")
            await pilot.pause()
            assert app.language == "zh"
            assert str(app.query_one("#create-job", Button).label) == "创建并运行"

    asyncio.run(choose_once())
    asyncio.run(reopen_and_change())


def test_tui_applies_manual_review(tmp_path: Path):
    async def run() -> None:
        source = tmp_path / "source"
        source.mkdir()
        audio = source / "a.wav"
        audio.write_bytes(b"audio")
        app = VocalSieveApp(str(tmp_path / "review.db"), str(tmp_path / "settings.json"))
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.pause()
            await pilot.click("#lang-en")
            await pilot.pause()
            job = app.service.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
            stat = audio.stat()
            app.service.database.upsert_scanned_file(
                job.id,
                ScannedFile("a.wav", audio, stat.st_size, stat.st_mtime_ns),
                job.config.cache_key,
            )
            app.service.database.update_file(job.id, "a.wav", status=FileStatus.SELECTED)
            app.service.database.set_job_state(job.id, JobStatus.COMPLETED)
            app.selected_job_id = job.id
            app.selected_result_path = "a.wav"
            app.apply_review("review-exclude")
            await pilot.pause()
            assert not app.service.query_results(job.id)[0].effective_selected
            assert "exclude" in str(app.query_one("#result-detail").render())

    asyncio.run(run())
