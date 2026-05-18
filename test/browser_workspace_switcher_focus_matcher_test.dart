import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_matcher.dart';

void main() {
  test(
    'browser focus matcher keeps the switcher open for descendants inside the panel',
    () {
      expect(
        browserFocusWithinWorkspaceSwitcher(
          ancestorTexts: const [
            'Save and switch',
            'Workspace switcher alpha/repo Hosted Saved workspaces Repository Branch Save and switch',
          ],
          savedWorkspacesLabel: 'Saved workspaces',
        ),
        isTrue,
      );
    },
  );

  test(
    'browser focus matcher dismisses when focus moves to an external control',
    () {
      expect(
        browserFocusWithinWorkspaceSwitcher(
          ancestorTexts: const [
            'Search issues',
            'TrackState.AI Dashboard Board JQL Search Hierarchy Settings',
          ],
          savedWorkspacesLabel: 'Saved workspaces',
        ),
        isFalse,
      );
    },
  );
}
