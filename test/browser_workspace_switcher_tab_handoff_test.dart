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

  test('Tab from the last post-row control wraps back to the trigger', () {
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
      0,
    );
  });

  test(
    'Tab from the DOM-last post-row control wraps to the trigger when the footer is earlier in DOM order',
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
              visualTop: 216,
              visualLeft: 0,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
              visualTop: 120,
              visualLeft: 0,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
              visualTop: 168,
              visualLeft: 0,
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
        0,
      );
    },
  );

  test(
    'Tab from the selected row uses visual order when post-row controls are earlier in DOM order',
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
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
              visualTop: 120,
              visualLeft: 0,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
              visualTop: 120,
              visualLeft: 112,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
              visualTop: 216,
              visualLeft: 0,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: true,
              isSelectedWorkspaceRow: true,
              isWorkspaceSwitcherTrigger: false,
              visualTop: 0,
              visualLeft: 0,
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
    },
  );

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
    'Tab from the open trigger wraps to the selected row inside the panel',
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

  test(
    'Shift+Tab from the selected workspace row uses visual order for the last in-panel control when the footer is earlier in DOM order',
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
              visualTop: 216,
              visualLeft: 0,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
              visualTop: 120,
              visualLeft: 0,
            ),
            BrowserWorkspaceSwitcherTabStopSnapshot(
              isFocusable: true,
              isWithinWorkspaceSwitcher: true,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
              visualTop: 168,
              visualLeft: 0,
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
        2,
      );
    },
  );

  test(
    'Shift+Tab from the trigger wraps to the last in-panel control',
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
              isWithinWorkspaceSwitcher: false,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
          ],
          currentIndex: 0,
          backwards: true,
        ),
        3,
      );
    },
  );

  test(
    'Shift+Tab from the trigger wraps to the selected row when no post-row controls exist',
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
              isWithinWorkspaceSwitcher: false,
              isWithinWorkspaceRow: false,
              isSelectedWorkspaceRow: false,
              isWorkspaceSwitcherTrigger: false,
            ),
          ],
          currentIndex: 0,
          backwards: true,
        ),
        1,
      );
    },
  );

  test(
    'Tab from the last post-row control wraps to selected row when no trigger exists',
    () {
      expect(
        browserWorkspaceSwitcherTabHandoffIndex(
          focusStops: const [
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
          currentIndex: 1,
          backwards: false,
        ),
        0,
      );
    },
  );
}
