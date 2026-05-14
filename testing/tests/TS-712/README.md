# TS-712

Validates the production workspace-sync coordinator behavior for the
30-second minimum interval and duplicate suppression described in the ticket.

The automation:
1. starts a manual workspace-sync check
2. triggers overlapping app-resume events while the first check is still in
   flight
3. completes the first check and verifies no duplicate follow-up starts within
   the enforced 30-second floor
4. triggers another app-resume event 10 seconds after completion and verifies it
   is still suppressed
5. triggers a final app-resume event 35 seconds after completion and verifies it
   starts immediately

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-712/test_ts_712.dart --reporter expanded
```

## Environment

- Flutter test runtime
- Production `WorkspaceSyncService`
- Layered cadence probe abstraction backed by a fixed UTC clock

## Expected result

Only one sync check should run before the 30-second floor expires, even when
app-resume events overlap or occur 10 seconds after completion. A new check
should start immediately once 35 seconds have elapsed since the prior check
completed.
