# TS-615

Exercises the hosted desktop header when repository access is shown as
`Attachments limited`.

The current hosted UI surfaces that state through the desktop workspace
switcher. The automation reaches a real hosted GitHub session, verifies the
workspace-switcher repository access control is present, checks that it stays at
the documented 32px header control height and centered against the visible
`Search issues` field and `Create issue` button, checks the shared 8px
action-cluster spacing token around the control, and fails if the limited state
is only present in accessibility metadata instead of being clearly visible on
the trigger.

## Run this test

```bash
python testing/tests/TS-615/test_ts_615.py
```
