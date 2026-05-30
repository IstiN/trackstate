import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-141/support/ts141_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-191 blocks Local Git issue creation when Summary is blank despite valid custom-field input',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts141LocalGitFixture? fixture;

      const descriptionValue =
          'Description stays filled while the missing Summary validation is shown.';
      const solutionValue =
          'Valid custom-field content must not bypass the required Summary check.';
      const acceptanceCriteriaValue =
          '- Save is blocked.\n- The user sees the summary-required error.\n- No issue file is created.';
      const validationMessage =
          'Save failed: Issue summary is required before creating an issue.';

      try {
        fixture = await tester.runAsync(Ts141LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-191 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-191 requires a clean Local Git repository before opening '
              'Create issue, but `git status --short` returned '
              '${initialStatus.join(' | ')}.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          Ts141LocalGitFixture.existingIssueKey,
          Ts141LocalGitFixture.existingIssueSummary,
        );

        final createIssueSection = await screen.openCreateIssueFlow();
        await screen.expectCreateIssueFormVisible(
          createIssueSection: createIssueSection,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Solution',
          createIssueSection: createIssueSection,
          failingStep: 3,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Acceptance Criteria',
          createIssueSection: createIssueSection,
          failingStep: 3,
        );

        await screen.enterLabeledTextField(
          'Description',
          text: descriptionValue,
        );
        await screen.enterLabeledTextField('Solution', text: solutionValue);
        await screen.enterLabeledTextField(
          'Acceptance Criteria',
          text: acceptanceCriteriaValue,
        );
        await screen.submitCreateIssue(createIssueSection: createIssueSection);
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));

        expect(
          await screen.isMessageBannerVisibleContaining(validationMessage),
          isTrue,
          reason:
              'Step 5 failed: submitting Create issue with a blank Summary '
              'should surface the visible validation error "$validationMessage". '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isTrue,
          reason:
              'Step 5 failed: the Create issue form should remain open after '
              'Summary validation fails, but the Summary field is no longer '
              'visible.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          isEmpty,
          reason:
              'Step 5 failed: the Summary field should still be visibly blank '
              'after the blocked save attempt.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Description'),
          descriptionValue,
          reason:
              'Step 5 failed: the user-entered Description should remain '
              'visible after the blocked save attempt.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Solution'),
          solutionValue,
          reason:
              'Step 5 failed: the user-entered Solution should remain visible '
              'after the blocked save attempt.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Acceptance Criteria'),
          acceptanceCriteriaValue,
          reason:
              'Step 5 failed: the user-entered Acceptance Criteria should '
              'remain visible after the blocked save attempt.',
        );

        final latestHead = await tester.runAsync(fixture.headRevision) ?? '';
        final finalStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final createdIssueExists = await tester.runAsync(
          () => File(
            '${fixture!.repositoryPath}/${Ts141LocalGitFixture.createdIssuePath}',
          ).exists(),
        );

        expect(
          latestHead,
          initialHead,
          reason:
              'A blocked create attempt with a blank Summary must not add a '
              'new git commit.',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'A blocked create attempt with a blank Summary must leave the '
              'Local Git worktree clean, but `git status --short` returned '
              '${finalStatus.join(' | ')}.',
        );
        expect(
          createdIssueExists,
          isFalse,
          reason:
              'A blocked create attempt with a blank Summary must not create '
              'the new issue file at ${Ts141LocalGitFixture.createdIssuePath}.',
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Future<void> _expectCreateFieldVisible(
  TrackStateAppComponent screen, {
  required String label,
  required String createIssueSection,
  required int failingStep,
}) async {
  if (await screen.isTextFieldVisible(label)) {
    return;
  }
  fail(
    'Step $failingStep failed: the Local Git Create issue form opened from '
    '$createIssueSection did not render a visible "$label" field. Visible '
    'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
    'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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
