from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from vocalsieve.domain import PipelineConfig
from vocalsieve.exporter import safe_destination


def test_config_is_immutable_and_validates(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    config = PipelineConfig(str(source), str(tmp_path / "output"))
    config.validate()
    with pytest.raises(FrozenInstanceError):
        config.top_n = 4  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    "change",
    [
        {"top_n": 0},
        {"device": "magic"},
        {"no_speech_threshold": 2.0},
        {"physics_workers": 0},
    ],
)
def test_invalid_config_is_rejected(tmp_path: Path, change: dict):
    source = tmp_path / "source"
    source.mkdir()
    values = {"source_dir": str(source), "output_dir": str(tmp_path / "out"), **change}
    with pytest.raises(ValueError):
        PipelineConfig(**values).validate()


def test_cache_key_changes_with_processing_config(tmp_path: Path):
    base = PipelineConfig(str(tmp_path / "source"), str(tmp_path / "out"))
    changed = PipelineConfig(str(tmp_path / "source"), str(tmp_path / "out"), top_n=5)
    assert base.cache_key != changed.cache_key


def test_safe_destination_rejects_traversal(tmp_path: Path):
    with pytest.raises(ValueError):
        safe_destination(tmp_path, "../escape.wav")
    assert safe_destination(tmp_path, "speaker/a.wav") == (tmp_path / "speaker/a.wav").resolve()


def test_config_accepts_quoted_windows_paths():
    config = PipelineConfig('  "E:\\say-music\\data_music"  ', "'E:\\say-music' ")
    assert config.source_dir == "E:\\say-music\\data_music"
    assert config.output_dir == "E:\\say-music"
