import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_tab_handoff.dart';

void main() {
  test(
    'Tab from the selected row hands focus to the first post-row control',
    () {
      expect(
        browserWorkspaceSwitcherTabHandoffIndex(
          focusStops: const [
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: false,
              isWithinWorkspaceSwitcher: false,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: true,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: true,
              isSelectedWorkspaceRow: true,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: true,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: false,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
          ],
          currentIndex: 2,
          backwards: false,
        ),
        4,
      );
    },
  );

  test(
    'Shift+Tab from the first post-row control returns to the selected row',
    () {
      expect(
        browserWorkspaceSwitcherTabHandoffIndex(
          focusStops: const [
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: true,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: true,
              isSelectedWorkspaceRow: true,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: true,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
          ],
          currentIndex: 3,
          backwards: true,
        ),
        1,
      );
    },
  );

  test('Tab from the last post-row control wraps back to the selected row', () {
    expect(
      browserWorkspaceSwitcherTabHandoffIndex(
        focusStops: const [
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceSwitcher: true,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
            isWorkspaceSwitcherTrigger: true,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceSwitcher: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: true,
            isWorkspaceSwitcherTrigger: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceSwitcher: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: false,
            isWorkspaceSwitcherTrigger: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceSwitcher: true,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
            isWorkspaceSwitcherTrigger: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceSwitcher: true,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
            isWorkspaceSwitcherTrigger: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceSwitcher: false,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
            isWorkspaceSwitcherTrigger: false,
          ),
        ],
        currentIndex: 4,
        backwards: false,
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
            isWithinWorkspaceSwitcher: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: false,
            isWorkspaceSwitcherTrigger: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceSwitcher: true,
            isWithinWorkspaceRow: true,
            isSelectedWorkspaceRow: true,
            isWorkspaceSwitcherTrigger: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceSwitcher: false,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
            isWorkspaceSwitcherTrigger: false,
          ),
          BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceSwitcher: false,
            isWithinWorkspaceRow: false,
            isSelectedWorkspaceRow: false,
            isWorkspaceSwitcherTrigger: false,
          ),
        ],
        currentIndex: 3,
        backwards: false,
      ),
      isNull,
    );
  });

  test(
    'Tab from the open trigger hands focus to the selected workspace row',
    () {
      expect(
        browserWorkspaceSwitcherTabHandoffIndex(
          focusStops: const [
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: true,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: true,
              isSelectedWorkspaceRow: true,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: false,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
          ],
          currentIndex: 0,
          backwards: false,
        ),
        1,
      );
    },
  );

  test(
    'Shift+Tab from the selected workspace row wraps to the last in-panel control',
    () {
      expect(
        browserWorkspaceSwitcherTabHandoffIndex(
          focusStops: const [
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: true,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: true,
              isSelectedWorkspaceRow: true,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: false,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
          ],
          currentIndex: 1,
          backwards: true,
        ),
        4,
      );
    },
  );
}
