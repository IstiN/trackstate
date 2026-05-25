# TS-419

Validates the hosted bootstrap read envelope against
`https://istin.github.io/trackstate-setup/`.

The automation:
1. opens the deployed hosted tracker while recording repository GitHub API traffic
2. verifies `.trackstate/index/issues.json` is fetched during startup
3. verifies `DEMO/project.json` plus the expected config JSON files are fetched
4. verifies startup does not eagerly request issue `main.md`, `comments/`, or
   `attachments/` artifacts
5. opens **Dashboard** and verifies the visible issue summaries match entries
   from the summary index

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-419/test_ts_419.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to the hosted app and the GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: hosted startup fetches the project/config metadata envelope and
`.trackstate/index/issues.json`, does not eagerly hydrate issue detail artifacts,
and the Dashboard visibly shows issue summaries present in the summary index.

Fail: the summary index is not fetched, required project/config JSON files are
missing, startup eagerly requests detail artifacts, or Dashboard does not show
visible summaries that match the index data.
```
