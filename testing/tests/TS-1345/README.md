# TS-1345 test automation

Verifies that `.github/workflows/release-on-main.yml` defines a final
`publish-release` job that aggregates Linux, Windows, and macOS artifacts plus
a unified SHA256 checksum file into a single GitHub Release.

## What is tested

1. The `publish-release` job exists and depends on all three platform build jobs.
2. Steps download Linux, Windows, and macOS artifacts.
3. A unified `trackstate-vX.Y.Z.sha256` file is generated covering all six binaries
   (Linux desktop + CLI, Windows desktop + CLI, macOS desktop + CLI).
4. The `gh release upload` command publishes the six platform archives plus the
   unified checksum file.
5. The job uses `gh release create`, `gh release upload`, and `gh release edit`.
6. The release is marked non-draft and non-prerelease with title `TrackState vX.Y.Z`.

## Run this test

```bash
python -m unittest testing.tests.TS-1345.test_ts_1345
```
