# TS-598 test automation

Verifies that the production `IssueMutationService.updateFields` path returns a
typed machine-readable `notFound` failure when a caller targets an issue key
that does not exist in the repository index.

The automation:
1. seeds a local Git repository with a single surviving `TRACK-122` issue and no
   `MISSING-404` issue
2. captures the repository-visible preconditions before the mutation attempt
3. calls `IssueMutationService.updateFields` for `MISSING-404`
4. verifies the typed mutation envelope reports `isSuccess == false`,
   `operation == "update-fields"`, the missing issue key, and
   `IssueMutationErrorCategory.notFound`
5. confirms the failed mutation leaves the repository index, issue searches, git
   revision, and worktree unchanged for integrated clients

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-598/test_ts_598.dart --reporter expanded
```

## Required environment / config

No external credentials are required. The test creates its own temporary local
Git repository fixture and exercises the production mutation service against
that seeded repository.

## Expected pass / fail behavior

- **Pass:** `updateFields` returns a failed typed result for `MISSING-404` with
  `IssueMutationErrorCategory.notFound`, the contextual not-found message, and
  no repository-visible side effects.
- **Fail:** the mutation reports the wrong category or message, returns success,
  creates or changes repository data, creates a commit, dirties the worktree, or
  makes the missing issue appear in search results.
