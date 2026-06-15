# TS-1355 test automation

Verifies that `.github/workflows/release-on-main.yml` generates release notes
that include the platform-specific manual bypass instructions required for
unsigned and unnotarized desktop packages.

## What is tested

1. The `publish-release` job appends a section titled
   `## Launching unsigned desktop packages`.
2. The section warns that desktop packages are `unsigned and unnotarized`.
3. The macOS guidance tells the user to `right-click` the app and choose `Open`.
4. The Windows guidance tells the user to click `More info`, then `Run anyway`.

## Run this test

```bash
python -m unittest testing.tests.TS-1355.test_ts_1355
```

## Notes

The latest stable release on GitHub may pre-date the fix; this test validates
the release-creation workflow/template so every subsequent release will include
the required guidance.
