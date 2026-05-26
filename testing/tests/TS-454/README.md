# TS-454

Verifies that a hosted issue mutation refreshes only the affected issue summary
and hydrated artifacts instead of rebuilding the full repository snapshot.

The automation:
1. opens the provider-backed JQL Search view and confirms Issue-A and Issue-B
   are visible
2. hydrates Detail and Comments for both issues so the test starts from the same
   cached state described by the ticket
3. transitions Issue-A from `To Do` to `In Progress`
4. proves repository behavior stayed scoped by asserting `loadSnapshot` did not
   run again, Issue-A received a forced targeted hydrate, Issue-A's comment file
   was reread after the mutation, and Issue-B's comment file was not reread
5. reopens Issue-B and confirms its existing Detail and Comments state remains
   interactive after the Issue-A mutation

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-454/test_ts_454.dart -r expanded
```

## Required configuration

This test uses an in-memory provider-backed TrackState fixture, so no external
credentials or services are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
