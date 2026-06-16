# TS-504 test automation

Verifies that a hosted `github-releases` attachment upload fails when the target
release container already contains a foreign asset that is not tracked in
`attachments.json`.

The automation:
1. seeds `DEMO/TS-400` in the live setup repository with
   `attachmentStorage.mode = github-releases`, an empty `attachments.json`
   manifest, and a release container for `TS-400`
2. uploads a foreign `extra_file.zip` asset directly to that release so the
   release state no longer matches TrackState's manifest
3. runs the real production `trackstate attachment upload --target hosted
   --provider github ...` flow with a valid attachment payload
4. verifies the CLI returns the expected repository conflict error naming the
   unexpected asset and manual cleanup requirement
5. verifies the remote release still contains only the foreign asset and that
   `attachments.json` remains unchanged

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles the repo-local Dart CLI before executing the hosted upload scenario.

## Run this test

```bash
python testing/tests/TS-504/test_ts_504.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Network access to GitHub APIs and release uploads

## Expected pass / fail behavior

- **Pass:** the command exits with the expected repository failure, the JSON
  error envelope names `extra_file.zip` and manual cleanup, and the release
  state remains unchanged with an empty `attachments.json` manifest.
- **Fail:** the upload succeeds, the error shape/message is wrong, the foreign
  asset disappears or is absorbed, the manifest changes, or the hosted fixture
  cannot be exercised through the production-visible GitHub flow.
