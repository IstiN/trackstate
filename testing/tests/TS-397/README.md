# TS-397

Validates the live hosted **Edit issue** surface for `DEMO-3` against the
deployed tracker at `https://istin.github.io/trackstate-setup/`.

The automation:
1. opens the production **Edit issue** dialog for `DEMO-3`
2. reads the project-defined **Components** and **Fix versions** values from the
   live setup repository config
3. verifies the live edit surface shows only those values as selectable chips
4. verifies the deployed UI does not expose an inline text input, listbox, or
   other ad-hoc entry surface for either field
5. fails with production-visible evidence when the hosted app exposes extra
   values or allows inline entry

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-397/test_ts_397.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to the hosted app and GitHub API

## Expected result

```text
Pass: the live Edit issue surface shows only project-configured Components and
Fix versions values, and the deployed UI exposes no inline input path for
creating ad-hoc metadata values.

Fail: the hosted edit surface shows extra values, omits configured values, or
exposes an inline entry surface that would allow ad-hoc metadata creation.
```
