# Changelog

All notable changes follow Keep a Changelog and Semantic Versioning.

## [Unreleased]

### Added
- Added `GET /api/v1/jobs/{job_id}/report` so HTTP clients can fetch the same
  aggregate job summary as `vocalsieve report`.
- Completed a minimal local Web UI workflow for creating jobs, selecting jobs,
  viewing events/results/report summaries, and triggering export.

### Changed
- Split the FastAPI adapter into app assembly, auth, runtime, job, event, and
  worker modules while preserving `from vocalsieve.api import create_app`.
- Tightened the API contract with typed `ConfigResponse`, `ReportResponse`,
  `RejectionSummary`, `BackendSummary`, and `ThresholdSummary` schemas.
- Regenerated the checked-in OpenAPI contract and TypeScript API types.

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
