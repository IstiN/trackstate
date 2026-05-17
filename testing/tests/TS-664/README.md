# TS-664

Validates that the production workspace-profile persistence service stores the
required serialized fields and derives deterministic branch-specific workspace
IDs for hosted repositories.

The automation:
1. initializes `SharedPreferencesWorkspaceProfileService` with mock device
   storage
2. creates a hosted `owner/repo` workspace profile for the `main` branch
3. inspects the raw `trackstate.workspaceProfiles.state` value saved in
   `SharedPreferences`
4. creates a second hosted `owner/repo` profile for the `develop` branch
5. verifies the persisted workspace IDs remain deterministic and distinct while
   the stored fields stay correct

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-664/test_ts_664.dart --reporter expanded
```

## Environment

- Flutter test runtime
- Mock `SharedPreferences` device storage

## Expected result

The stored state should persist the deterministic workspace identifier,
display name, target type, repository coordinates, default branch, write
branch, and `lastOpenedAt`. Saving `owner/repo` for `main` and `develop`
should produce different deterministic IDs.
