# TS-1241

Validates the live hosted stale-base-SHA save regression against the deployed
tracker at `https://istin.github.io/trackstate-setup/`.

The automation:
1. seeds a hosted workspace profile whose `writeBranch` is an old commit SHA
2. opens the production **Edit issue** flow for `DEMO-3992`
3. creates a concurrent GitHub commit so the stored write ref is stale
4. changes **Priority** to `Highest` and **Status** to `Done`
5. saves the edit and verifies the visible success banner plus dialog close
6. proves the GitHub save sequence fetches the latest branch ref and commit SHA
   before posting the replacement tree

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1241/test_ts_1241.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` with write access to `IstiN/trackstate-setup`
- network access to the hosted app and GitHub API

## Expected result

```text
Pass: even with a stale hosted write ref, saving DEMO-3992 fetches the latest
GitHub branch ref and commit SHA immediately before the tree update, shows a
success banner, closes the editor, and leaves no visible 422 error.

Fail: the hosted edit save path still uses the stale SHA, skips the latest ref /
commit fetches, surfaces a save error (including 422 / Invalid object requested),
or does not close the editor after save.
```
