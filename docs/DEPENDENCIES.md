# Dependency maintenance

VocalSieve does not use automatic dependency update pull requests. Dependency
remediation is performed on a maintainer-controlled branch named
`chore/dependency-maintenance-YYYYMMDD`; it is never merged only to reduce an
audit count or close an alert.

## Maintenance procedure

1. Identify the affected direct and transitive packages, their fixed versions,
   and upstream compatibility notes.
2. Prefer the smallest compatible patch or minor upgrade. Major upgrades are
   isolated in their own maintenance branch and require focused migration tests.
3. Regenerate the applicable lockfiles without changing unrelated direct
   dependencies, then inspect the complete diff.
4. Require every relevant local validation and the complete hosted CI matrix
   before merging. A cancelled check is not a successful check.

Privileged self-hosted workflows install Python dependencies with `uv sync
--frozen` before any signing secret is exposed. Container base overrides must use
verified digests. The Web lock currently resolves the high-severity `nanoid`
advisory at `3.3.18`; the Python lock keeps pip and setuptools at their audited
fixed versions.

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
