# TS-922

Validates the compile-time hardening contract for the workspace-sync widget
semantic label.

The automation:
1. copies this repository to a disposable temp workspace,
2. confirms the live production source passes the contextualized
   `_workspaceSyncSemanticLabel(l10n, viewModel)` value into the sync widget,
3. mutates that widget argument in the temp copy to the raw string
   `Attention needed`, and
4. runs `flutter analyze lib/ui/features/tracker/views/trackstate_app.dart`.

The test only passes when the analyzer/compiler blocks that raw generic string
with a real type or argument diagnostic instead of reporting a clean build.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-922/test_ts_922.py
```

## Expected behavior

The production checkout remains unchanged. The temp workspace mutation should
fail static analysis or compilation because the sync widget contract should not
accept a generic raw status string.
