ARG CPU_BASE=python:3.12-slim-bookworm
ARG GPU_BASE=nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04

FROM ${CPU_BASE} AS cpu
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 VOCALSIEVE_CONTAINER=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 vocalsieve
RUN mkdir -p /state /models /data/input /data/output \
    && chown -R vocalsieve:vocalsieve /state /models /data
WORKDIR /app
COPY pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir ".[api]"
USER vocalsieve
EXPOSE 8765
ENTRYPOINT ["vocalsieve"]
CMD ["--database", "/state/vocalsieve.db", "serve", "--port", "8765"]

FROM ${GPU_BASE} AS gpu
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    VOCALSIEVE_CONTAINER=1 PATH=/opt/venv/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv ffmpeg libsndfile1 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv \
    && useradd --create-home --uid 10001 vocalsieve
RUN mkdir -p /state /models /data/input /data/output \
    && chown -R vocalsieve:vocalsieve /state /models /data
WORKDIR /app
COPY pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[api]"
USER vocalsieve
EXPOSE 8765
ENTRYPOINT ["vocalsieve"]
CMD ["--database", "/state/vocalsieve.db", "serve", "--port", "8765"]
