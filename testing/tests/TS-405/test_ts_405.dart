import 'package:flutter/material.dart';
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

        await _openStatuses(robot, tester, fixture.repositoryPath);
        await _expectStatusSnapshot(
          tester,
          name: 'In Progress',
          id: duplicateId,
          category: 'indeterminate',
          failingStep: 1,
        );

        await _tapButton(tester, filledLabel: 'Add status');
        await _expectTextVisible(tester, 'Add status', failingStep: 2);
        await _expectLabeledTextFieldVisible(tester, 'ID', failingStep: 3);
        await _expectLabeledTextFieldVisible(tester, 'Name', failingStep: 3);
        await _expectTextVisible(tester, 'Category', failingStep: 3);
        await tester.enterText(
          _labeledSettingsTextField('ID').first,
          duplicateId,
        );
        await tester.pumpAndSettle();
        await tester.enterText(
          _labeledSettingsTextField('Name').first,
          duplicateName,
        );
        await tester.pumpAndSettle();

        expect(
          _textFormFieldValue(tester, 'ID'),
          duplicateId,
          reason:
              'Step 3 failed: the Add status dialog did not keep the entered duplicate ID visible.',
        );
        expect(
          _textFormFieldValue(tester, 'Name'),
          duplicateName,
          reason:
              'Step 3 failed: the Add status dialog did not keep the entered Name visible.',
        );

        await _tapButton(tester, filledLabel: 'Save');
        expect(
          _labeledSettingsTextField('ID'),
          findsNothing,
          reason:
              'Step 4 failed: saving the Add status dialog should close the editor overlay before repository validation runs.',
        );

        await _tapButton(tester, filledLabel: 'Save settings');
        await tester.pumpAndSettle();
        final duplicateAttemptHead =
            await tester.runAsync(fixture.headRevision) ?? '';
        final duplicateAttemptStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final duplicateAttemptStatusesJson =
            await tester.runAsync(
              () => fixture!.readRepositoryFile(statusesPath),
            ) ??
            '';
        if (_messageText(duplicateError).evaluate().isEmpty) {
          fail(
            'Step 4 failed: saving Settings after adding the duplicate status '
            'ID "$duplicateId" did not render the expected validation message '
            '"$duplicateError". The unsaved "$duplicateName" draft remained '
            'visible in Settings, the repository HEAD stayed at '
            '$duplicateAttemptHead, `git status --short` remained '
            '${duplicateAttemptStatus.isEmpty ? '<clean>' : duplicateAttemptStatus.join(' | ')}, '
            'and DEMO/config/statuses.json stayed unchanged as '
            '$duplicateAttemptStatusesJson. Visible texts: '
            '${_formatSnapshot(_visibleTexts(tester), limit: 60)}.',
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

        await _openStatuses(robot, tester, fixture.repositoryPath);

        await _tapButton(tester, filledLabel: 'Add status');
        await _expectTextVisible(tester, 'Add status', failingStep: 5);
        await tester.enterText(
          _labeledSettingsTextField('ID').first,
          missingNameId,
        );
        await tester.pumpAndSettle();

        expect(
          _textFormFieldValue(tester, 'ID'),
          missingNameId,
          reason:
              'Step 5 failed: the second Add status dialog did not keep the entered ID visible.',
        );
        expect(
          _textFormFieldValue(tester, 'Name'),
          isEmpty,
          reason:
              'Step 5 precondition failed: the Name field should still be blank before the missing-name validation attempt.',
        );

        await _tapButton(tester, filledLabel: 'Save');
        await _tapButton(tester, filledLabel: 'Save settings');
        await tester.pumpAndSettle();

        expect(
          _messageText(missingNameError),
          findsOneWidget,
          reason:
              'Step 5 failed: saving Settings after leaving Name blank should show "$missingNameError". '
              'Visible texts: ${_formatSnapshot(_visibleTexts(tester))}.',
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

Future<void> _openStatuses(
  dynamic robot,
  WidgetTester tester,
  String repositoryPath,
) async {
  await robot.pumpLocalGitApp(repositoryPath: repositoryPath);
  await robot.openSettings();
  robot.expectVisibleSettingsContent();
  await tester.tap(robot.statusesTab);
  await tester.pumpAndSettle();
  await _expectTextVisible(tester, 'Project Settings', failingStep: 1);
  await _expectTextVisible(
    tester,
    'Project settings administration',
    failingStep: 1,
  );
  await _expectTextVisible(tester, 'Statuses', failingStep: 1);
}

Future<void> _tapButton(
  WidgetTester tester, {
  String? filledLabel,
  String? textLabel,
}) async {
  final candidates = <Finder>[
    if (filledLabel != null) find.widgetWithText(FilledButton, filledLabel),
    if (textLabel != null) find.widgetWithText(TextButton, textLabel),
    if (filledLabel != null) find.widgetWithText(TextButton, filledLabel),
    if (filledLabel != null)
      find.bySemanticsLabel(RegExp('^${RegExp.escape(filledLabel)}\$')),
  ];
  for (final candidate in candidates) {
    if (candidate.evaluate().isEmpty) {
      continue;
    }
    await tester.ensureVisible(candidate.first);
    await tester.tap(candidate.first, warnIfMissed: false);
    await tester.pumpAndSettle();
    return;
  }

  fail(
    'Expected a visible button labeled "${filledLabel ?? textLabel}", but none was rendered.',
  );
}

Future<void> _expectTextVisible(
  WidgetTester tester,
  String text, {
  required int failingStep,
}) async {
  await tester.pump();
  final finder = find.text(text, findRichText: true);
  if (finder.evaluate().isNotEmpty) {
    return;
  }
  fail(
    'Step $failingStep failed: the Settings surface did not render visible "$text" text. '
    'Visible texts: ${_formatSnapshot(_visibleTexts(tester))}.',
  );
}

Future<void> _expectLabeledTextFieldVisible(
  WidgetTester tester,
  String label, {
  required int failingStep,
}) async {
  await tester.pump();
  if (_labeledSettingsTextField(label).evaluate().isNotEmpty) {
    return;
  }
  fail(
    'Step $failingStep failed: the Add status dialog did not expose a visible "$label" field. '
    'Visible texts: ${_formatSnapshot(_visibleTexts(tester))}.',
  );
}

Future<void> _expectStatusSnapshot(
  WidgetTester tester, {
  required String name,
  required String id,
  required String category,
  required int failingStep,
}) async {
  final combined = _visibleTexts(tester).join(' | ');
  final expectedFragments = <String>[name, 'ID: $id', 'Category: $category'];
  final missing = expectedFragments
      .where((fragment) => !combined.contains(fragment))
      .toList(growable: false);
  if (missing.isEmpty) {
    return;
  }
  fail(
    'Step $failingStep failed: the visible Statuses list did not show ${missing.join(', ')} for the seeded status. '
    'Visible texts: ${_formatSnapshot(_visibleTexts(tester))}.',
  );
}

Finder _labeledSettingsTextField(String label) => find.descendant(
  of: find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$')),
  matching: find.byWidgetPredicate(
    (widget) => widget is EditableText || widget is TextField,
    description: 'editable control labeled $label',
  ),
);

String _textFormFieldValue(WidgetTester tester, String label) {
  final field = _labeledSettingsTextField(label);
  if (field.evaluate().isEmpty) {
    fail('Expected a visible editable control labeled "$label".');
  }
  final widget = tester.widget(field.first);
  if (widget is EditableText) {
    return widget.controller.text;
  }
  if (widget is TextField) {
    return widget.controller?.text ?? '';
  }
  fail('Expected the "$label" control to expose an editable text controller.');
}

Finder _messageText(String text) => find.text(text, findRichText: true);

List<String> _visibleTexts(WidgetTester tester) {
  final values = <String>[];
  for (final widget in tester.widgetList<Text>(find.byType(Text))) {
    final value = widget.data?.trim();
    if (value == null || value.isEmpty || values.contains(value)) {
      continue;
    }
    values.add(value);
  }
  return values;
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
