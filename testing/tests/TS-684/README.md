# TS-684 test automation

Verifies that a mocked GitHub release-creation `409 Conflict` response is
surfaced to the caller as a resource-conflict-style failure when a
`github-releases` attachment upload starts.

The automation:
1. seeds a cached issue snapshot for `TS-101` with `attachmentStorage.mode =
   github-releases`
2. runs the production attachment upload flow through
   `ProviderBackedTrackStateRepository` and `GitHubTrackStateProvider`
3. mocks the GitHub release lookup as missing and the release creation endpoint
   as `HTTP 409 Conflict`
4. verifies the caller-visible error contains the conflict details such as
   `409`, `Conflict`, and `tag already exists`
5. verifies no asset upload or `attachments.json` write happens after the
   release-creation conflict

## Run this test

```bash
python testing/tests/TS-684/test_ts_684.py
```

## Expected pass / fail behavior

- **Pass:** the upload fails with a visible release-creation conflict that
  includes `409` / `Conflict` / `tag already exists`, and no asset upload or
  metadata write is attempted.
- **Fail:** the upload succeeds, reports a 422 validation-style failure, hides
  the conflict behind a generic error, or mutates attachment state after the
  release-creation conflict.
