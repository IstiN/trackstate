# TS-713

Verifies that the production local Git workspace sync flow reports a committed
`HEAD` movement separately from a later unstaged worktree edit in the same
repository.

The automation:
1. creates a disposable local Git fixture with a seeded `DEMO/DEMO-1/main.md`
   issue file
2. commits a change to move `HEAD`
3. triggers a workspace sync check and verifies the published result reports
   only `local head change`
4. edits the same file without staging it
5. triggers another sync check and verifies the published result reports only
   `local worktree change`

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-713/test_ts_713.dart --reporter expanded
```

## Required environment / config

No external environment variables are required. The test creates a temporary
local Git repository, seeds TrackState fixture content into it, and exercises
the production workspace sync code through a provider-backed testing adapter.

## Expected result

```text
Pass: the first sync result reports `local head change`, the second reports
`local worktree change`, and both results map `DEMO/DEMO-1/main.md` into the
`issueSummaries` and `issueDetails` domains.

Fail: either sync result reports the wrong reason or signal, misses the changed
issue path, or fails to include the expected issue summary/detail domains.
```
