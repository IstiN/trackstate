# TS-1344 test automation

Verifies that `.github/workflows/release-on-main.yml` defines the expected
Linux and Windows build jobs, steps, outputs, and artifact naming conventions.

## What is tested

1. The workflow contains `build-linux` and `build-windows` jobs.
2. Each job defines steps for desktop build, CLI build, packaging, and artifact upload.
3. Each job exposes `desktop_archive`, `cli_archive`, and `artifact_name` outputs.
4. Artifact names reflect platform and version:
   - Linux desktop: `TrackState-linux-x64-vX.Y.Z.tar.gz`
   - Linux CLI: `trackstate-cli-linux-x64-vX.Y.Z.tar.gz`
   - Windows desktop: `TrackState-windows-x64-vX.Y.Z.zip`
   - Windows CLI: `trackstate-cli-windows-x64-vX.Y.Z.tar.gz`

## Run this test

```bash
python -m unittest testing.tests.TS-1344.test_ts_1344
```
