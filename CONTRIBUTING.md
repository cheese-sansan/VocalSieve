# Contributing

Dependency updates follow the risk and validation policy in
[docs/DEPENDENCIES.md](docs/DEPENDENCIES.md). Automated Dependabot update PRs
are disabled; maintainers use a `codex/dependency-maintenance-YYYYMMDD` branch
when the weekly security workflow, a vulnerability alert, or release preparation
identifies an update.

1. Create a branch from `main`.
2. Install development dependencies with `uv sync --all-extras`.
3. Run `ruff check .`, `pyright`, and `pytest --cov` before opening a pull request.
4. Add tests for behavioral changes and update the changelog for user-visible changes.

Do not include model weights, private audio, generated outputs, databases, or
third-party binaries in commits. By contributing, you agree that your changes
are licensed under the MIT License.

## AI-assisted commits

Project direction, decisions, review, and release ownership remain with the
maintainer. When ChatGPT Codex materially assists a commit, use this exact trailer:

```text
Co-authored-by: ChatGPT Codex <chatgpt-codex-connector[bot]@users.noreply.github.com>
```

Do not add the trailer to work that was not materially assisted by ChatGPT Codex.

## Release validation

Run the local release gate from a clean worktree:

```powershell
.\scripts\release_gate.ps1 -SkipDocker
```

Maintainers use `-BuildPortable` and an authorized corpus path for the full
Windows CUDA gate. Never commit models, audio corpora, signing certificates, or
FFmpeg binaries.
