import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/components/screens/settings_screen_robot.dart';
import '../testing/tests/TS-445/support/ts445_settings_recovery_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'Settings recovery callout Connect GitHub navigates to inline repository access, no dialog',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);

      try {
        final repository = await tester.runAsync(
          Ts445SettingsRecoveryRepository.create,
        );
        if (repository == null) {
          throw StateError('Repository fixture was not created.');
        }

        await robot.pumpApp(repository: repository);
        await robot.openSettings();

        expect(robot.startupRecoveryCallout, findsOneWidget);
        expect(
          robot.startupRecoveryActionButton('Retry'),
          findsOneWidget,
        );
        final connectAction = robot.startupRecoveryActionButton('Connect GitHub');
        expect(connectAction, findsOneWidget);

        await tester.tap(connectAction, warnIfMissed: false);
        await tester.pumpAndSettle();

        expect(robot.projectSettingsHeading, findsOneWidget);
        expect(robot.repositoryAccessSection, findsOneWidget);
        expect(find.byType(Dialog), findsNothing);
        expect(
          find.widgetWithText(TextFormField, 'Fine-grained token'),
          findsOneWidget,
          reason:
              'The inline hosted provider configuration should be exposed.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
