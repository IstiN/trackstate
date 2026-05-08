# TrackState Test Review Focus

- Review the test PR as a test artifact, not as a product implementation PR.
- If the test passed, reject synthetic coverage that pre-authors the expected final state instead of exercising the production-visible behavior from the Test Case.
- If the test failed, decide whether the failure is caused by bad test code or by a real product defect/product API gap.
- Approve a failed test when it correctly exercises the Test Case, fails for a genuine product defect or missing production capability, and includes enough bug evidence for bug creation.
- Request changes only when the test itself is wrong, incomplete, flaky, synthetic, outside `testing/`, or missing a useful bug description.
- Do not keep looping on the same product gap. Once the failure is a valid product failure, approval should let the Test Case reach `Failed` so the bug creation agent can create or link the Bug.
