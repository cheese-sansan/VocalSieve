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


def test_config_rejects_same_source_and_output(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(ValueError, match="must be different"):
        PipelineConfig(str(source), str(source)).validate()


def test_config_rejects_lexical_alias_of_source_as_output(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    output_alias = source / ".." / source.name
    with pytest.raises(ValueError, match="must be different"):
        PipelineConfig(str(source), str(output_alias)).validate()


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
    config = PipelineConfig('  "C:\\Audio Corpus\\input"  ', "'C:\\Audio Corpus\\output' ")
    assert config.source_dir == "C:\\Audio Corpus\\input"
    assert config.output_dir == "C:\\Audio Corpus\\output"
