# TS-796

Verifies that the active local workspace keeps its local repository metadata
visible without suppressing the GitHub sign-in entry point.

The automation:
1. seeds the production workspace profile store with one active local workspace
   and one inactive hosted workspace
2. launches the production tracker in a Flutter widget runtime that can open
   the active local repository
3. opens **Workspace switcher** and verifies the active local row still shows
   the local repository path, branch metadata, and `Local Git` state
4. opens **Settings** from the active local workspace and verifies the
   repository-access surface still shows `Connect GitHub` together with the
   local `Repository Path` and `Write Branch` fields
5. taps **Connect GitHub** and confirms the production connection dialog opens,
   then closes it and verifies the local metadata remains visible

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-796/test_ts_796.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: the active local workspace row keeps its local repository metadata/path
visible, and the active local Repository access surface still exposes a visible,
working Connect GitHub control instead of suppressing it.
```
