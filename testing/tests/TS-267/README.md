# TS-267

Verifies that the live `IstiN/trackstate-setup` repository publishes
`.github/dependabot.yml` with a `github-actions` update block rooted at `/` and
an update schedule, then checks the visible GitHub file page through the
Playwright browser path.

## Run this test

```bash
TS267_RESULT_PATH=outputs/ts267_observation.json \
python3 -m unittest discover -s testing/tests/TS-267 -p 'test_*.py' -v
```
