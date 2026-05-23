# TS-907

Validates the local pre-commit accessibility analysis flow for the sync-pill
semantic label regression described in the ticket.

The automation:
1. copies this repository to a disposable temp workspace,
2. verifies the live production source currently uses the dedicated
   typed `workspaceSyncAttentionNeededSemanticLabel` localization wrapper inside
   `_workspaceSyncAttentionNeededSemanticLabel()`,
3. downgrades that wrapper access inside the temp copy to
   `workspaceSyncAttentionNeededVisibleLabel`, and
4. runs `flutter analyze lib/ui/features/tracker/views/trackstate_app.dart`.

The test only passes when the local analysis command stops looking clean and
surfaces a real diagnostic for that weakened semantic label instead of
reporting `No issues found!`.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-907/test_ts_907.py
```

## Expected behavior

The production checkout remains unchanged. The temp workspace mutation should be
blocked by a terminal-visible accessibility diagnostic from `flutter analyze`.
