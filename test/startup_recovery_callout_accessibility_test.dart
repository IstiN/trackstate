import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/components/screens/settings_screen_robot.dart';
import '../testing/core/utils/color_contrast.dart';
import '../testing/tests/TS-445/support/ts445_settings_recovery_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'settings startup recovery callout uses retry label and AA-safe action states',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      TestGesture? mouseGesture;

      try {
        final repository = await tester.runAsync(
          Ts445SettingsRecoveryRepository.create,
        );
        if (repository == null) {
          throw StateError(
            'Startup recovery repository fixture was not created.',
          );
        }

        await robot.pumpApp(repository: repository);
        await robot.openSettings();

        const expectedTitle = 'GitHub startup limit reached';
        const expectedMessage =
            'Hosted startup loaded the minimum app-shell data, but GitHub rate-limited a deferred repository read. Retry later or connect GitHub for a higher limit to resume full hosted reads.';
        final callout = robot.startupRecoveryCallout;
        final retryAction = robot.startupRecoveryActionButton('Retry');
        final connectAction = robot.startupRecoveryActionButton(
          'Connect GitHub',
        );

        expect(callout, findsOneWidget);
        expect(retryAction, findsOneWidget);
        expect(connectAction, findsOneWidget);

        final calloutBackground = robot.decoratedContainerBackgroundColor(
          callout,
        )!;
        expect(
          contrastRatio(
            robot.renderedTextColorWithin(callout, expectedTitle),
            calloutBackground,
          ),
          greaterThanOrEqualTo(4.5),
        );
        expect(
          contrastRatio(
            robot.renderedTextColorWithin(callout, expectedMessage),
            calloutBackground,
          ),
          greaterThanOrEqualTo(4.5),
        );

        mouseGesture = await robot.hover(retryAction);
        expect(
          _buttonContrast(
            robot: robot,
            action: retryAction,
            label: 'Retry',
            states: const <WidgetState>{WidgetState.hovered},
            calloutBackground: calloutBackground,
          ),
          greaterThanOrEqualTo(4.5),
        );
        await mouseGesture.removePointer();
        mouseGesture = null;
        await tester.pump();

        expect(
          _buttonContrast(
            robot: robot,
            action: retryAction,
            label: 'Retry',
            states: const <WidgetState>{WidgetState.focused},
            calloutBackground: calloutBackground,
          ),
          greaterThanOrEqualTo(4.5),
        );
        expect(
          _buttonContrast(
            robot: robot,
            action: connectAction,
            label: 'Connect GitHub',
            states: const <WidgetState>{WidgetState.focused},
            calloutBackground: calloutBackground,
          ),
          greaterThanOrEqualTo(4.5),
        );
      } finally {
        await mouseGesture?.removePointer();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}

double _buttonContrast({
  required SettingsScreenRobot robot,
  required Finder action,
  required String label,
  required Set<WidgetState> states,
  required Color calloutBackground,
}) {
  return contrastRatio(
    robot.resolvedButtonForeground(action, states, text: label),
    Color.alphaBlend(
      robot.resolvedButtonBackground(action, states),
      calloutBackground,
    ),
  );
}
