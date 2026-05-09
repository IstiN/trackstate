import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/screens/settings_screen_robot.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-114 connected status container background uses the centralized success token',
    (tester) async {
      final robot = SettingsScreenRobot(tester);
      final failures = <String>[];

      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await robot.pumpApp(
        repository: const DemoTrackStateRepository(),
        sharedPreferences: const {
          'trackstate.githubToken.trackstate.trackstate': 'stored-token',
        },
      );
      await robot.openSettings();

      if (robot.projectSettingsHeading.evaluate().length != 1) {
        failures.add(
          'Step 1 failed: expected the Settings screen to show the Project Settings heading, '
          'but found ${robot.projectSettingsHeading.evaluate().length} matches.',
        );
      }

      final connectedButtonCount = robot.selectedConnectedControl.evaluate().length;
      if (connectedButtonCount != 1) {
        failures.add(
          'Step 2 failed: expected exactly one visible Connected status control, found $connectedButtonCount.',
        );
      }

      final visibleConnectedLabel = find.descendant(
        of: robot.selectedConnectedControl,
        matching: find.text('Connected'),
      );
      if (visibleConnectedLabel.evaluate().length != 1) {
        failures.add(
          'Step 2 failed: expected the visible Connected label to appear inside the repository-access control, '
          'but found ${visibleConnectedLabel.evaluate().length} matches.',
        );
      }

      if (connectedButtonCount == 1 &&
          visibleConnectedLabel.evaluate().isNotEmpty) {
        final renderedBackground = robot.renderedButtonBackground(
          robot.selectedConnectedControl,
        );
        final successToken = robot.colors().success;
        final renderedHex = _rgbHex(renderedBackground);
        final tokenHex = _rgbHex(successToken);

        if (renderedHex != tokenHex) {
          failures.add(
            'Step 4 failed: Connected background rendered as $renderedHex instead of the centralized '
            'success token $tokenHex.',
          );
        }

        if (renderedHex == '#CD5B3B') {
          failures.add(
            'Step 4 failed: Connected background still uses the legacy hardcoded hex #CD5B3B.',
          );
        }
      }

      if (failures.isNotEmpty) {
        fail(failures.join('\n'));
      }
    },
  );
}

String _rgbHex(Color color) {
  final rgb = color.toARGB32() & 0x00FFFFFF;
  return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
}
