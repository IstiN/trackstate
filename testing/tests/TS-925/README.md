# TS-925

## Objective

Verify the live CI fail-fast policy: an accessibility audit failure on a disposable
pull request must block any downstream deploy or publish stage.

## Automation approach

1. creates a disposable pull request with a rendered low-contrast accessibility probe;
2. waits for the live `Flutter Required Checks` pull-request workflow run;
3. inspects the actual GitHub Actions jobs and status checks for the accessibility
   failure;
4. opens the live run page for human-style verification and checks whether any
   downstream deploy/publish stage is skipped or blocked.

If the workflow does not expose a downstream deployment stage at all, or if that
stage still proceeds after the accessibility failure, the test fails as a real
product gap and writes a bug description.
