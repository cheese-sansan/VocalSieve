"""Write the canonical OpenAPI contract used by the web client."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vocalsieve.api import create_app


def main() -> None:
    destination = Path(__file__).resolve().parents[1] / "openapi.json"
    state_path = destination.parent / ".tmp" / "openapi.db"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    app = create_app(state_path, session_token="schema-generation-token")
    generated = json.dumps(app.openapi(), indent=2, sort_keys=True)
    if "--check" in sys.argv:
        current = destination.read_text(encoding="utf-8")
        if current != generated:
            raise SystemExit("openapi.json is stale; run scripts/export_openapi.py")
        return
    destination.write_text(generated, encoding="utf-8")


if __name__ == "__main__":
    main()
