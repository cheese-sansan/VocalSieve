# Changelog

All notable changes follow Keep a Changelog and Semantic Versioning.

## [0.9.0-rc.1] - Unreleased

### Added
- Versioned Python SDK and local API contract.
- English and Simplified Chinese TUI.
- SQLite job history, cancellation, resume, filtering, and export.
- CPU and NVIDIA GPU container targets.
- Windows portable and signing build tooling with a double-click TUI launcher.

### Changed
- Rebuilt the package around a `src/` layout and structured events.
- Replaced bundled FFmpeg with runtime discovery and installation guidance.
- Added pinned post-checkout FFmpeg packaging with GPL source provenance.
