import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/utils/color_contrast.dart';
import '../../fixtures/settings/local_git_settings_screen_context.dart';
import 'support/ts404_settings_admin_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-404 settings admin keeps tabbed navigation and responsive edit surfaces',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = createLocalGitSettingsScreenRobot(tester);
      Ts404SettingsAdminFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts404SettingsAdminFixture.create);
        if (fixture == null) {
          throw StateError('TS-404 fixture creation did not complete.');
        }

        await robot.resize(const Size(1280, 900));
        await robot.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await robot.openSettings();
        robot.expectVisibleSettingsContent();

        for (final tabLabel in const [
          'Statuses',
          'Workflows',
          'Issue Types',
          'Fields',
        ]) {
          expect(
            robot.tabByLabel(tabLabel),
            findsOneWidget,
            reason:
                'Step 2 failed: expected the visible "$tabLabel" tab in Settings. '
                'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
          );
        }

        final saveSettingsBackground = robot.resolvedButtonBackground(
          robot.saveSettingsButton,
          const <WidgetState>{},
        );
        final saveSettingsForeground = robot.resolvedButtonForeground(
          robot.saveSettingsButton,
          const <WidgetState>{},
          text: 'Save settings',
        );
        final saveSettingsContrast = contrastRatio(
          saveSettingsForeground,
          saveSettingsBackground,
        );

        expect(
          _rgbHex(saveSettingsBackground),
          _rgbHex(robot.colors().primary),
          reason:
              'Expected Result failed: the visible Save settings action should use the TrackStateTheme primary token. '
              'Rendered=${_rgbHex(saveSettingsBackground)} token=${_rgbHex(robot.colors().primary)}.',
        );
        expect(
          _rgbHex(saveSettingsForeground),
          _rgbHex(robot.colors().page),
          reason:
              'Expected Result failed: the visible Save settings label should use the TrackStateTheme page token. '
              'Rendered=${_rgbHex(saveSettingsForeground)} token=${_rgbHex(robot.colors().page)}.',
        );
        expect(
          saveSettingsContrast >= 4.5,
          isTrue,
          reason:
              'Expected Result failed: Save settings contrast was ${saveSettingsContrast.toStringAsFixed(2)}:1, below 4.5:1.',
        );

        await robot.selectTab('Statuses');
        expect(
          robot.configCardItem(
            'Statuses',
            Ts404SettingsAdminFixture.statusName,
          ),
          findsOneWidget,
          reason:
              'Step 3 failed: the Statuses tab did not show the visible "${Ts404SettingsAdminFixture.statusName}" row required for editing. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          robot.actionButton(Ts404SettingsAdminFixture.editStatusLabel),
          findsOneWidget,
          reason:
              'Step 3 failed: the visible Edit action for "${Ts404SettingsAdminFixture.statusName}" was not present on the Statuses tab. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );

        await robot.tapActionButton(Ts404SettingsAdminFixture.editStatusLabel);

        expect(
          robot.editorTitle('Edit status'),
          findsOneWidget,
          reason:
              'Step 4 failed: opening the status edit action on the wide layout did not show the visible "Edit status" heading. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          find.text('ID'),
          findsOneWidget,
          reason:
              'Step 4 failed: the wide edit surface did not show the visible ID field label. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          find.text('Name'),
          findsOneWidget,
          reason:
              'Step 4 failed: the wide edit surface did not show the visible Name field label. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          find.text('Category'),
          findsOneWidget,
          reason:
              'Step 4 failed: the wide edit surface did not show the visible Category field label. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          robot.settingsEditorDialog,
          findsNothing,
          reason:
              'Step 4 failed: the wide layout rendered the status editor as a centered Dialog instead of a drawer-style side surface. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );

        final wideRect = robot.editorSurfaceRect('Edit status');
        final wideViewport = robot.viewportSize;
        debugPrint('TS-404 wide editor rect: $wideRect viewport=$wideViewport');

        expect(
          wideRect.left > wideViewport.width / 2,
          isTrue,
          reason:
              'Step 4 failed: the wide edit surface was not positioned on the right side of the viewport. '
              'Rect=$wideRect viewport=$wideViewport.',
        );
        expect(
          (wideViewport.width - wideRect.right) <= 16,
          isTrue,
          reason:
              'Step 4 failed: the wide edit surface was not docked close enough to the right edge to behave like a side drawer. '
              'Rect=$wideRect viewport=$wideViewport.',
        );
        expect(
          wideRect.width <= 520,
          isTrue,
          reason:
              'Step 4 failed: the wide edit surface exceeded the expected drawer width cap. '
              'Rect=$wideRect viewport=$wideViewport.',
        );

        await robot.tapActionButton('Cancel');
        expect(
          robot.editorTitle('Edit status'),
          findsNothing,
          reason:
              'Step 4 cleanup failed: the status editor stayed visible after Cancel on the wide layout.',
        );

        await robot.resize(const Size(560, 900));
        await robot.selectTab('Statuses');
        await robot.tapActionButton(Ts404SettingsAdminFixture.editStatusLabel);

        expect(
          robot.editorTitle('Edit status'),
          findsOneWidget,
          reason:
              'Step 6 failed: reopening the status editor on the narrow layout did not show the visible "Edit status" heading. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          robot.settingsEditorDialog,
          findsOneWidget,
          reason:
              'Step 6 failed: the narrow layout did not render the status editor as a modal surface. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );

        final narrowRect = robot.editorSurfaceRect('Edit status');
        final narrowViewport = robot.viewportSize;
        final leftMargin = narrowRect.left;
        final rightMargin = narrowViewport.width - narrowRect.right;
        debugPrint(
          'TS-404 narrow editor rect: $narrowRect viewport=$narrowViewport '
          'leftMargin=$leftMargin rightMargin=$rightMargin',
        );

        expect(
          (leftMargin - rightMargin).abs() <= 24,
          isTrue,
          reason:
              'Step 6 failed: the narrow edit surface was not centered like a modal sheet. '
              'Rect=$narrowRect viewport=$narrowViewport leftMargin=$leftMargin rightMargin=$rightMargin.',
        );
        expect(
          narrowRect.width < narrowViewport.width,
          isTrue,
          reason:
              'Step 6 failed: the narrow edit surface expanded to the full viewport width instead of staying modal. '
              'Rect=$narrowRect viewport=$narrowViewport.',
        );
        expect(
          find.text('ID'),
          findsOneWidget,
          reason:
              'Step 6 failed: the narrow modal edit surface did not show the visible ID field label. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          find.text('Name'),
          findsOneWidget,
          reason:
              'Step 6 failed: the narrow modal edit surface did not show the visible Name field label. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          find.text('Category'),
          findsOneWidget,
          reason:
              'Step 6 failed: the narrow modal edit surface did not show the visible Category field label. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}

String _rgbHex(Color color) {
  final rgb = color.toARGB32() & 0x00FFFFFF;
  return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
}
