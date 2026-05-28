# TS-912

Validates that an unavailable saved local workspace can be restored to active
`Local Git` only after the user-visible Retry or Re-authenticate flow completes
the directory-access grant step.

The automation:
1. seeds one hosted active workspace plus one saved local workspace in the
   `Unavailable` state
2. launches the production tracker in the supported Flutter widget runtime at
   the ticket viewport of 1440x900
3. opens the Workspace switcher, confirms the saved local row is visibly
   unavailable, and taps the visible Retry or Re-authenticate action
4. completes the directory-access grant through the app's
   `workspaceDirectoryPicker` seam without manufacturing the restored end state
5. verifies the same saved workspace becomes active as `Local Git`, the retry
   action disappears, and the directory-access prompt ran exactly once

The earlier live Playwright rework stopped at Chromium's native picker boundary.
That boundary is an automation gap for that surface, not the intended TS-912
result. This ticket now runs in the supported Flutter harness that can complete
the access-grant step.

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-912/test_ts_912.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: the saved unavailable local workspace exposes a working Retry or
Re-authenticate action, the directory-access prompt completes once for the
saved folder, and the workspace becomes the active `Local Git` session.

Fail: the unavailable row is missing, the visible retry-style action cannot be
activated, the directory-access prompt does not complete, or the workspace does
not settle to active `Local Git` after access is granted.
```
