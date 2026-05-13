# TS-608 test automation

Verifies that re-uploading a hosted attachment with the same filename replaces
the live GitHub Release asset bytes instead of only updating metadata.

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles the repo-local Dart CLI before exercising the live hosted upload flow.

## Run this test

```bash
python3 testing/tests/TS-608/test_ts_608.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Network access to GitHub APIs and release uploads

## Scenario notes

- Reuses the proven hosted release-replacement flow already automated for
  `TS-484`.
- Seeds `DEMO/TS-123` in the live setup repository and enables
  `attachmentStorage.mode = github-releases` with tag prefix
  `trackstate-attachments-`.
- Uploads `design_v1.png` twice and verifies the second upload replaces the
  downloaded release asset bytes, not only the manifest metadata.
