# TS-658

Validates that `trackstate ticket link` rejects an unsupported relationship
type in a disposable Local Git repository and leaves no persisted relationship
data behind.

The automation creates Issue A and Issue B, runs:

```bash
trackstate ticket link --target local --key TS-1 --target-key TS-2 --type "unsupported-relationship-type"
```

and then asserts that the visible CLI JSON response reports a validation error
with exit code `2` while no `links.json` artifact is created.

## Install dependencies

No Python packages are required beyond the standard library. Ensure these tools
are available before running the test:

1. `python3`
2. `flutter`
3. `git`

## Run this test

```bash
python3 -m unittest testing.tests.TS-658.test_ts_658
```

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
