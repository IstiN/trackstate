# TS-684 test automation

Verifies the local `TrackStateCli` attachment-upload execution path when a
mocked GitHub release-creation `409 Conflict` occurs for a `github-releases`
attachment upload.

The automation:
1. seeds a `TS-101` snapshot with `attachmentStorage.mode = github-releases`
2. executes `TrackStateCli.run(['attachment', 'upload', ...])` for the local
   target path the ticket requires
3. mocks the GitHub release lookup as missing and the release creation endpoint
   as `HTTP 409 Conflict`
4. verifies the caller-visible CLI envelope/text is conflict-specific instead
   of a generic `REPOSITORY_OPEN_FAILED` wrapper
5. verifies no asset upload or `attachments.json` write happens after the
   release-creation conflict

## Run this test

```bash
python testing/tests/TS-684/test_ts_684.py
```

## Expected pass / fail behavior

- **Pass:** the local CLI failure itself is conflict-specific, includes
  `409` / `Conflict` / `tag already exists`, avoids the generic
  `REPOSITORY_OPEN_FAILED` wrapper, and does not mutate attachment state.
- **Fail:** the upload succeeds, reports a 422 validation-style failure, keeps
  the conflict hidden behind the generic local CLI repository error, or mutates
  attachment state after the release-creation conflict.
