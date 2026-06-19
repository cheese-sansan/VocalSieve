"""Write the canonical OpenAPI contract used by the web client."""

from __future__ import annotations

import json
from pathlib import Path

from vocalsieve.api import create_app


def main() -> None:
    destination = Path(__file__).resolve().parents[1] / "openapi.json"
    state_path = destination.parent / ".tmp" / "openapi.db"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    app = create_app(state_path, session_token="schema-generation-token")
    destination.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
