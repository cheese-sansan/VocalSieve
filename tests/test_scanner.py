from pathlib import Path

from vocalsieve.scanner import scan_audio_files


def test_scan_is_recursive_and_excludes_output(tmp_path: Path):
    source = tmp_path / "source"
    (source / "nested").mkdir(parents=True)
    (source / "nested" / "a.wav").write_bytes(b"x")
    (source / "notes.txt").write_text("ignore")
    output = source / "generated"
    output.mkdir()
    (output / "old.wav").write_bytes(b"x")
    files = scan_audio_files(str(source), str(output))
    assert [item.relative_path for item in files] == ["nested/a.wav"]


def test_scan_allows_source_inside_output_parent(tmp_path: Path):
    output = tmp_path / "workspace"
    source = output / "data_music"
    source.mkdir(parents=True)
    (source / "a.wav").write_bytes(b"x")
    files = scan_audio_files(str(source), str(output))
    assert [item.relative_path for item in files] == ["a.wav"]
