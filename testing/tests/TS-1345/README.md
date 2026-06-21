# TS-1345 test automation

Verifies that `.github/workflows/release-on-main.yml` defines:
1. A `publish-release` job that aggregates Linux and Windows artifacts plus
   a unified SHA256 checksum file into a single GitHub Release.
2. A `publish-macos-release` job that downloads macOS artifacts, generates a
   separate `trackstate-apple-vX.Y.Z.sha256` checksum, and uploads macOS assets
   to the same release.

## What is tested

1. The `publish-release` job exists and depends on `build-linux` and `build-windows`.
2. The `publish-macos-release` job exists and depends on `build-macos` and `publish-release`.
3. Steps download Linux, Windows, and macOS artifacts in their respective jobs.
4. A unified `trackstate-vX.Y.Z.sha256` file is generated covering Linux and Windows binaries
   (Linux desktop + CLI, Windows desktop + CLI).
5. A separate `trackstate-apple-vX.Y.Z.sha256` file is generated covering macOS binaries
   (macOS desktop + CLI).
6. The `gh release upload` command publishes all platform archives plus both checksum files.
7. The job uses `gh release create`, `gh release upload`, and `gh release edit`.
8. The release is marked non-draft and non-prerelease with title `TrackState vX.Y.Z`.

## Run this test

```bash
python -m unittest testing.tests.TS-1345.test_ts_1345
```
