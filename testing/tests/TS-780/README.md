# TS-780

Validates the real production serialization path for `RepositorySyncCheck`
when the hosted compare flow returns an explicit `load_snapshot_delta=0`
directive.

The ticket test now consumes a reusable component service under
`testing/components/services/`, which hides the concrete GitHub framework
adapter and keeps the required `tests -> components -> frameworks -> core`
layering intact. That service drives the production `GitHubTrackStateProvider`
compare-sync path, then attempts to serialize the returned
`RepositorySyncCheck` through Dart's shipped JSON encoding path (`jsonEncode`)
instead of a test-owned mapper.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-780/test_ts_780.dart --reporter expanded
```

## Environment variables / config

No extra environment variables are required. The test uses mocked GitHub HTTP
responses and the in-repo Flutter test environment.

## Expected output

```text
Pass: the production serializer emits a payload map that omits
load_snapshot_delta for the no-flag control path and includes
load_snapshot_delta: 0 for the explicit-false path.

Fail: RepositorySyncCheck cannot be serialized through the shipped production
JSON path, or the serialized explicit-false payload still omits
load_snapshot_delta / uses a non-zero value / is indistinguishable from the
control payload.
```
