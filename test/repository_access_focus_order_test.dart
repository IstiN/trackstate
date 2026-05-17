import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../testing/components/screens/settings_screen_robot.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'repository access tabs from Fine-grained token to Remember on this browser and Connect token',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);

      try {
        await robot.pumpApp(
          repository: const DemoTrackStateRepository(),
        );
        await robot.openSettings();

        await tester.tap(
          find.descendant(
            of: robot.repositoryAccessSection,
            matching: find.bySemanticsLabel(RegExp('Connect GitHub')),
          ),
        );
        await tester.pumpAndSettle();

        final focusCandidates = <String, Finder>{
          'Fine-grained token': robot.labeledTextField('Fine-grained token'),
          'Remember on this browser': robot.checkboxTile(
            'Remember on this browser',
          ),
          'Connect token': find.descendant(
            of: robot.repositoryAccessSection,
            matching: find.bySemanticsLabel(
              RegExp('^${RegExp.escape('Connect token')}\$'),
            ),
          ),
        };

        await tester.tap(focusCandidates['Fine-grained token']!);
        await tester.pumpAndSettle();

        expect(
          robot.focusedLabel(focusCandidates),
          'Fine-grained token',
        );

        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
        expect(
          robot.focusedLabel(focusCandidates),
          'Remember on this browser',
        );

        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
        expect(robot.focusedLabel(focusCandidates), 'Connect token');
      } finally {
        semantics.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
}
