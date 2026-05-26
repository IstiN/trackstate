# TS-536 test automation

Verifies that a release-backed attachment upload reuses an existing draft release
when the release already has the correct tag and title but its body was manually
edited to `Manual Notes`.

The automation:
1. switches the live DEMO project to `github-releases` mode with tag prefix
   `trackstate-attachments-`
2. seeds issue `TS-50` and an empty `attachments.json` manifest
3. creates or normalizes the draft release `trackstate-attachments-TS-50` with
   title `Attachments for TS-50` and body `Manual Notes`
4. uploads a unique attachment through the production Dart repository code
5. verifies the manifest points at the seeded release tag and GitHub shows the
   same release id with the uploaded asset
6. accepts either preserved body text (`Manual Notes`) or normalization to the
   standard machine-managed attachment note

## Run this test

```bash
python testing/tests/TS-536/test_ts_536.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `GH_TOKEN` or `GITHUB_TOKEN`
- Network access to the live setup repository configured by
  `TRACKSTATE_LIVE_SETUP_REPOSITORY` / `TRACKSTATE_LIVE_SETUP_REF`
