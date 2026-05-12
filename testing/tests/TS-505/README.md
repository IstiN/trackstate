# TS-505 test automation

Verifies that a `github-releases` attachment upload does **not** update
`DEMO/DEMO-1/DEMO-2/attachments.json` when the GitHub release asset
`POST .../assets` call fails with an HTTP 500.

The automation:
1. seeds a cached `DEMO-2` issue with an existing repository-path attachment
   manifest entry
2. runs the production `ProviderBackedTrackStateRepository` upload flow in
   `github-releases` mode against a scripted provider that forces the asset
   upload to fail
3. verifies the caller sees the direct upload error and the manifest text stays
   byte-for-byte unchanged without a new `release-failure.pdf` entry

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
uses the repo-local Dart probe package and runs `dart pub get --offline`
automatically before analysis and execution.

## Run this test

```bash
python testing/tests/TS-505/test_ts_505.py
```

## Required environment / config

- Python 3.12+
- A Dart SDK available on `PATH`, or set `TRACKSTATE_DART_BIN` / `TS38_DART_BIN`
  to a Dart executable. If no Dart SDK is available, the runtime can bootstrap
  one into `~/.cache/trackstate-test-tools` (or `TRACKSTATE_TOOL_CACHE` /
  `TS38_TOOL_CACHE` if set).
- `PUB_CACHE` is optional; otherwise the runtime defaults to `~/.pub-cache`.
- No external GitHub, Jira, or tracker credentials are required. The test uses
  an in-memory scripted provider and cached snapshot fixtures only.

## Expected pass / fail behavior

- **Pass:** the script exits successfully, reports the GitHub release asset
  upload failure to the caller, and writes `outputs/test_automation_result.json`
  with `"status": "passed"` after confirming `attachments.json` remained
  unchanged.
- **Fail:** the script raises an assertion error, writes
  `outputs/test_automation_result.json` with `"status": "failed"`, and records
  the observed mismatch in `outputs/bug_description.md` if the manifest changes,
  the upload error is missing, or the probe cannot validate the production flow.
