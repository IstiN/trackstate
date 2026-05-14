# Implementation approach and key decisions

Implemented a workspace-scoped background sync pipeline that sits behind repository/provider interfaces so local Git and hosted GitHub runtimes can publish the same domain-level sync signals without coupling product logic to provider-specific APIs.

The new `WorkspaceSyncService` runs on the configured cadence, forces checks on workspace start/switch and app resume, suppresses overlapping runs, coalesces follow-up requests, applies hosted retry backoff, and maps provider sync snapshots into the canonical refresh domains agreed in the ticket (`projectMeta`, `issueSummaries`, `issueDetails`, `comments`, `attachments`, `repositoryIndex`).

`TrackerViewModel` now owns the sync lifecycle, preserves pending refresh state while edits or saves are active, applies deferred refreshes when editing ends, and exposes structured sync status for the UI. The tracker UI now surfaces that state through an actionable top-level sync indicator, a dedicated Workspace Sync settings card, and an in-editor pending-updates notice.

Resolved the `origin/main` merge failure by folding in the new hosted-workspace catalog interfaces alongside the TS-636 sync contracts instead of letting either side replace the other. The shared repository/provider surfaces now carry both background sync support and hosted repository listing support, and the upstream onboarding test provider was updated to satisfy the newer sync-check contract.

# Files changed and why

- `lib/data/services/workspace_sync_service.dart` — new background sync coordinator with cadence, overlap control, domain mapping, and hosted backoff.
- `lib/data/providers/trackstate_provider.dart` — added provider sync contracts and state/check result types.
- `lib/data/repositories/trackstate_repository.dart` — exposed repository-level sync checks for provider-backed repositories and preserved upstream hosted-workspace catalog support during the merge.
- `lib/data/providers/local/local_git_trackstate_provider.dart` — added local HEAD/worktree detection and changed-path reporting.
- `lib/data/providers/github/github_trackstate_provider.dart` — added hosted branch/session detection and compare-based changed-path reporting.
- `lib/domain/models/trackstate_models.dart` — added sync domains, triggers, health, result, and status models.
- `lib/ui/features/tracker/view_models/tracker_view_model.dart` — wired sync lifecycle, deferred refresh handling, retry/resume entry points, and disposal-safe status updates.
- `lib/ui/features/tracker/views/trackstate_app.dart` — added app-resume hook, sync status UI, settings diagnostics, and pending-refresh messaging in edit flows.
- `lib/l10n/app_en.arb` plus generated localization files — added sync-related strings.
- `test/workspace_sync_service_test.dart`, `test/tracker_view_model_sync_test.dart`, `test/workspace_sync_navigation_test.dart` — added unit/widget coverage for sync service behavior, deferred refresh handling, and sync navigation.
- `test/workspace_onboarding_test.dart` — updated the hosted onboarding test provider with a `checkSync` implementation so the merged branch satisfies the shared provider contract.
- Existing repository/provider/widget tests and fake providers — updated for the new `checkSync` contract and the adjusted hosted create-flow expectations.
- `test/goldens/settings_admin_desktop.png`, `test/goldens/mobile_board.png` — refreshed golden baselines after the sync UI changes.

# How to verify / test results

- Run `flutter analyze`
- Run `flutter test`

Result: analyzer clean and `301` tests passing.
