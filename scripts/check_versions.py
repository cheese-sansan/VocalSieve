"""Fail when release-facing version declarations drift apart."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    python_version = project["project"]["version"]
    init_text = (ROOT / "src/vocalsieve/__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"$', init_text, re.MULTILINE)
    if match is None:
        raise SystemExit("Unable to find vocalsieve.__version__")
    package_version = match.group(1)
    web_version = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))["version"]
    expected_web = python_version.replace("rc", "-rc.")
    openapi_version = json.loads((ROOT / "openapi.json").read_text(encoding="utf-8"))["info"][
        "version"
    ]
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    errors = []
    if package_version != python_version:
        errors.append(f"package={package_version}, pyproject={python_version}")
    if openapi_version != python_version:
        errors.append(f"openapi={openapi_version}, pyproject={python_version}")
    if web_version != expected_web:
        errors.append(f"web={web_version}, expected={expected_web}")
    if f"[{expected_web}]" not in changelog:
        errors.append(f"CHANGELOG has no [{expected_web}] heading")
    if errors:
        raise SystemExit("Version drift detected: " + "; ".join(errors))
    print(f"Version declarations agree on {python_version}")


if __name__ == "__main__":
    main()
