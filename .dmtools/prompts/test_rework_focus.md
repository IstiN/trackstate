# TrackState Test Rework Focus

- Fix only review findings that are actionable inside `testing/`.
- Do not modify production code, workflow files, or non-testing project files.
- Do not make a product-gap test pass by hardcoding the final state, weakening assertions, or replacing the required production action with a synthetic fixture.
- If the required behavior is missing from production code or public APIs, keep the test as a faithful reproduction, mark `outputs/test_automation_result.json` as `"failed"`, and write a detailed `outputs/bug_description.md`.
- The bug description must explain the missing/broken production capability, exact reproduction steps, expected vs actual behavior, and the failing command/output.
- Missing production behavior is not `blocked_by_human`; it is a failed Test Case that should flow to bug creation.
