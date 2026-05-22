# TS-923

Validates the compliant side of the sync-pill semantic-label analyzer rule.

The automation:
1. copies this repository to a disposable temp workspace,
2. verifies the live production source still uses the localized
   `workspaceSyncAttentionNeededSemanticLabel` getter for the attention-needed
   sync pill,
3. verifies the English localization value keeps the required
   `Sync error` semantic prefix, and
4. runs `flutter analyze lib/ui/features/tracker/views/trackstate_app.dart`.

The test only passes when the unmodified implementation stays analyzer-clean and
reports `No issues found!` with exit code `0`.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-923/test_ts_923.py
```

## Expected behavior

The production checkout remains unchanged. The temp workspace analysis should
stay clean and confirm that valid semantic labels are allowed.
