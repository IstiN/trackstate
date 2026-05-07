import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/color_blindness_filters.dart';

void main() {
  testWidgets(
    'TS-50 connected status remains distinguishable when color cues are removed',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);

      try {
        for (final scenario in <({String name, ColorFilter filter})>[
          (name: 'grayscale', filter: ColorBlindnessFilters.grayscale()),
          (name: 'protanopia', filter: ColorBlindnessFilters.protanopia()),
        ]) {
          await robot.pumpApp(
            repository: const DemoTrackStateRepository(),
            sharedPreferences: const {
              'trackstate.githubToken.trackstate.trackstate': 'stored-token',
            },
            appWrapper: (child) =>
                ColorFiltered(colorFilter: scenario.filter, child: child),
          );
          await robot.openSettings();

          expect(
            robot.connectedControl,
            findsOneWidget,
            reason:
                'The Settings provider control should still render the visible "Connected" label with the ${scenario.name} filter applied.',
          );
          expect(
            robot.semanticsLabelOf(robot.connectedControl),
            'Connected',
            reason:
                'The selected provider control should continue exposing the "Connected" status through its accessible label in the ${scenario.name} scenario.',
          );
          expect(
            find.descendant(
              of: robot.connectedControl,
              matching: find.text('Connected'),
            ),
            findsOneWidget,
            reason:
                'The rendered provider control should keep the explicit "Connected" text inside the selected control for ${scenario.name}, so the state does not depend on color alone.',
          );
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
