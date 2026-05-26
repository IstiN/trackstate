# TS-715

Validates that revoking the hosted GitHub PAT drives the deployed TrackState app
into the user-visible `Sync unavailable` state, surfaces an authentication error
in the `Workspace sync` settings section, and schedules the next retry about one
minute later.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-715/test_ts_715.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` with access to the hosted TrackState repository
- any live hosted setup variables required by
  `testing.core.config.live_setup_test_config`
- optional `TRACKSTATE_LIVE_APP_URL` override for the deployed app under test

## Expected result

```text
Pass: after the PAT is revoked, the top-bar sync pill changes to `Sync unavailable`,
the visible `Workspace sync` card shows an authentication-flavored failure plus a
`Next retry at ...` message, and the next failed repository-scoped GitHub check
is observed about one minute after the first failed check.

Fail: the hosted app does not surface the expected `Sync unavailable` state, does
not show the authentication/backoff messaging in the `Workspace sync` card, or
does not perform the next failed repository-scoped retry at roughly one minute.
```
