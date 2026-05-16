# TS-772

Validates that a comments-only hosted background sync for Issue-C refreshes the
Comments surface without dispatching a `detail` hydration for the selected
issue.

The test reuses the proven TS-734 mutable hosted repository fixture so the
production workspace-sync listener, refresh dispatcher, and visible issue detail
UI all participate in the scenario.

## Run this test

```bash
flutter test testing/tests/TS-772/test_ts_772.dart --reporter expanded
```

## Expected result

```text
Pass: a comments-only sync triggers an Issue-C comments hydration, does not
dispatch any Issue-C detail or other non-comments hydrations, and updates the
visible comment text in place.

Fail: the comments-only sync skips the expected comments refresh, dispatches an
Issue-C detail/non-comments hydration, or does not update the user-visible
comment content.
```
