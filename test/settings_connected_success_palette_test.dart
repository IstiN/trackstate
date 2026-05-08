import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../testing/components/screens/settings_screen_robot.dart';
import '../testing/core/utils/color_contrast.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'settings connected control uses the centralized success palette accessibly',
    (tester) async {
      final robot = SettingsScreenRobot(tester);

      await robot.pumpApp(
        repository: const DemoTrackStateRepository(),
        sharedPreferences: const {
          'trackstate.githubToken.trackstate.trackstate': 'stored-token',
        },
      );
      await robot.openSettings();

      expect(robot.settingsConnectedControl, findsOneWidget);

      final textColor = robot.renderedTextColorWithin(
        robot.settingsConnectedControl,
        'Connected',
      );
      final background = robot.renderedButtonBackground(
        robot.settingsConnectedControl,
      );

      expect(textColor, robot.colors().success);
      expect(contrastRatio(textColor, background), greaterThanOrEqualTo(4.5));
    },
  );
}
