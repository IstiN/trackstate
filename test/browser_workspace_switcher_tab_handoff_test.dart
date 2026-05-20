import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_tab_handoff.dart';

void main() {
  test('Tab from the selected row hands focus to the first post-row control', () {
    expect(
      browserWorkspaceSwitcherTabHandoffIndex(
        focusStops: const [
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: false,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: true,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
          ),
        ],
        currentIndex: 2,
        backwards: false,
      ),
      4,
    );
  });

  test('Shift+Tab from the first post-row control returns to the selected row', () {
    expect(
      browserWorkspaceSwitcherTabHandoffIndex(
        focusStops: const [
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: true,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
          ),
        ],
        currentIndex: 3,
        backwards: true,
      ),
      1,
    );
  });

  test('non-boundary tab stops do not trigger a manual handoff', () {
    expect(
      browserWorkspaceSwitcherTabHandoffIndex(
        focusStops: const [
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: true,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
          ),
        ],
        currentIndex: 3,
        backwards: false,
      ),
      isNull,
    );
  });
}
