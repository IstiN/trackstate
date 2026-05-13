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
  NoTesting -->|Yes| Justify[Add justification in outputs/response.md]
  NoTesting -->|No| Output[Write outputs/response.md]
  Justify --> Output
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

### 8 — Web (kIsWeb) capability gating for browser-incompatible upload paths

Some external APIs (e.g. `uploads.github.com`) do not expose browser-safe CORS headers. Any capability that requires a CORS-incompatible host **must** be gated on `!kIsWeb`:

```mermaid
flowchart TD
  Impl([Implementing upload / network feature]) --> Host{Upload target\nCORS-safe for browsers?}
  Host -->|api.github.com etc.| Both[Enable on all platforms]
  Host -->|uploads.github.com\nor other non-CORS hosts| Gate["supportsFeature = canWrite && !kIsWeb"]
  Gate --> UI[UI falls to restricted/unavailable\nstate on web]
  UI --> Msg[Update callout message\nto explain the limitation clearly]
```

- Import: `import 'package:flutter/foundation.dart' show kIsWeb;`
- **Never** advertise a write capability on web that routes through a non-CORS endpoint — the upload appears to work (controls enabled) but silently fails.
- Update the UI callout message to explain the limitation (not just "not supported yet").



| # | Rule |
|---|------|
| 1 | Read `lib/`, `pubspec.yaml`, `lib/main.dart`, existing patterns before writing code |
| 2 | Add packages via `flutter pub add`, never hand-edit `pubspec.yaml` |
| 3 | `ValueKey` (kebab-case) on every user-facing or automation-targeted widget |
| 4 | `Semantics(label:...)` on every `IconButton`, `GestureDetector`, custom interactive widget |
| 5 | Theme tokens only — no hardcoded `Color(0xFF...)` or pixel sizes |
| 6 | All `Text()` content must go through the localization system |
| 7 | For CLI: validate `--path`, run from repo root, keep JSON response schema stable |
| 8 | Do not touch `testing/` unless ticket requires it; justify in `outputs/response.md` |
| 9 | `flutter analyze` → 0 issues; `flutter test` → all pass before finishing |
| 10 | Null safety: no `dynamic`, no unjustified `!` |

## Bug-fix additional rules

- Ticket returned to dev → read prior Jira comments + previous PR diffs before changing anything
- CLI bug → test both happy path and exact error path from ticket
- Check `git log --oneline lib/ | head -20` before fixing to see recent changes to the same files

## Output (`outputs/response.md`)

Must include: issues/notes · approach · files modified · test coverage · `flutter analyze` + `flutter test` result
