import 'package:flutter/material.dart';
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
    'connected repository access control keeps WCAG AA contrast while hovered and pressed',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      TestGesture? mouseGesture;
      TestGesture? touchGesture;

      try {
        await robot.pumpApp(
          repository: const DemoTrackStateRepository(),
          sharedPreferences: const {
            'trackstate.githubToken.trackstate.trackstate': 'stored-token',
          },
        );
        await robot.openSettings();

        expect(
          _contrastFor(
            robot: robot,
            states: const <WidgetState>{},
          ),
          greaterThanOrEqualTo(4.5),
        );

        mouseGesture = await robot.hover(robot.settingsConnectedControl);
        expect(
          _contrastFor(
            robot: robot,
            states: const <WidgetState>{WidgetState.hovered},
          ),
          greaterThanOrEqualTo(4.5),
        );
        await mouseGesture.removePointer();
        mouseGesture = null;
        await tester.pump();

        touchGesture = await robot.pressAndHold(robot.settingsConnectedControl);
        await tester.pump(const Duration(milliseconds: 200));
        expect(
          _contrastFor(
            robot: robot,
            states: const <WidgetState>{WidgetState.pressed},
          ),
          greaterThanOrEqualTo(4.5),
        );
      } finally {
        await touchGesture?.up();
        await mouseGesture?.removePointer();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}

double _contrastFor({
  required SettingsScreenRobot robot,
  required Set<WidgetState> states,
}) {
  return contrastRatio(
    robot.resolvedButtonForeground(
      robot.settingsConnectedControl,
      states,
      text: 'Connected',
    ),
    robot.resolvedButtonBackground(robot.settingsConnectedControl, states),
  );
}
