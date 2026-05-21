## Root Cause Analysis
**Bug**: The desktop workspace switcher keeps keyboard focus inside its own panel after opening, so pressing `Tab` does not blur the component and the panel cannot dismiss through the required blur flow.

**Root cause**: `_openWorkspaceSwitcher` in `lib/ui/features/tracker/views/trackstate_app.dart` immediately requests focus inside the opened panel instead of keeping focus on the workspace-switcher trigger. Once focus starts inside the sheet, a browser `Tab` advances to the switcher’s internal controls such as the `Repository` field, so focus never leaves the component and blur dismissal cannot happen.

**Impact**: In desktop browsers, the workspace switcher does not satisfy the linked TS-821 keyboard behavior: one `Tab` press after opening does not move focus to an external visible control, and the panel cannot close from blur in that scenario.

**Fix approach**: Keep focus on the desktop workspace-switcher trigger when the sheet opens, while preserving arrow-key selection changes after the switcher is visible. This restores the intended first-`Tab` path to an external control so the browser blur handler can dismiss the panel.
