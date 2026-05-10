# TS-258

Validates that the live `actionlint` gate in `IstiN/trackstate-setup` covers
newly added workflow files anywhere under `.github/workflows/`.

The automation creates a disposable branch, adds a brand-new invalid
`.github/workflows/new-utility.yml`, pushes the branch, and verifies that the
visible `actionlint` run fails and mentions the new file in its log output.

## Run this test

```bash
TS258_RESULT_PATH=outputs/ts258_observation.json \
python3 -m unittest discover -s testing/tests/TS-258 -p 'test_*.py' -v
```
