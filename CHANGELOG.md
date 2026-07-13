# Changelog

All notable changes follow Keep a Changelog and Semantic Versioning.

## [0.9.0-rc.2] - 2026-07-10

### Added
- Resource-aware concurrent jobs with SQLite-backed cross-process leases.
- Auditable manual include/exclude review in the TUI, SDK, and local API.
- Runtime capacity and structured actionable API/diagnostic responses.
- Transactional schema v3 migration with a pre-migration SQLite backup.
- Experimental local Web workflow for job creation, lifecycle control, review,
  reporting, and re-export through the versioned API.

### Changed
- Raised the default runtime capacity to two active jobs while limiting CUDA to one.
- Re-export now reconciles only files previously managed by the same job.
- Split the local API adapter into focused assembly, authentication, runtime,
  job, event, and worker modules without changing the `/api/v1` boundary.

## [0.9.0-rc.1] - 2026-06-22

### Added
- Versioned Python SDK and local API contract.
- English and Simplified Chinese TUI.
- SQLite job history, cancellation, resume, filtering, and export.
- CPU and NVIDIA GPU container targets.
- Authenticode-signed Windows portable distribution with a double-click TUI launcher.
- Rejection-code explanations, aggregate summary reports, and `vocalsieve report`.
- Fast and JSON doctor diagnostics with explicit backend fallback reporting.
- Deterministic generated-audio fixtures and a real-decoder pipeline test.

### Changed
- Rebuilt the package around a `src/` layout and structured events.
- Replaced bundled FFmpeg with runtime discovery and installation guidance.
- Added pinned post-checkout FFmpeg packaging with GPL source provenance.
- Grouped minor/patch dependency updates while keeping major updates isolated.

### Security
- Published the self-signed prerelease code-signing certificate and fingerprint
  alongside Windows assets; the private key remains in GitHub Actions secrets.
