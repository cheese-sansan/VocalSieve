# Dependency maintenance

Dependabot minor and patch updates are grouped by ecosystem. Major updates stay
in separate pull requests and are never merged solely to reduce the open PR
count. A cancelled check is not a successful check.

## Current pull-request triage

This snapshot was recorded on 2026-06-22. Recheck the diff, upstream migration
notes, merge state, and full CI before acting.

| PR | Change | Risk | Decision |
| --- | --- | --- | --- |
| #2 | pytest-cov 6 to 7 | low-medium | Validate coverage semantics and merge independently. |
| #6 | setup-python 5 to 6 | medium | Prioritize after confirming all runner versions. |
| #7 | setup-node 4 to 6 | medium | Prioritize after confirming Node 24 runner support. |
| #8 | docker/login-action 3 to 4 | medium | Review removed inputs; merge independently if the full matrix passes. |
| #10 | actions/checkout 4 to 7 | medium | Confirm self-hosted runner support before merge. |
| #12 | docker/setup-buildx-action 3 to 4 | medium | Confirm Node 24 and removed-input compatibility. |
| #4 | Textual 1 to 8 | high | Close or defer; replace with one-major-at-a-time upgrades and TUI pilot tests. |
| #3 | plugin-react 4 to 6 | high | Defer to the coordinated web-toolchain branch. |
| #5 | TypeScript 5 to 6 | high | Defer; current checks include failures. |
| #9 | Vite 6 to 8 | high | Defer and upgrade through supported intermediate versions. |
| #11 | lucide-react 0.x to 1.x | high | Defer and visually inspect the web skeleton separately. |

## Required validation

Python dependency changes run:

```powershell
ruff check src tests
pyright
pytest --cov=vocalsieve
python -m build
pip-audit --skip-editable
```

Web dependency changes run:

```powershell
npm --prefix web ci
npm --prefix web audit --audit-level=high
npm --prefix web run build
```

GitHub Actions and Docker major updates additionally require the complete
hosted CI matrix. Changes used by `gpu.yml` or `windows-package.yml` must also
run on the self-hosted GPU runner before release work continues.
