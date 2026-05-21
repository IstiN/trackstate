# TS-908

## Objective

Verify that the live pull-request CI pipeline actually detects and blocks a PR that
introduces both a low-contrast Flutter widget and a non-descriptive semantics label.

## Automation approach

This test now exercises the real PR path instead of inspecting workflow source text:

1. creates a disposable branch and PR against `main`;
2. adds a Flutter probe widget under `lib/` with reduced text contrast and a weak
   semantics label;
3. waits for the live `Flutter Required Checks` PR workflow run on that disposable PR;
4. inspects the actual PR checks surface plus workflow jobs, steps, and logs for an
   accessibility result that reports both the contrast and semantic defects.

If GitHub exposes the PR run but no accessibility-oriented failing check/result exists,
the test fails as a real product gap and writes a bug description.
