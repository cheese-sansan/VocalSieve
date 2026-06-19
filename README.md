# VocalSieve

VocalSieve is a local-first audio corpus screening workbench. It scans a source
directory without modifying it, analyzes audio, transcribes eligible files with
`faster-whisper`, applies configurable rules, ranks the survivors, and exports
the final selection while preserving relative paths.

Jobs, metrics, transcripts, rejection reasons, events, and resume state are
stored in SQLite. The first TUI launch asks for English or Simplified Chinese;
the choice is remembered and can be changed later in Settings.

## Supported platforms

- Windows 10/11: native CLI and Textual TUI; CPU is ready, CUDA requires the
  CUDA 12 and cuDNN 9 runtime described in [the CUDA guide](docs/CUDA.md).
- Linux: CPU and NVIDIA GPU containers.
- macOS: experimental and not part of the release gate.

Python 3.11 or 3.12 is required. FFmpeg must be available on `PATH` for native
use; see [FFMPEG.md](docs/FFMPEG.md). Model weights are downloaded on first use
and are never committed to the repository or baked into images.

## Quick start with uv

```powershell
cd path\to\vocalsieve
uv sync --extra tui
uv run vocalsieve doctor
uv run vocalsieve
```

For development, API, and all tests:

```powershell
uv sync --all-extras
uv run pytest --cov=vocalsieve
```

## Quick start with pip

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[tui]"
.venv\Scripts\vocalsieve doctor
.venv\Scripts\vocalsieve
```

Install `.[api]` for the local HTTP API or `.[tui,api,dev]` for development.

## CLI

```powershell
vocalsieve run "E:\data\raw" "E:\data\screened" --model small --device auto --top-n 1200
vocalsieve doctor
vocalsieve doctor --deep --device cpu --model tiny
vocalsieve jobs
vocalsieve resume JOB_ID
vocalsieve export JOB_ID
```

Quoted Windows paths are accepted. `top-n` is a maximum after all acoustic and
transcription rules run, not a promise that the output will contain that many
files. Results are written to `OUTPUT/final_selected/` with complete CSV and
JSON reports beside it.

## Python SDK

```python
from vocalsieve import PipelineConfig, VocalSieveClient

config = PipelineConfig(
    source_dir=r"E:\data\raw",
    output_dir=r"E:\data\screened",
    device="auto",
    top_n=100,
)

with VocalSieveClient("vocalsieve.db") as client:
    job = client.create_job(config)
    completed = client.run_job(job.id)
    results = client.query_results(completed.id)
```

The public SDK surface is exported from `vocalsieve`; database rows and adapter
implementations are private. See [API.md](docs/API.md) for the HTTP contract.

## Docker

```powershell
$env:VOCALSIEVE_SESSION_TOKEN = "replace-with-a-long-random-value"
docker compose --profile cpu up --build
```

Use `--profile gpu` on an NVIDIA Container Toolkit host. The service is exposed
only as `127.0.0.1:8765`; input is read-only at `/data/input`, output is
`/data/output`, state is `/state`, and model cache is `/models`. See
[DOCKER.md](docs/DOCKER.md) for requests and regional mirror builds.

## Local API security

Start the native API with `vocalsieve serve`. It binds only to `127.0.0.1` and
prints a fresh session token. `/api/v1/health` is public; every endpoint that
can expose jobs, paths, results, transcripts, or events requires the token.
WebSockets additionally require an allowed localhost `Origin`.

The checked-in [OpenAPI contract](openapi.json) generates the TypeScript client
types used by the React/Vite skeleton in `web/`.

## Development and release checks

```powershell
ruff check src tests
pyright
pytest --cov=vocalsieve
python -m build
npm --prefix web ci
npm --prefix web run build
pip-audit --skip-editable
```

Contributions are welcome under the [MIT License](LICENSE). Read
[CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the
[third-party notices](THIRD_PARTY_NOTICES.md) before publishing changes.
