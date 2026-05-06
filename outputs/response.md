## Issues/Notes

- `instruction.md` was not present at the repository root, so implementation followed the ticket inputs in `input/TS-7/`.
- No functional gaps are left in the requested scope. Hosted GitHub and local Git runtimes now share the same repository-facing contract.
- Added `.gitignore` entries for `input/` and `cacheBasicJiraClient/` so ticket artifacts and local cache data are not staged by post-processing.

## Approach

- Split repository access behind explicit provider interfaces for tree listing, text file reads/writes, session/authentication, branch/commit operations, permission checks, and attachment/LFS checks.
- Moved the existing GitHub API behavior into `GitHubTrackStateProvider` and kept `SetupTrackStateRepository` as the hosted adapter-backed entry point for compatibility.
- Added `LocalGitTrackStateProvider` and `LocalTrackStateRepository` to read tracker data from a local repository with `git` commands and persist status updates as real commits on the current branch.
- Added explicit runtime selection via `TrackStateRuntime` and a conditional repository factory so web builds stay on the hosted adapter while IO runtimes can opt into `local-git`.
- Kept product logic stable by retaining the existing repository API surface used by the view model and UI, while making the load error messaging runtime-agnostic.

## Files Modified

- `.gitignore` — ignore ticket input artifacts and local Jira cache output.
- `lib/domain/models/trackstate_models.dart` — introduced generic repository connection/user models while keeping GitHub-specific compatibility types.
- `lib/data/providers/trackstate_provider.dart` — new provider capability interfaces and shared request/response models.
- `lib/data/providers/github/github_trackstate_provider.dart` — hosted GitHub implementation for repository reads, writes, permissions, branch resolution, and attachments.
- `lib/data/providers/local/local_git_trackstate_provider.dart` — local Git implementation backed by CLI commands, including commit-based writes and LFS attribute checks.
- `lib/data/repositories/trackstate_repository.dart` — refactored repository logic to operate on provider abstractions instead of hard-coded GitHub API calls.
- `lib/data/repositories/local_trackstate_repository.dart` — local adapter-backed repository entry point.
- `lib/data/repositories/trackstate_runtime.dart` — explicit runtime enum and environment parsing.
- `lib/data/repositories/trackstate_repository_factory.dart` — public repository factory.
- `lib/data/repositories/trackstate_repository_factory_io.dart` — IO runtime factory implementation for hosted vs local Git selection.
- `lib/data/repositories/trackstate_repository_factory_stub.dart` — web-safe factory implementation that rejects the local runtime.
- `lib/ui/features/tracker/view_models/tracker_view_model.dart` — updated to use generic repository users and runtime-neutral load error text.
- `lib/ui/features/tracker/views/trackstate_app.dart` — switched default repository creation to the explicit runtime factory.
- `test/trackstate_repository_test.dart` — extended hosted repository coverage to include provider-backed status writes.
- `test/local_trackstate_repository_test.dart` — added local Git repository loading, commit persistence, and LFS tracking tests.
- `test/trackstate_runtime_test.dart` — added runtime parsing and factory selection coverage.

## Test Coverage

- Added unit coverage for the hosted GitHub adapter path, including authenticated write-through status updates.
- Added unit coverage for the local Git adapter path, including repository snapshot loading, status changes committed with `git commit`, and `.gitattributes`/LFS detection.
- Added unit coverage for explicit runtime parsing and repository factory selection.
- Verification run:
  - `/tmp/flutter/bin/flutter analyze`
  - `/tmp/flutter/bin/flutter test`
