# TS-1355 test automation

Verifies that the published GitHub release notes include the required manual
bypass instructions for unsigned and unnotarized desktop packages, with
platform-specific guidance presented under semantic Markdown headings.

## What is tested

1. The `publish-release` job appends a block to the release body.
2. The block contains an unsigned/unnotarized security warning.
3. macOS guidance (`right-click` / `Open`) is present.
4. Windows guidance (`More info` / `Run anyway`) is present.
5. Each platform guidance block is introduced by an H2 or H3 Markdown heading
   so screen-reader users can navigate directly to the launch instructions.

## Run this test

```bash
python -m unittest testing.tests.TS-1355.test_ts_1355
```
