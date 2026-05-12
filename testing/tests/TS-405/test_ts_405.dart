import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/settings/local_git_settings_screen_context.dart';
import 'support/ts405_local_git_fixture.dart';

void main() {
  testWidgets(
    'TS-405 status catalog management blocks duplicate IDs and missing names before repository writes',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = createLocalGitSettingsScreenRobot(tester);
      Ts405LocalGitFixture? fixture;

      const duplicateId = 'in-progress';
      const duplicateName = 'Doing';
      const missingNameId = 'qa-review';
      const duplicateError =
          'Save failed: Status ID "$duplicateId" is defined more than once.';
      const missingNameError =
          'Save failed: Statuses must include both an ID and a name.';
      const statusesPath = 'DEMO/config/statuses.json';

      try {
        fixture = await tester.runAsync(Ts405LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-405 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final originalStatusesJson =
            await tester.runAsync(
              () => fixture!.readRepositoryFile(statusesPath),
            ) ??
            '';

        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-405 requires a clean Local Git repository before editing Settings, '
              'but `git status --short` returned ${initialStatus.join(' | ')}.',
        );

        await robot.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await robot.openProjectStatuses();

        expect(
          robot.isVisibleText('Project Settings'),
          isTrue,
          reason:
              'Step 1 failed: the Settings surface did not render visible "Project Settings" text. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          robot.isVisibleText('Project settings administration'),
          isTrue,
          reason:
              'Step 1 failed: the Settings surface did not render visible '
              '"Project settings administration" text. Visible texts: '
              '${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          robot.isVisibleText('Statuses'),
          isTrue,
          reason:
              'Step 1 failed: the Settings surface did not render visible "Statuses" text. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );
        expect(
          robot.statusSummaryVisible(
            name: 'In Progress',
            id: duplicateId,
            category: 'indeterminate',
          ),
          isTrue,
          reason:
              'Step 1 failed: the visible Statuses list did not show In Progress, ID: $duplicateId, '
              'and Category: indeterminate for the seeded status. Visible texts: '
              '${_formatSnapshot(robot.visibleTexts())}.',
        );

        await robot.tapActionButton('Add status');
        robot.expectStatusEditorVisible('Add status');
        await robot.enterTextField('ID', duplicateId);
        await robot.enterTextField('Name', duplicateName);

        expect(
          robot.textFieldValue('ID'),
          duplicateId,
          reason:
              'Step 3 failed: the Add status dialog did not keep the entered duplicate ID visible.',
        );
        expect(
          robot.textFieldValue('Name'),
          duplicateName,
          reason:
              'Step 3 failed: the Add status dialog did not keep the entered Name visible.',
        );

        await robot.tapActionButton('Save');
        expect(
          await robot.isTextFieldVisible('ID'),
          isFalse,
          reason:
              'Step 4 failed: saving the Add status dialog should close the editor overlay before repository validation runs.',
        );

        await robot.tapActionButton('Save settings');
        final duplicateAttemptHead =
            await tester.runAsync(fixture.headRevision) ?? '';
        final duplicateAttemptStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final duplicateAttemptStatusesJson =
            await tester.runAsync(
              () => fixture!.readRepositoryFile(statusesPath),
            ) ??
            '';
        if (!robot.isVisibleText(duplicateError)) {
          fail(
            'Step 4 failed: saving Settings after adding the duplicate status '
            'ID "$duplicateId" did not render the expected validation message '
            '"$duplicateError". The unsaved "$duplicateName" draft remained '
            'visible in Settings, the repository HEAD stayed at '
            '$duplicateAttemptHead, `git status --short` remained '
            '${duplicateAttemptStatus.isEmpty ? '<clean>' : duplicateAttemptStatus.join(' | ')}, '
            'and DEMO/config/statuses.json stayed unchanged as '
            '$duplicateAttemptStatusesJson. Visible texts: '
            '${_formatSnapshot(robot.visibleTexts(), limit: 60)}.',
          );
        }

        await _expectRepositoryUnchanged(
          tester,
          fixture: fixture,
          expectedHead: initialHead,
          expectedStatusesJson: originalStatusesJson,
          failingStep: 4,
          context:
              'the duplicate-ID validation attempt should not write project settings',
        );

        await robot.openProjectStatuses();

        await robot.tapActionButton('Add status');
        robot.expectStatusEditorVisible('Add status');
        await robot.enterTextField('ID', missingNameId);

        expect(
          robot.textFieldValue('ID'),
          missingNameId,
          reason:
              'Step 5 failed: the second Add status dialog did not keep the entered ID visible.',
        );
        expect(
          robot.textFieldValue('Name'),
          isEmpty,
          reason:
              'Step 5 precondition failed: the Name field should still be blank before the missing-name validation attempt.',
        );

        await robot.tapActionButton('Save');
        await robot.tapActionButton('Save settings');

        expect(
          robot.isVisibleText(missingNameError),
          isTrue,
          reason:
              'Step 5 failed: saving Settings after leaving Name blank should show "$missingNameError". '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
        );

        await _expectRepositoryUnchanged(
          tester,
          fixture: fixture,
          expectedHead: initialHead,
          expectedStatusesJson: originalStatusesJson,
          failingStep: 5,
          context:
              'the missing-name validation attempt should not write project settings',
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

Future<void> _expectRepositoryUnchanged(
  WidgetTester tester, {
  required Ts405LocalGitFixture fixture,
  required String expectedHead,
  required String expectedStatusesJson,
  required int failingStep,
  required String context,
}) async {
  final latestHead = await tester.runAsync(fixture.headRevision) ?? '';
  final statusLines =
      await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
  final statusesJson =
      await tester.runAsync(
        () => fixture.readRepositoryFile('DEMO/config/statuses.json'),
      ) ??
      '';

  expect(
    latestHead,
    expectedHead,
    reason: 'Step $failingStep failed: $context must not create a new commit.',
  );
  expect(
    statusLines,
    isEmpty,
    reason:
        'Step $failingStep failed: $context must leave the Local Git worktree clean, '
        'but `git status --short` returned ${statusLines.join(' | ')}.',
  );
  expect(
    statusesJson,
    expectedStatusesJson,
    reason:
        'Step $failingStep failed: $context must leave DEMO/config/statuses.json unchanged.',
  );
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
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
