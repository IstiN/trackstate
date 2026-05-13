import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/fixtures/settings/local_git_settings_screen_context.dart';
import '../testing/tests/TS-483/support/ts483_attachments_settings_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'attachments settings keep Reset and Save settings after Release tag prefix in tab order',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = createLocalGitSettingsScreenRobot(tester);
      Ts483AttachmentsSettingsFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts483AttachmentsSettingsFixture.create);
        if (fixture == null) {
          throw StateError('Attachments settings fixture creation did not complete.');
        }

        await robot.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await robot.openSettings();
        await robot.selectTab('Attachments');
        await robot.selectAttachmentStorageMode('GitHub Releases');
        await robot.enterAttachmentReleaseTagPrefix('release-assets-');

        final focusCandidates = <String, Finder>{
          'Attachment storage mode': find.bySemanticsLabel(
            RegExp('Attachment storage mode'),
          ),
          'Release tag prefix': find.bySemanticsLabel(
            RegExp('Release tag prefix'),
          ),
          'Reset': robot.resetSettingsButton,
          'Save settings': robot.saveSettingsButton,
        };

        await robot.clearFocus();

        final reachedStorageSelector = await _focusByTab(
          tester,
          label: 'Attachment storage mode',
          finder: focusCandidates['Attachment storage mode']!,
          focusedLabel: () => robot.focusedLabel(focusCandidates),
        );
        expect(reachedStorageSelector, isTrue);

        final focusOrder = await _collectFocusOrder(
          tester,
          focusedLabel: () => robot.focusedLabel(focusCandidates),
          tabSteps: 3,
        );

        expect(
          focusOrder,
          const <String>[
            'Attachment storage mode',
            'Release tag prefix',
            'Reset',
            'Save settings',
          ],
        );
      } finally {
        await tester.runAsync(() async {
          await fixture?.dispose();
        });
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}

Future<bool> _focusByTab(
  WidgetTester tester, {
  required String label,
  required Finder finder,
  required String? Function() focusedLabel,
  int maxTabs = 24,
}) async {
  for (var index = 0; index < maxTabs; index += 1) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    if (finder.evaluate().isNotEmpty && focusedLabel() == label) {
      return true;
    }
  }
  return false;
}

Future<List<String>> _collectFocusOrder(
  WidgetTester tester, {
  required String? Function() focusedLabel,
  required int tabSteps,
}) async {
  final order = <String>[focusedLabel() ?? '<outside candidates>'];
  for (var index = 0; index < tabSteps; index += 1) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    order.add(focusedLabel() ?? '<outside candidates>');
  }
  return order;
}
