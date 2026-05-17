# TS-654

Validates that opening an issue with non-canonical link metadata in the TrackState
UI emits a schema-validation warning through the UI rendering pipeline.

The automation:
1. seeds the production issue-detail flow with `TRACK-12/links.json` containing
   `{"type":"blocks","target":"TRACK-11","direction":"inward"}`
2. opens `TRACK-12` in the production Flutter issue-detail UI
3. captures user-visible detail content plus system log output
4. verifies the issue detail stays visible and that the logs mention the
   non-canonical `blocks` / `inward` metadata mismatch

## Run this test

```bash
flutter test testing/tests/TS-654/test_ts_654.dart --reporter expanded
```
