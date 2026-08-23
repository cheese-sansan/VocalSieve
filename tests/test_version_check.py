import json
from pathlib import Path

from scripts import check_versions


def _write_version_files(root: Path, changelog: str) -> None:
    (root / "src" / "vocalsieve").mkdir(parents=True)
    (root / "web").mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "vocalsieve"\nversion = "0.9.0rc2"\n',
        encoding="utf-8",
    )
    (root / "src" / "vocalsieve" / "__init__.py").write_text(
        '__version__ = "0.9.0rc2"\n', encoding="utf-8"
    )
    (root / "web" / "package.json").write_text(
        json.dumps({"version": "0.9.0-rc.2"}), encoding="utf-8"
    )
    (root / "openapi.json").write_text(
        json.dumps({"info": {"version": "0.9.0rc2"}}), encoding="utf-8"
    )
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")


def test_version_declaration_accepts_unreleased_target(tmp_path: Path) -> None:
    _write_version_files(
        tmp_path,
        "# Changelog\n\n## [Unreleased]\n\nTarget release: 0.9.0-rc.2\n",
    )

    assert check_versions.version_declaration_errors(tmp_path) == []


def test_version_declaration_accepts_released_heading(tmp_path: Path) -> None:
    _write_version_files(tmp_path, "# Changelog\n\n## [0.9.0-rc.2] - 2026-08-09\n")

    assert check_versions.version_declaration_errors(tmp_path) == []


def test_version_declaration_rejects_unreleased_without_target(tmp_path: Path) -> None:
    _write_version_files(tmp_path, "# Changelog\n\n## [Unreleased]\n")

    errors = check_versions.version_declaration_errors(tmp_path)

    assert errors == ["CHANGELOG has neither [0.9.0-rc.2] nor its Unreleased target"]
