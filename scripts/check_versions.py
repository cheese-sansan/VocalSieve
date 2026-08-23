"""Fail when release-facing version declarations drift apart."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def version_declaration_errors(root: Path) -> list[str]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    python_version = project["project"]["version"]
    init_text = (root / "src/vocalsieve/__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"$', init_text, re.MULTILINE)
    if match is None:
        raise SystemExit("Unable to find vocalsieve.__version__")
    package_version = match.group(1)
    web_version = json.loads((root / "web/package.json").read_text(encoding="utf-8"))["version"]
    expected_release = python_version.replace("rc", "-rc.")
    openapi_version = json.loads((root / "openapi.json").read_text(encoding="utf-8"))["info"][
        "version"
    ]
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")

    errors = []
    if package_version != python_version:
        errors.append(f"package={package_version}, pyproject={python_version}")
    if openapi_version != python_version:
        errors.append(f"openapi={openapi_version}, pyproject={python_version}")
    if web_version != expected_release:
        errors.append(f"web={web_version}, expected={expected_release}")
    if f"[{expected_release}]" not in changelog and (
        "## [Unreleased]" not in changelog or f"Target release: {expected_release}" not in changelog
    ):
        errors.append(f"CHANGELOG has neither [{expected_release}] nor its Unreleased target")
    return errors


def main() -> None:
    errors = version_declaration_errors(ROOT)
    if errors:
        raise SystemExit("Version drift detected: " + "; ".join(errors))
    print("Version declarations agree")


if __name__ == "__main__":
    main()
