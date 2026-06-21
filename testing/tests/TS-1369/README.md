# TS-1369 test automation

Verifies that the generated release notes contain a structured table accurately
listing all desktop and CLI artifacts with their corresponding platform and
architecture details.

## What is tested

1. A release tag is selected from:
   - `TS1369_RELEASE_TAG` environment variable,
   - GitHub Actions CI metadata for a version-tag workflow run, or
   - the latest published GitHub release.
2. The release body is fetched from GitHub.
3. The release notes include a "Compiled artifacts" section with a Markdown table.
4. The table lists the six expected artifacts:
   - Linux desktop (`TrackState-linux-x64-vX.Y.Z.tar.gz`) and CLI (`trackstate-cli-linux-x64-vX.Y.Z.tar.gz`) labeled `x64`
   - Windows desktop (`TrackState-windows-x64-vX.Y.Z.zip`) and CLI (`trackstate-cli-windows-x64-vX.Y.Z.tar.gz`) labeled `x64`
   - macOS desktop (`TrackState-macos-arm64-vX.Y.Z.zip`) and CLI (`trackstate-cli-macos-arm64-vX.Y.Z.tar.gz`) labeled `arm64`

## Run this test

```bash
mkdir -p outputs && python testing/tests/TS-1369/test_ts_1369.py
```

## Required environment

- `gh` CLI available on `PATH` (public repository access is sufficient).
- Optional: `TS1369_RELEASE_TAG` to target a specific release tag.

## Expected pass / fail / blocked behavior

- **Pass:** the release notes contain a compiled artifacts table with all six
  artifacts listed and correct architecture labels.
- **Fail:** the table is missing, a platform or artifact is missing, or an
  architecture label is incorrect.
- **Blocked:** the selected release cannot be inspected (no matching release or
  no release body available).
