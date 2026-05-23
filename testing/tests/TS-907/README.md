# TS-907

Validates the local pre-commit accessibility analysis flow for the sync-pill
semantic label regression described in the ticket.

The automation:
1. exports the current `origin/main` snapshot to a disposable temp workspace,
2. verifies the current main snapshot uses the dedicated typed
   `workspaceSyncAttentionNeededSemanticLabel` localization wrapper access for
   the attention-needed sync pill,
3. downgrades that wrapper access in the temp copy to
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

The production checkout remains unchanged. The temp workspace mutation against
the current `main` implementation should be blocked by a terminal-visible
accessibility diagnostic from `flutter analyze`.
