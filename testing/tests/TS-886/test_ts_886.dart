import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/screens/settings_screen_robot.dart';

const _approvedDesktopGoldenPath =
    '../../../test/goldens/settings_admin_desktop.png';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-886 Admin settings desktop surface matches the approved golden baseline',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);

      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          const RepaintBoundary(
            child: TrackStateApp(repository: DemoTrackStateRepository()),
          ),
        );
        await tester.pumpAndSettle();
        await tester.tap(find.text('Settings').first, warnIfMissed: false);
        await tester.pumpAndSettle();

        expect(
          robot.projectSettingsHeading,
          findsOneWidget,
          reason:
              'Step 1 failed: navigating to Settings did not show the visible '
              '"Project Settings" heading. Visible texts: '
              '${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          robot.projectSettingsAdmin,
          findsOneWidget,
          reason:
              'Step 1 failed: navigating to Settings did not show the visible '
              '"Project settings administration" heading. Visible texts: '
              '${_formatSnapshot(robot.visibleTexts())}.',
        );

        for (final tabLabel in const [
          'Statuses',
          'Workflows',
          'Issue Types',
          'Fields',
        ]) {
          expect(
            robot.tabByLabel(tabLabel),
            findsOneWidget,
            reason:
                'Step 2 failed: the visible "$tabLabel" admin tab was not present '
                'after opening Settings. Visible texts: '
                '${_formatSnapshot(robot.visibleTexts())}.',
          );
        }

        expect(
          robot.saveSettingsButton,
          findsOneWidget,
          reason:
              'Human-style verification failed: the visible admin surface did not '
              'show the primary "Save settings" action. Visible texts: '
              '${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          robot.resetSettingsButton,
          findsOneWidget,
          reason:
              'Human-style verification failed: the visible admin surface did not '
              'show the "Reset" action. Visible texts: '
              '${_formatSnapshot(robot.visibleTexts())}.',
        );

        expect(
          robot.viewportSize,
          const Size(1440, 960),
          reason:
              'Step 3 failed: the admin surface did not render at the approved '
              'desktop golden viewport size. Observed viewport: '
              '${robot.viewportSize}.',
        );

        await expectLater(
          find.byType(TrackStateApp),
          matchesGoldenFile(_approvedDesktopGoldenPath),
          reason:
              'Expected Result failed: the rendered Settings admin surface no '
              'longer matches the approved desktop golden baseline at '
              '$_approvedDesktopGoldenPath.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
