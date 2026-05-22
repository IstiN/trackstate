# TS-936

Verifies that a live pull request with a failing accessibility audit is blocked
from merging by GitHub branch protection on `main`.

The automation:
1. creates a disposable pull request against `IstiN/trackstate`,
2. injects the same rendered low-contrast accessibility probe pattern used by
   the existing live accessibility-failure coverage,
3. waits for the real `Flutter Required Checks` pull-request workflow and the
   contributor-visible `Accessibility checks` status check to fail, and
4. inspects GitHub's contributor-visible merge surface plus branch-protection
   required-check configuration to confirm the PR is blocked from merge.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-936/test_ts_936.py
```
