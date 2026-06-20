import asyncio
from pathlib import Path

from textual.widgets import Button, TabbedContent

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
            assert app.sub_title == "Audio corpus workbench"
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
            assert app.sub_title == "音频语料工作台"
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
