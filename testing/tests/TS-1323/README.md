# TS-1323

Verifies the attachment upload pipeline rejects a success-shaped response when the stored file is shorter than the source payload.

## Scenario

The test seeds a local repository-backed TrackState fixture, truncates the stored attachment bytes in the fake storage layer, and then calls the production upload flow.

## Run

```bash
flutter test testing/tests/TS-1323/test_ts_1323.dart --reporter expanded
```

## Expected result

The upload should fail, and no success-shaped attachment response or attachment metadata write should be produced after the stored byte count differs from the source byte count.
