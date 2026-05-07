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
            appWrapper: (child) => ColorFiltered(
              colorFilter: scenario.filter,
              child: child,
            ),
          );
          await robot.openSettings();

          expect(
            robot.selectedConnectedControl,
            findsOneWidget,
            reason:
                'The selected Settings provider control should still render the visible "Connected" label with the ${scenario.name} filter applied.',
          );
          await expectLater(
            robot.selectedConnectedControl,
            matchesGoldenFile(
              'goldens/connected_control_${scenario.name}.png',
            ),
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
