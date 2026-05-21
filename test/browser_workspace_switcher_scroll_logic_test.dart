import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_scroll_logic.dart';

void main() {
  test(
    'capture tracks the background semantics scroller before window in mixed-scroll layouts',
    () {
      final targets = captureBrowserWorkspaceSwitcherScrollTargets(
        windowCandidate: const BrowserWorkspaceSwitcherScrollCandidate(
          key: 'window',
          scrollY: 24,
          maxScrollY: 800,
          width: 1440,
          height: 960,
          explicitlyScrollable: true,
          isWindow: true,
        ),
        elementCandidates: const [
          BrowserWorkspaceSwitcherScrollCandidate(
            key: 'switcher',
            scrollY: 0,
            maxScrollY: 320,
            width: 420,
            height: 480,
            explicitlyScrollable: true,
            textSummary: 'Workspace switcher Saved workspaces',
          ),
          BrowserWorkspaceSwitcherScrollCandidate(
            key: 'semantics-scroller',
            scrollY: 336,
            maxScrollY: 1500,
            width: 1320,
            height: 900,
            explicitlyScrollable: true,
            textSummary: 'TrackState Settings Saved workspaces',
          ),
        ],
      );

      expect(
        [
          for (final target in targets)
            (target.key, target.scrollY, target.isWindow),
        ],
        [('semantics-scroller', 336.0, false), ('window', 24.0, true)],
      );
    },
  );

  test(
    'restore targets only the scroll owner that drifted from the captured position',
    () {
      final targetsToRestore =
          browserWorkspaceSwitcherScrollTargetsNeedingRestore(
            capturedTargets: const [
              BrowserWorkspaceSwitcherTrackedScrollTarget(
                key: 'semantics-scroller',
                scrollY: 336,
                isWindow: false,
              ),
              BrowserWorkspaceSwitcherTrackedScrollTarget(
                key: 'window',
                scrollY: 24,
                isWindow: true,
              ),
            ],
            currentWindowScrollY: 24,
            currentElementScrollYByKey: const {'semantics-scroller': 0},
          );

      expect(
        [for (final target in targetsToRestore) target.key],
        ['semantics-scroller'],
      );
    },
  );

  test(
    'capture falls back to window when no background element is scrollable',
    () {
      final targets = captureBrowserWorkspaceSwitcherScrollTargets(
        windowCandidate: const BrowserWorkspaceSwitcherScrollCandidate(
          key: 'window',
          scrollY: 180,
          maxScrollY: 900,
          width: 1440,
          height: 960,
          explicitlyScrollable: true,
          isWindow: true,
        ),
        elementCandidates: const [
          BrowserWorkspaceSwitcherScrollCandidate(
            key: 'tiny-panel',
            scrollY: 0,
            maxScrollY: 10,
            width: 240,
            height: 180,
            explicitlyScrollable: true,
          ),
        ],
      );

      expect(
        [
          for (final target in targets)
            (target.key, target.scrollY, target.isWindow),
        ],
        [('window', 180.0, true)],
      );
    },
  );
}
