import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/screens/issue_type_settings_robot.dart';
import '../../fixtures/settings/local_git_settings_screen_context.dart';
import 'support/ts407_issue_type_admin_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-407 issue type administration supports hierarchy edits and constrains icon selection',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final settingsRobot = createLocalGitSettingsScreenRobot(tester);
      final issueTypeRobot = IssueTypeSettingsRobot(tester, settingsRobot);
      final failures = <String>[];
      Ts407IssueTypeAdminFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts407IssueTypeAdminFixture.create);
        if (fixture == null) {
          throw StateError('TS-407 fixture creation did not complete.');
        }

        await settingsRobot.pumpLocalGitApp(
          repositoryPath: fixture.repositoryPath,
        );
        await settingsRobot.openSettings();
        settingsRobot.expectVisibleSettingsContent();
        await issueTypeRobot.openIssueTypesTab();

        if (issueTypeRobot
            .issueTypeTile(Ts407IssueTypeAdminFixture.storyName)
            .evaluate()
            .isEmpty) {
          failures.add(
            'Step 1 failed: Settings > Issue Types did not show the existing '
            '"${Ts407IssueTypeAdminFixture.storyName}" entry. Visible texts: '
            '${issueTypeRobot.visibleTextSnapshot()}.',
          );
        }

        final editStoryButton = issueTypeRobot.editIssueTypeButton(
          Ts407IssueTypeAdminFixture.storyName,
        );
        if (editStoryButton.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: the Story issue type did not expose a visible '
            'Edit action in Settings > Issue Types, so the admin flow could not '
            'open the issue type editor. Visible texts: '
            '${issueTypeRobot.visibleTextSnapshot()}.',
          );
        } else {
          await issueTypeRobot.openIssueTypeEditor(
            Ts407IssueTypeAdminFixture.storyName,
          );

          const requiredEditorTexts = <String>[
            'Edit issue type',
            'ID',
            'Name',
            'Hierarchy level',
            'Icon',
            'Workflow',
            'Save',
            'Cancel',
          ];
          final missingEditorTexts = requiredEditorTexts
              .where((text) => !issueTypeRobot.showsText(text))
              .toList(growable: false);
          if (missingEditorTexts.isNotEmpty) {
            failures.add(
              'Step 2 failed: editing Story should show the full issue type '
              'editor, but the dialog was missing '
              '${missingEditorTexts.map((text) => '"$text"').join(', ')}. '
              'Visible dialog texts: ${issueTypeRobot.visibleTextSnapshot()}.',
            );
          }

          final initialHierarchy = issueTypeRobot.readTextFieldValue(
            'Hierarchy level',
          );
          if (initialHierarchy != '0') {
            failures.add(
              'Step 3 precondition failed: Story should start with hierarchy '
              'level 0, but the editor showed "$initialHierarchy". Visible '
              'dialog texts: ${issueTypeRobot.visibleTextSnapshot()}.',
            );
          }

          await issueTypeRobot.enterTextFieldValue('Hierarchy level', '1');
          await issueTypeRobot.saveEditor();

          if (!issueTypeRobot.issueTypeSubtitleContains(
            'Story',
            'Hierarchy level: 1',
          )) {
            failures.add(
              'Step 3 failed: after saving the Story editor with hierarchy '
              'level 1, the Issue Types list did not show '
              '"Hierarchy level: 1" for Story. Visible texts: '
              '${issueTypeRobot.visibleTextSnapshot()}.',
            );
          }

          await issueTypeRobot.saveSettings();
          await _waitForCondition(
            tester,
            () async {
              final savedIssueTypes = await tester.runAsync(
                fixture!.readIssueTypeEntries,
              );
              if (savedIssueTypes == null) {
                return false;
              }
              final savedStory = savedIssueTypes.singleWhere(
                (entry) => entry['id'] == Ts407IssueTypeAdminFixture.storyId,
              );
              return savedStory['hierarchyLevel'] == 1;
            },
            failureMessage:
                'Step 3 failed: Save settings did not persist Story hierarchy '
                'level 1 to DEMO/config/issue-types.json.',
          );

          final persistedIssueTypes = await tester.runAsync(
            fixture.readIssueTypeEntries,
          );
          if (persistedIssueTypes == null) {
            failures.add(
              'Step 3 failed: Save settings completed in the UI, but the '
              'fixture could not read back config/issue-types.json for '
              'verification.',
            );
          } else {
            final persistedStory = persistedIssueTypes.singleWhere(
              (entry) => entry['id'] == Ts407IssueTypeAdminFixture.storyId,
            );
            if (persistedStory['hierarchyLevel'] != 1) {
              failures.add(
                'Step 3 failed: Save settings did not persist Story hierarchy '
                'level 1 to DEMO/config/issue-types.json. Observed Story entry: '
                '$persistedStory.',
              );
            }
          }

          await issueTypeRobot.openIssueTypesTab();
          final reopenedStoryTile = issueTypeRobot.issueTypeTile(
            Ts407IssueTypeAdminFixture.storyName,
          );
          if (reopenedStoryTile.evaluate().isEmpty) {
            failures.add(
              'Step 4 failed: after Save settings, re-entering Settings > Issue '
              'Types did not show the Story row again, so the test could not '
              'reopen the visible admin flow. Visible texts: '
              '${issueTypeRobot.visibleTextSnapshot()}.',
            );
          } else {
            final reopenedEditButton = issueTypeRobot.editIssueTypeButton(
              Ts407IssueTypeAdminFixture.storyName,
            );
            if (reopenedEditButton.evaluate().isEmpty) {
              failures.add(
                'Step 4 failed: after Save settings, the visible Story row in '
                'Settings > Issue Types did not expose an Edit action, so the '
                'test could not reopen the editor from the user-visible admin '
                'surface. Visible texts: ${issueTypeRobot.visibleTextSnapshot()}.',
              );
            } else {
              await issueTypeRobot.openIssueTypeEditor(
                Ts407IssueTypeAdminFixture.storyName,
              );

              final iconPickerOpened = await issueTypeRobot.openIconPicker();
              final iconControlDescriptions = issueTypeRobot
                  .describeIconInputControls();
              if (!iconPickerOpened) {
                failures.add(
                  'Step 4 failed: reopening Story showed the Icon control as '
                  '${iconControlDescriptions.isEmpty ? 'no discoverable picker surface' : iconControlDescriptions.join(', ')} '
                  'instead of a user-visible picker for the supported '
                  'TrackState outline glyphs '
                  '(${IssueTypeSettingsRobot.iconPickerLabels.join(', ')}).',
                );
              } else {
                final iconOptions = issueTypeRobot.readDropdownOptions('Icon');
                final missingIconOptions = IssueTypeSettingsRobot
                    .iconPickerLabels
                    .where((label) => !iconOptions.contains(label))
                    .toList(growable: false);
                if (missingIconOptions.isNotEmpty) {
                  failures.add(
                    'Step 4 failed: the opened Icon picker did not expose the '
                    'supported TrackState glyph choices '
                    '${missingIconOptions.map((label) => '"$label"').join(', ')}. '
                    'Observed options: ${iconOptions.isEmpty ? '<none>' : iconOptions.join(', ')}.',
                  );
                }
              }
            }
          }

          final forbiddenUploadTexts = <String>[
            'Upload',
            'Upload attachment',
            'Choose a file',
            'Browse',
            'Custom image',
          ];
          final visibleForbiddenTexts = forbiddenUploadTexts
              .where(issueTypeRobot.showsText)
              .toList(growable: false);
          if (visibleForbiddenTexts.isNotEmpty) {
            failures.add(
              'Step 5 failed: the issue type icon picker must not allow '
              'arbitrary graphics upload, but the editor showed '
              '${visibleForbiddenTexts.map((text) => '"$text"').join(', ')}. '
              'Visible dialog texts: ${issueTypeRobot.visibleTextSnapshot()}.',
            );
          }
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
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

Future<void> _waitForCondition(
  WidgetTester tester,
  Future<bool> Function() condition, {
  required String failureMessage,
  Duration timeout = const Duration(seconds: 5),
  Duration step = const Duration(milliseconds: 100),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    await tester.pump(step);
    if (await condition()) {
      return;
    }
  }
  fail(failureMessage);
}
