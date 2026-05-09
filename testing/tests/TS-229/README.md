# TS-229 test automation

This test verifies that `IstiN/trackstate-setup` exposes releases and tags
through the public GitHub API and that both arrays include stable version tags
in `v<major>.<minor>.<patch>` format.

It also performs a human-style verification by checking that the latest common
stable version appears on the public GitHub Releases and Tags pages.

## Run this test

```bash
TS229_RESULT_PATH=outputs/ts229_observation.json \
python3 -m unittest discover -s testing/tests/TS-229 -p 'test_*.py' -v
```

## Optional environment variables

- `TRACKSTATE_RELEASE_TAG_REPOSITORY` (default: `IstiN/trackstate-setup`)
- `TRACKSTATE_EXPECTED_STABLE_VERSION` (optional, disabled by default)
