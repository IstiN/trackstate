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
            BrowserWorkspaceSwitcherFocusAncestorSnapshot(textContent: 'Board'),
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

  test(
    'browser row matcher recognizes descendants of the saved-workspace semantics row',
    () {
      expect(
        browserFocusWithinWorkspaceSwitcherRow(
          ancestors: const [
            BrowserWorkspaceSwitcherFocusAncestorSnapshot(
              textContent: 'Hosted alt workspace',
            ),
            BrowserWorkspaceSwitcherFocusAncestorSnapshot(
              semanticsIdentifier:
                  'trackstate-workspace-switcher-row-hosted:alt/repo@main',
              textContent:
                  'Hosted alt workspace Hosted Active alt/repo Branch: main',
            ),
            BrowserWorkspaceSwitcherFocusAncestorSnapshot(
              semanticsIdentifier: browserWorkspaceSwitcherSemanticsIdentifier,
              textContent: 'Workspace switcher',
            ),
          ],
        ),
        isTrue,
      );
    },
  );

  test(
    'browser row matcher ignores switcher text fields outside the saved-workspace rows',
    () {
      expect(
        browserFocusWithinWorkspaceSwitcherRow(
          ancestors: const [
            BrowserWorkspaceSwitcherFocusAncestorSnapshot(textContent: 'main'),
            BrowserWorkspaceSwitcherFocusAncestorSnapshot(
              semanticsIdentifier: browserWorkspaceSwitcherSemanticsIdentifier,
              textContent:
                  'Workspace switcher Saved workspaces Repository Branch Save and switch',
            ),
          ],
        ),
        isFalse,
      );
    },
  );

  test(
    'browser key filter treats ArrowDown inside the switcher as a prevent-default key',
    () {
      expect(
        browserWorkspaceSwitcherShouldPreventDefaultKey(
          key: 'ArrowDown',
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

  test('browser key filter keeps ArrowDown outside the switcher untouched', () {
    expect(
      browserWorkspaceSwitcherShouldPreventDefaultKey(
        key: 'ArrowDown',
        ancestors: const [
          BrowserWorkspaceSwitcherFocusAncestorSnapshot(textContent: 'Board'),
          BrowserWorkspaceSwitcherFocusAncestorSnapshot(
            textContent:
                'TrackState.AI Dashboard Board JQL Search Hierarchy Settings Saved workspaces Repository Branch Save and switch',
          ),
        ],
      ),
      isFalse,
    );
  });
}
