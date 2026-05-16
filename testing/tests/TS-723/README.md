# TS-723

Validates that startup restoration skips an invalid most-recent workspace and
automatically falls back to the next most recent valid workspace instead of
routing the user into Settings.

The automation:
1. preloads three saved workspaces where W1 is the active invalid local
   workspace, W2 is the next most recent valid hosted workspace, and W3 is the
   oldest hosted workspace
2. launches the deployed TrackState app and waits for the interactive shell to
   render after startup restoration
3. verifies the visible non-blocking restore message names W1 and includes the
   skip reason
4. verifies the workspace switcher trigger and persisted workspace state both
   promote W2 as the active workspace

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-723/test_ts_723.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` for the live hosted repository fixture
- any other live setup configuration required by
  `testing.core.config.live_setup_test_config`

## Expected result

```text
Pass: startup restoration skips W1, shows a non-blocking message naming W1 and
the skip reason, keeps the user on the interactive shell, and promotes W2 as
the active workspace.

Fail: startup restoration routes the user into Settings, does not show the W1
restore message, or leaves a workspace other than W2 active after the restore.
```
