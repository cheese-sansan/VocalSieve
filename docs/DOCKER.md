# Docker

Create `data/input` and `data/output`, set a strong token, then choose one
profile:

```powershell
$env:VOCALSIEVE_SESSION_TOKEN = "replace-with-a-long-random-value"
docker compose --profile cpu up --build
docker compose --profile gpu up --build
```

Compose publishes only `127.0.0.1:8765`. Mounts are fixed by convention:

- `/data/input`: read-only source corpus
- `/data/output`: selected files and reports
- `/state`: SQLite state
- `/models`: persistent model cache

API requests must use container paths, not host paths. For example,
`source_dir` is `/data/input` and `output_dir` is `/data/output`.

For networks where Docker Hub is unavailable, override the build base without
changing the Dockerfile:

```powershell
docker build --build-arg CPU_BASE=mirror.example/library/python:3.12-slim-bookworm --target cpu -t vocalsieve:cpu .
docker build --build-arg GPU_BASE=mirror.example/nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04 --target gpu -t vocalsieve:gpu .
```

Release validation commands:

```powershell
docker run --rm vocalsieve:cpu doctor
docker run --rm --gpus all -v vocalsieve-models:/models -e HF_HOME=/models vocalsieve:gpu doctor --deep --device cuda --model tiny
```
