# TS-1355 — Release Note Instructions

Static validation that the `release-on-main.yml` workflow generates release notes containing:

- A security warning that desktop packages are unsigned and unnotarized.
- Platform-specific launch guidance for macOS (`right-click` → `Open`) and Windows (`More info` → `Run anyway`).
- Semantic Markdown headings (`##`, `###`) for screen-reader navigation.

The test does not publish a release.
