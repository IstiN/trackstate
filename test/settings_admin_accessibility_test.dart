import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../testing/components/screens/settings_screen_robot.dart';
import '../testing/core/utils/color_contrast.dart';

void main() {
  testWidgets(
    'settings admin flow keeps primary controls labeled, ordered, and readable',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);

      try {
        await robot.pumpApp(repository: const DemoTrackStateRepository());
        await robot.openSettings();

        robot.expectVisibleSettingsContent();

        final semanticsLabels = robot.visibleSemanticsLabelsSnapshot();
        for (final label in const [
          'Settings',
          'Project settings administration',
          'Repository access',
          'Connect GitHub',
          'Local Git',
          'Dark theme',
        ]) {
          expect(
            _containsSemanticsFragment(semanticsLabels, label),
            isTrue,
            reason: 'Expected settings semantics to include "$label".',
          );
        }

        for (final tab in const [
          'Statuses',
          'Issue Types',
          'Workflows',
          'Fields',
        ]) {
          expect(robot.tabByLabel(tab), findsOneWidget);
        }

        await robot.clearFocus();
        expect(
          await robot.collectFocusOrder(
            candidates: {
              'Search issues': robot.searchIssuesField,
              'Dark theme': robot.darkThemeControl,
            },
          ),
          containsAllInOrder([
            'Search issues',
            'Dark theme',
          ]),
        );

        final placeholderContrast = contrastRatio(
          robot.renderedTextColorWithin(
            robot.searchIssuesField,
            SettingsScreenRobot.jqlPlaceholderText,
          ),
          robot.colors().surface,
        );
        expect(placeholderContrast, greaterThanOrEqualTo(3.0));
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}

bool _containsSemanticsFragment(List<String> observed, String fragment) {
  return observed.any((label) => label.contains(fragment));
}
