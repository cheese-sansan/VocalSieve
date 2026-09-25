# Code structure and public boundaries

VocalSieve uses a `src/` Python package, a local Web client, and a small set of
release scripts. Keep transport code separate from the job and export logic.

| Path | Responsibility |
| --- | --- |
| `src/vocalsieve/domain.py` | Job, result, configuration, and policy types |
| `src/vocalsieve/database.py` | SQLite state, migrations, and cross-process leases |
| `src/vocalsieve/service.py`, `pipeline.py` | Job orchestration and audio processing |
| `src/vocalsieve/exporter.py` | Reconciled dataset and report output |
| `src/vocalsieve/sdk.py`, `__init__.py` | Supported Python SDK surface |
| `src/vocalsieve/cli.py`, `tui.py` | CLI and terminal presentation |
| `src/vocalsieve/api.py` | Stable `create_app` import path |
| `src/vocalsieve/http_api/` | Internal HTTP app, routes, auth, models, and workers |
| `web/src/api/` | Local API client and generated OpenAPI types |
| `scripts/` | Contract checks, packaging, benchmarking, and release gates |

`vocalsieve.__all__`, `vocalsieve.api.create_app`, and `/api/v1` are compatibility
boundaries. Modules under `http_api/` are internal implementation details. Keep
database schema v3 migrations, existing CSV/JSON fields, and the review endpoint
contract intact when changing adapters or presentation code.

The generated [OpenAPI contract](../../openapi.json) and
[Web types](../../web/src/api/schema.d.ts) are checked against the Python API.
Use the commands in [CONTRIBUTING.md](../../CONTRIBUTING.md) before merging.
