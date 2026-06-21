# TS-1347 test automation

Verifies that `.github/workflows/release-on-main.yml` generates a release body
that combines GitHub's auto-generated notes with a structured scaffold for
installation guidance.

## What is tested

1. The `publish-release` job calls the GitHub `releases/generate-notes` API.
2. The release body uses semantic Markdown headers, including at least one H1
   (`# `) and H2 (`## `), for logical screen-reader navigation.
3. The release body includes a `Quick Start` or `Installation` section title.
4. The release body appends a `## Compiled artifacts` section.
5. The artifacts table lists Linux, macOS, and Windows platforms with Desktop
   and CLI columns.
6. The scaffold mentions the unified checksum file and the CLI install commands
   for Linux, macOS, Windows PowerShell, and Windows Command Prompt.
7. The scaffold includes an accessible `## Launching unsigned desktop packages`
   section with macOS (`right-click` → `Open`) and Windows (`More info` →
   `Run anyway`) launch guidance.
8. The release title follows `TrackState vX.Y.Z`.

## Run this test

```bash
python -m unittest testing.tests.TS-1347.test_ts_1347
```
