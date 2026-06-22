# TS-1392 — Assistant Skill Manifest Assets

Verifies the presence and machine-readable content of the GitHub and Claude assistant skill manifest assets.

## Run this test

```bash
python -m unittest testing.tests.TS-1392.test_ts_1392 -v
```

## What is tested

- `assets/assistant/trackstate-github.skill` exists and is valid JSON.
- `assets/assistant/trackstate-claude.skill` exists and is valid JSON.
- Each manifest declares `schemaVersion`, `name`, `id`, `assistant`, `install`, `invocation`, and `runtime` sections.
- The file content matches the manifest constants embedded in `lib/cli/assistant_manifests.dart`.
