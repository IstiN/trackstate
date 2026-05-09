import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-141/support/ts141_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-209 cancels Local Git issue creation without persisting filesystem changes',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts141LocalGitFixture? fixture;

      const draftSummary = 'TS-209 cancel should discard all Local Git changes';
      const draftDescription =
          'This draft should disappear after the user cancels the create form.';
      const solutionValue =
          'Cancel must discard the entered Local Git custom-field values.';
      const acceptanceCriteriaValue =
          '- The dialog closes.\n- No new issue file appears.\n- Git history stays unchanged.';
      const diagramsValue = 'flowchart TD; Cancel-->DiscardDraft;';

      try {
        fixture = await tester.runAsync(Ts141LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-209 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final initialFilesystem =
            await tester.runAsync(
              () => _snapshotRepositoryFilesystem(fixture!.repositoryPath),
            ) ??
            const <String>[];

        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-209 requires a clean Local Git repository before opening '
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
        await _expectVisibleControl(
          screen,
          label: 'Save',
          failingStep: 1,
          context: 'inside the Local Git Create issue dialog',
        );
        await _expectVisibleControl(
          screen,
          label: 'Cancel',
          failingStep: 1,
          context: 'inside the Local Git Create issue dialog',
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Solution',
          createIssueSection: createIssueSection,
          failingStep: 1,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Acceptance Criteria',
          createIssueSection: createIssueSection,
          failingStep: 1,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Diagrams',
          createIssueSection: createIssueSection,
          failingStep: 1,
        );

        await screen.populateCreateIssueForm(
          summary: draftSummary,
          description: draftDescription,
        );
        await screen.enterLabeledTextField('Solution', text: solutionValue);
        await screen.enterLabeledTextField(
          'Acceptance Criteria',
          text: acceptanceCriteriaValue,
        );
        await screen.enterLabeledTextField('Diagrams', text: diagramsValue);

        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          draftSummary,
          reason:
              'Step 2 failed: the visible Summary field did not retain the '
              'entered draft value before cancellation.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Description'),
          draftDescription,
          reason:
              'Step 2 failed: the visible Description field did not retain the '
              'entered draft value before cancellation.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Solution'),
          solutionValue,
          reason:
              'Step 2 failed: the visible Solution field did not retain the '
              'entered draft value before cancellation.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Acceptance Criteria'),
          acceptanceCriteriaValue,
          reason:
              'Step 2 failed: the visible Acceptance Criteria field did not '
              'retain the entered draft value before cancellation.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Diagrams'),
          diagramsValue,
          reason:
              'Step 2 failed: the visible Diagrams field did not retain the '
              'entered draft value before cancellation.',
        );

        final cancelled = await screen.tapVisibleControl('Cancel');
        expect(
          cancelled,
          isTrue,
          reason:
              'Step 3 failed: the visible "Cancel" action could not dismiss '
              'the Local Git Create issue dialog. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'Step 3 failed: tapping "Cancel" should close the Local Git '
              'Create issue dialog, but the Summary field remained visible. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isFalse,
          reason:
              'Step 3 failed: cancelling Create issue should not show a save '
              'failure banner. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          Ts141LocalGitFixture.existingIssueKey,
          Ts141LocalGitFixture.existingIssueSummary,
        );
        await screen.searchIssues(Ts141LocalGitFixture.createdIssueKey);
        screen.expectIssueSearchResultAbsent(
          Ts141LocalGitFixture.createdIssueKey,
          draftSummary,
        );

        final latestHead = await tester.runAsync(fixture.headRevision) ?? '';
        final finalStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final finalFilesystem =
            await tester.runAsync(
              () => _snapshotRepositoryFilesystem(fixture!.repositoryPath),
            ) ??
            const <String>[];
        final createdIssueExists = await tester.runAsync(
          () => File(
            p.join(
              fixture!.repositoryPath,
              Ts141LocalGitFixture.createdIssuePath,
            ),
          ).exists(),
        );

        expect(
          latestHead,
          initialHead,
          reason:
              'Step 4 failed: cancelling Create issue must not add a new git '
              'commit.',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'Step 4 failed: cancelling Create issue must leave the Local Git '
              'worktree clean, but `git status --short` returned '
              '${finalStatus.join(' | ')}.',
        );
        expect(
          createdIssueExists,
          isFalse,
          reason:
              'Step 4 failed: cancelling Create issue must not create the issue '
              'file at ${Ts141LocalGitFixture.createdIssuePath}.',
        );
        expect(
          finalFilesystem,
          initialFilesystem,
          reason:
              'Step 4 failed: cancelling Create issue changed the Local Git '
              'filesystem snapshot. Before: ${initialFilesystem.join(' | ')}. '
              'After: ${finalFilesystem.join(' | ')}.',
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

Future<void> _expectVisibleControl(
  TrackStateAppComponent screen, {
  required String label,
  required int failingStep,
  required String context,
}) async {
  final isVisible =
      await screen.isSemanticsLabelVisible(label) ||
      await screen.isTextVisible(label);
  if (isVisible) {
    return;
  }
  fail(
    'Step $failingStep failed: no visible "$label" control was rendered '
    '$context. Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
    'Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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

Future<List<String>> _snapshotRepositoryFilesystem(
  String repositoryPath,
) async {
  final entries = <String>[];
  await for (final entity in Directory(repositoryPath).list(recursive: true)) {
    final relativePath = p.relative(entity.path, from: repositoryPath);
    if (relativePath.isEmpty || relativePath == '.') {
      continue;
    }
    if (entity is Directory || p.basename(relativePath) == 'main.md') {
      entries.add(entity is Directory ? '$relativePath/' : relativePath);
    }
  }
  entries.sort();
  return List.unmodifiable(entries);
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
