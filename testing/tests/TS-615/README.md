# TS-615

Exercises the hosted desktop header when repository access is shown as
`Attachments limited`.

The automation connects a real hosted GitHub session, verifies the desktop
workspace-switcher repository access control is present, checks that the
rendered `Attachments limited` state is visibly surfaced on the trigger,
verifies the documented 32px header-control parity against the visible
`Search issues` input and `Create issue` button, and checks the shared 8px
action-cluster spacing token around the control.

## Run this test

```bash
python testing/tests/TS-615/test_ts_615.py
```
