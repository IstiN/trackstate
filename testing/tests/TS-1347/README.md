# TS-1347 test automation

Verifies that `.github/workflows/release-on-main.yml` generates a release body
that combines GitHub's auto-generated notes with a structured scaffold for
installation guidance.

## What is tested

1. The `publish-release` job calls the GitHub `releases/generate-notes` API.
2. The release body appends a `## Compiled artifacts` section.
3. The artifacts table lists Linux, macOS, and Windows platforms with Desktop
   and CLI columns.
4. The scaffold mentions the unified checksum file and a placeholder for future
   install commands.
5. The release title follows `TrackState vX.Y.Z`.

## Run this test

```bash
python -m unittest testing.tests.TS-1347.test_ts_1347
```
