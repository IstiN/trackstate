# TS-484 test automation

Verifies that hosted GitHub Release-backed attachment uploads use the
deterministic per-issue release container and replace an existing asset when the
same sanitized file name is uploaded again.

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles the repo-local Dart CLI before exercising the live hosted upload flow.

## Run this test

```bash
python3 testing/tests/TS-484/test_ts_484.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Network access to GitHub APIs and release uploads

## Scenario notes

- Seeds `DEMO/TS-123` in the live setup repository and enables
  `attachmentStorage.mode = github-releases` with the default
  `trackstate-attachments-` prefix.
- Uploads `design_v1.png` through the real hosted CLI twice.
- A passing result means:
  - the first upload resolves to release tag `trackstate-attachments-TS-123`
    with title `Attachments for TS-123`
  - the public attachment id stays issue-scoped and backend-agnostic
  - the second upload keeps the same release container and logical attachment id
    while the GitHub Release still exposes exactly one `design_v1.png` asset.
