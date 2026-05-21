## Bug Fix Summary

### Root Cause
The desktop workspace switcher was moving focus into the opened sheet as soon as it appeared. That made the next `Tab` land on an internal control such as `Repository` instead of leaving the switcher, so the blur-dismiss path could not run.

### Fix
Updated `lib/ui/features/tracker/views/trackstate_app.dart` so opening the desktop workspace switcher keeps focus on the trigger rather than auto-focusing the active workspace row. Arrow-key workspace switching remains intact after the sheet opens, but the first `Tab` can now move to an external control as required for blur dismissal.

I also resolved the later sync conflict against `origin/main` by combining this focus fix with the incoming workspace-switcher scroll-preservation changes from TS-880/TS-881. The merged result keeps the new captured scroll snapshot behavior while preserving TS-884's trigger-owned focus on open.

### Test Coverage
- Reproduction test added: `test/workspace_switcher_trigger_semantics_test.dart` — `desktop workspace switcher keeps focus on the trigger when opened`
- Updated regression expectation: `test/workspace_switcher_test.dart` — `desktop workspace switcher Arrow Down moves focus to the next row and switches once`
- Validation run: `flutter analyze`, `flutter test`, `flutter build web`, and the new regression test in Chrome
- Post-merge validation on the combined branch: `flutter analyze && flutter test` (`410 tests passed`)

### Notes
The provided TS-821 Playwright script targets the already-deployed GitHub Pages app by default, so its hosted run still reflects the old published build until this code is deployed. The local code path is covered by the Chrome regression test added here.
