# TS-1344 test automation

Verifies that `.github/workflows/release-on-main.yml` defines the expected
Linux and Windows build jobs, steps, outputs, and artifact naming conventions.

## What is tested

1. The workflow contains `build-linux` and `build-windows` jobs.
2. Each job runs on the correct hosted runner:
   - `build-linux` → `ubuntu-latest`
   - `build-windows` → `windows-latest`
3. Each job defines steps for desktop build, CLI build, packaging, and artifact upload.
4. Each job exposes `desktop_archive`, `cli_archive`, and `artifact_name` outputs.
5. Artifact names reflect platform and version:
   - Linux desktop: `TrackState-linux-x64-vX.Y.Z.tar.gz`
   - Linux CLI: `trackstate-cli-linux-x64-vX.Y.Z.tar.gz`
   - Windows desktop: `TrackState-windows-x64-vX.Y.Z.zip`
   - Windows CLI: `trackstate-cli-windows-x64-vX.Y.Z.tar.gz`
6. Upload steps fail fast with `if-no-files-found: error`.

## Run this test

```bash
python -m unittest testing.tests.TS-1344.test_ts_1344
```

## Outputs

On completion the test writes:

- `outputs/test_automation_result.json`
- `outputs/response.md` (Jira wiki markup)
- `outputs/pr_body.md` (GitHub Markdown)
- `outputs/bug_description.md` (only on failure)
