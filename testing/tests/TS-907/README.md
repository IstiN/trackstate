# TS-907

Validates the local pre-commit accessibility analysis flow for the sync-pill
semantic label regression described in the ticket.

The automation:
1. exports the current `origin/main` snapshot to a disposable temp workspace,
2. verifies the current main snapshot uses the dedicated typed
  `_workspaceSyncAttentionNeededSemanticLabel(l10n)` helper at the live sync-pill
  semantic-label call site,
3. downgrades that call site in the temp copy to the generic
  `_workspaceSyncAttentionNeededVisibleLabel(l10n)` value, and
4. runs `flutter analyze lib/ui/features/tracker/views/trackstate_app.dart`.

The test only passes when the local analysis command stops looking clean and
blocks the weakened semantic label with a real analyzer diagnostic instead of
reporting `No issues found!`.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-907/test_ts_907.py
```

## Expected behavior

The production checkout remains unchanged. The temp workspace mutation against
the current `main` implementation should be blocked by a terminal-visible
analyzer diagnostic from `flutter analyze`.
