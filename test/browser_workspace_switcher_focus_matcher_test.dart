import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_matcher.dart';

void main() {
  test(
    'browser focus matcher keeps the switcher open for descendants inside the panel',
    () {
      expect(
        browserFocusWithinWorkspaceSwitcher(
          ancestors: const [
            BrowserWorkspaceSwitcherFocusAncestorSnapshot(
              textContent: 'Save and switch',
            ),
            BrowserWorkspaceSwitcherFocusAncestorSnapshot(
              semanticsIdentifier: browserWorkspaceSwitcherSemanticsIdentifier,
              textContent:
                  'Workspace switcher alpha/repo Hosted Saved workspaces Repository Branch Save and switch',
            ),
          ],
        ),
        isTrue,
      );
    },
  );

  test(
    'browser focus matcher dismisses external controls even when a shared ancestor text still contains Saved workspaces',
    () {
      expect(
        browserFocusWithinWorkspaceSwitcher(
          ancestors: const [
            BrowserWorkspaceSwitcherFocusAncestorSnapshot(
              textContent: 'Board',
            ),
            BrowserWorkspaceSwitcherFocusAncestorSnapshot(
              textContent:
                  'TrackState.AI Dashboard Board JQL Search Hierarchy Settings Saved workspaces Repository Branch Save and switch',
            ),
          ],
        ),
        isFalse,
      );
    },
  );
}
