# Documentation

Start with the [English README](../README.md) or [简体中文 README](../README.zh-CN.md)
for the project overview and installation. The documents below are grouped by
audience so operational guides and maintainer procedures stay distinct.

## User and operator guides

- [Filtering and rejection reasons](guides/FILTERING.md)
- [Local HTTP API](guides/API.md)
- [CUDA setup](guides/CUDA.md)
- [FFmpeg setup and provenance](guides/FFMPEG.md)
- [Container operation](guides/DOCKER.md)

## Maintainer procedures

- [Code structure and public boundaries](maintainers/ARCHITECTURE.md)
- [Private benchmark procedure](maintainers/BENCHMARK.md)
- [Dependency maintenance](maintainers/DEPENDENCIES.md)
- [Release checklist](maintainers/RELEASE.md)

## License inventories

- [Python dependencies](PYTHON_LICENSES.md)
- [Node dependencies](NODE_LICENSES.md)

These inventories are generated in place by the release scripts; their paths are
part of the packaging workflow.
