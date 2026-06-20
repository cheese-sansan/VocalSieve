# Contributing

1. Create a branch from `main`.
2. Install development dependencies with `uv sync --all-extras --dev`.
3. Run `ruff check .`, `pyright`, and `pytest --cov` before opening a pull request.
4. Add tests for behavioral changes and update the changelog for user-visible changes.

Do not include model weights, private audio, generated outputs, databases, or
third-party binaries in commits. By contributing, you agree that your changes
are licensed under the MIT License.
## Release validation

Run the local release gate from a clean worktree:

```powershell
.\scripts\release_gate.ps1 -SkipDocker
```

Maintainers use `-BuildPortable` and an authorized corpus path for the full
Windows CUDA gate. Never commit models, audio corpora, signing certificates, or
FFmpeg binaries.
