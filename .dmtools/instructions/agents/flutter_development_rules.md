# TrackState Flutter Development Rules

Injected via `.dmtools/config.js → additionalInstructions`. The shared `agents/` submodule stays project-independent.

## Stack

```mermaid
graph LR
  App["Flutter / Dart\nlib/"] --> CLI["Dart CLI\nbin/trackstate.dart\n→ dart run trackstate"]
  App --> Tests["flutter test\nunit + widget"]
  App --> Config[".dmtools/config.js"]
  Testing["Automation\ntesting/"] -. owned by test agents .-> App
```

## Implementation flow

```mermaid
flowchart TD
  Start([Start ticket]) --> Read[Read lib/ pubspec.yaml lib/main.dart\nexisting state-management]
  Read --> Scope{Touches\npermission/storage\nlayers?}
  Scope -->|Yes| Permission[See Permission & Storage rules below]
  Scope -->|No| Impl[Implement following existing patterns]
  Impl --> Widget{UI changes?}
  Widget -->|Yes| Keys[Add ValueKey + Semantics label\nUse theme tokens, not hardcoded colors\nLocalize all Text strings]
  Widget -->|No| Analyze
  Keys --> Analyze[flutter analyze → 0 issues]
  Permission --> Analyze
  Analyze --> Test[flutter test → all pass]
  Test --> NoTesting{Touched testing/ ?}
  NoTesting -->|Yes| Revert[Revert all changes in testing/ —
dev agent must not own that tree]
  NoTesting -->|No| Output[Write outputs/response.md]
  Revert --> Output
```

## Permission & Storage implementation rules

These patterns caused the most BLOCKING review cycles. **Read before touching provider/repository/permission code.**

### 1 — Wire capabilities end-to-end through the provider

Never hard-code a capability flag to `false` in `_permissionFromRepoJson()` or similar. Every new feature capability (e.g. `supportsReleaseAttachmentWrites`) must be:
- Detected in the provider from actual API data
- Exposed in the permission/session model
- Checked in the repository gate before performing the operation

```mermaid
sequenceDiagram
  participant VM as ViewModel
  participant Repo as Repository
  participant Provider as Provider
  participant API as GitHub API

  VM->>Repo: canUploadAttachment?
  Repo->>Provider: permissionFromRepo()
  Provider->>API: repo metadata
  API-->>Provider: has release write?
  Provider-->>Repo: supportsReleaseAttachmentWrites=true
  Repo-->>VM: allowed ✓
```

### 2 — Storage-aware permission gates

When multiple storage backends exist (local-git, GitHub Releases, etc.), each gate must check the **configured** storage mode, not a generic permission:

```
// ❌ WRONG — generic permission, ignores storage mode
if (!permission.canManageAttachments) throw ...

// ✅ CORRECT — storage-mode-aware gate
if (storageMode == AttachmentStorageMode.githubReleases) {
  if (!permission.supportsReleaseAttachmentWrites) throw ...
} else {
  if (!permission.canManageAttachments) throw ...
}
```

### 3 — Atomic write ordering (upload → metadata)

When implementing two-step writes (binary + JSON manifest):

```mermaid
sequenceDiagram
  participant R as Repository
  participant P as Provider

  R->>P: uploadBinary()
  P-->>R: ok
  R->>P: updateManifest(attachments.json)
  alt manifest write fails
    R->>P: rollbackBinary()
    P-->>R: binary deleted
    R-->>Caller: throw
  else success
    R-->>Caller: updatedAttachment (with POST-write revisionOrOid)
  end
```

**Never** return a stale `revisionOrOid` computed before the write. Always re-read or refresh the revision after `applyFileChanges`.

### 4 — Download via authenticated asset API, not browser_download_url

For private/hosted GitHub repos, `browser_download_url` requires browser redirect and fails for programmatic access. Use:
```
GET /repos/{owner}/{repo}/releases/assets/{asset_id}
```
with `Accept: application/octet-stream` and authenticated token.

### 5 — UI state must respect hostedRepositoryAccessMode

Callout tone/messaging must branch on `hostedRepositoryAccessMode`:
- `writable` → supported/success state
- `readOnly` | `disconnected` → restricted/warning state

Never collapse `readOnly` and `disconnected` into the same "supported" branch.

### 6 — In-memory validation scaffolding must not persist to disk

Synthetic or fallback fields injected for validation (e.g. reserved built-in fields) must be stripped before `saveProjectSettings()` serializes to `config/fields.json`. Keep fallback logic in validation; do not let it reach the persistence layer.

### 7 — Cover all entry points, not just the first one found

When fixing a rendering/display bug (e.g. locale label fallback), check **all** surfaces where the same data is displayed:
- Search results list
- Board column headers
- Issue detail view
- Settings editor

Add a test for each surface you fix.

### 8 — Web (kIsWeb) capability gating for browser-incompatible paths

Any code path that uses `Process.run`, `dart:io` File/Directory, or CORS-incompatible hosts **must** be gated on `!kIsWeb` or have a web-specific fallback:

```mermaid
flowchart TD
  Impl([Implementing feature]) --> Check{Uses Process.run,\ndart:io File,\nor non-CORS host?}
  Check -->|Yes| Web{Has web fallback?}
  Web -->|No| MUST["MUST add:\n1. kIsWeb gate\n2. Web-specific alternative\n   (browser File API, etc.)\n3. Graceful error if impossible"]
  Web -->|Yes| OK([✅ Both paths covered])
  Check -->|No| OK
```

Common web-incompatible patterns:
- `Process.run(...)` → throws `Unsupported operation` on web
- `File(path).readAsString()` → dart:io unavailable on web
- `LocalTrackStateRepository` → uses filesystem, needs `openBrowserLocalRepository` on web
- `uploads.github.com` → no CORS headers, needs `!kIsWeb` gate

```dart
// ❌ WRONG — crashes on web
final result = await Process.run('git', ['status']);

// ✅ CORRECT — web-aware with fallback
if (kIsWeb) {
  return _browserLocalFallback();
} else {
  final result = await Process.run('git', ['status']);
}
```

- Import: `import 'package:flutter/foundation.dart' show kIsWeb;`
- **Never** let a web execution path reach `Process.run` or `dart:io` — it crashes, not just fails silently.
- When adding workspace retry/restore logic, ALWAYS check if the existing `openBrowserLocalRepository` path handles the case.

### 9 — Async startup: always notify listeners after deferred operations

When deferring a probe/restore to avoid blocking startup:

```mermaid
sequenceDiagram
  participant Load as load()
  participant Deferred as deferredRestore()
  participant UI as Listeners/UI
  
  Load->>Deferred: unawaited(restore())
  Load->>UI: notifyListeners() → shell_ready
  Note over Deferred: restore completes later...
  Deferred->>UI: ❌ WRONG if no notifyListeners()
  Deferred->>UI: ✅ MUST notifyListeners() when done
```

**Rules:**
- Every `unawaited()` async operation that changes state MUST call `notifyListeners()` on completion
- Early-return branches in deferred callbacks MUST still notify if the state is meaningful (e.g. `githubAuthorizationCodeReturned`)
- Test both: (a) startup completes without blocking, AND (b) deferred result eventually surfaces

### 10 — Workspace state: test ALL state transitions, not just happy path

When implementing workspace state changes (retry, restore, switch):

```mermaid
flowchart TD
  Change([State change logic]) --> Paths{All paths\ncovered?}
  Paths -->|"Only success path"| BAD["❌ Missing:\n- What if reopen fails on web?\n- What if directory doesn't match?\n- What if token expired?"]
  Paths -->|"Success + all error branches"| GOOD["✅ Each branch either:\n1. Transitions to correct state\n2. Shows error UI\n3. Notifies listeners"]
```

**Rules:**
- Never reuse `previousViewModel.repository` for a "restored" workspace — create fresh state
- If `_prepareWorkspaceSwitch()` can fail on web, add `try/catch` with browser-specific fallback
- Regression test must verify the VISIBLE repository changed, not just workspace metadata



| # | Rule |
|---|------|
| 1 | Read `lib/`, `pubspec.yaml`, `lib/main.dart`, existing patterns before writing code |
| 2 | Add packages via `flutter pub add`, never hand-edit `pubspec.yaml` |
| 3 | `ValueKey` (kebab-case) on every user-facing or automation-targeted widget |
| 4 | `Semantics(label:...)` on every `IconButton`, `GestureDetector`, custom interactive widget |
| 5 | Theme tokens only — no hardcoded `Color(0xFF...)` or pixel sizes |
| 6 | All `Text()` content must go through the localization system |
| 7 | For CLI: validate `--path`, run from repo root, keep JSON response schema stable |
| 8 | **NEVER** create or modify files under `testing/` during development. If production changes break existing regression tests there, mention it in `outputs/response.md` and let the test-automation agent handle updates |
| 9 | `flutter analyze` → 0 issues; `flutter test` → all pass before finishing |
| 10 | Null safety: no `dynamic`, no unjustified `!` |
| 11 | Every code path that uses `Process.run` or `dart:io` MUST have a `kIsWeb` gate or web fallback |
| 12 | Every `unawaited()` deferred operation that changes state MUST call `notifyListeners()` on completion |
| 13 | Workspace state changes must cover ALL branches (success, web failure, directory mismatch, token expired) |

## `testing/` ownership

`testing/` contains regression probes, workflow-observation tests, accessibility
gates, and other automation owned by test-automation agents. It is **not** a
unit-test directory for development TDD.

- Development agents must **not** write, edit, or delete files under `testing/`.
- If your changes break existing `testing/` tests, note the breakage in
  `outputs/response.md` under `issues/notes`.
- Updating `testing/` to match new workflow / architecture contracts is the
  responsibility of `test_case_automation` / `pr_test_automation_*` agents.

## Bug-fix additional rules

- Ticket returned to dev → read prior Jira comments + previous PR diffs before changing anything
- CLI bug → test both happy path and exact error path from ticket
- Check `git log --oneline lib/ | head -20` before fixing to see recent changes to the same files
- **Web platform**: before fixing any workspace/startup bug, check if the failing path uses `Process.run` or native file access → add web fallback via `openBrowserLocalRepository`
- **Startup bugs**: check whether the fix blocks `shell_ready` — users must see the interactive shell quickly even if background probes are still running
- **State bugs**: verify the fix handles the case where the previous workspace was hosted but the target is local (never reuse `previousViewModel.repository`)
- **Scope**: fix ONLY the bug described in the ticket. Do not add unrelated JQL/locale/settings changes — they will be BLOCKING rejected

## Output (`outputs/response.md`)

Must include: issues/notes · approach · files modified · test coverage · `flutter analyze` + `flutter test` result
