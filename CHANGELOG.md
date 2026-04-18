# Changelog

## 2026-04-18

### Changed

- Added the Python package layout under `agent_language_lab/`.
- Added the Python agent protocol, loop, demo model, demo executor, runtime config, JSON serialization helper, tests, and CLI entrypoint.
- Made Python the only active implementation in the repository.
- Removed legacy source, tests, dependency metadata, generated output, and obsolete architecture notes from the previous implementation.
- Updated README, project guidance, architecture docs, and environment template around the Python runtime.

### Fixed

- Runtime config now treats an explicitly provided empty environment as authoritative instead of falling back to process environment variables.
- Auto-generated session and trace ids now use UUIDs instead of millisecond timestamps.
