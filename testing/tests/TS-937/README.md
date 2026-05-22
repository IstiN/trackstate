# TS-937

Validates that the dedicated workspace sync semantic-label regression test exists,
targets the live `_SyncPill` API contract, and passes through the real Flutter
test runner.

The automation:
1. opens `test/workspace_sync_semantic_label_contract_test.dart`
2. confirms the test case mutates the live sync widget call site from the
   localized wrapper to a raw `'Attention needed'` string before rerunning
   `flutter analyze`
3. confirms the live `_SyncPill` field, typed helper, and call site still use
   the `_SyncPillSemanticLabel` wrapper contract
4. runs `flutter test test/workspace_sync_semantic_label_contract_test.dart -r expanded`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-937/test_ts_937.py
```

## Expected behavior

The dedicated Flutter regression test passes, proving the live sync widget API
is still guarded against primitive `String` semantic labels and the unit test is
ready to catch regressions.
