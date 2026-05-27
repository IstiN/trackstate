# TS-257

Validates that an invalid pull request touching
`.github/workflows/release-on-main.yml` is blocked by a required
`actionlint` check in `IstiN/trackstate-setup`.

The automation creates a disposable branch and pull request, corrupts the
release workflow, and verifies both the contributor-visible `actionlint`
failure details and the merge-blocked PR state.

## Run this test

```bash
TS257_RESULT_PATH=outputs/ts257_observation.json \
python3 -m unittest discover -s testing/tests/TS-257 -p 'test_*.py' -v
```
