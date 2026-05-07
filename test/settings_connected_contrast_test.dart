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
    'connected repository access control keeps WCAG AA contrast',
    (tester) async {
      final robot = SettingsScreenRobot(tester);

      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await robot.pumpApp(
        repository: const DemoTrackStateRepository(),
        sharedPreferences: const {
          'trackstate.githubToken.trackstate.trackstate': 'stored-token',
        },
      );
      await robot.openSettings();

      final connectedContrast = contrastRatio(
        robot.renderedTextColorWithin(robot.connectedControl, 'Connected'),
        robot.colors().primary,
      );

      expect(connectedContrast, greaterThanOrEqualTo(4.5));
    },
  );
}
