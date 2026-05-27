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
    'TS-151 creates a Local Git issue when optional custom fields stay empty',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts141LocalGitFixture? fixture;

      const createdSummary = 'TS-151 blank custom fields keep core issue save';
      const createdDescription =
          'Created through the Local Git create form while leaving optional custom fields empty.';

      try {
        fixture = await tester.runAsync(Ts141LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-151 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-151 requires a clean Local Git repository before opening '
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
          summary: createdSummary,
          description: createdDescription,
        );
        await screen.submitCreateIssue(createIssueSection: createIssueSection);
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));

        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isFalse,
          reason:
              'Leaving optional custom fields blank should not block Local Git '
              'issue creation. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'The create form should close after successful issue creation, '
              'but the Summary field is still visible.',
        );

        await screen.searchIssues(Ts141LocalGitFixture.createdIssueKey);
        await screen.expectIssueSearchResultVisible(
          Ts141LocalGitFixture.createdIssueKey,
          createdSummary,
        );
        await screen.openIssue(
          Ts141LocalGitFixture.createdIssueKey,
          createdSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts141LocalGitFixture.createdIssueKey,
        );
        await screen.expectIssueDetailText(
          Ts141LocalGitFixture.createdIssueKey,
          createdSummary,
        );
        final latestHead = await tester.runAsync(fixture.headRevision) ?? '';
        final latestParent = await tester.runAsync(fixture.parentOfHead) ?? '';
        final latestSubject =
            await tester.runAsync(fixture.latestCommitSubject) ?? '';
        final latestFiles =
            await tester.runAsync(fixture.latestCommitFiles) ?? <String>[];
        final finalStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final createdMarkdown = await tester.runAsync(
          () => fixture!.readRepositoryFile(
            Ts141LocalGitFixture.createdIssuePath,
          ),
        );

        expect(
          latestHead,
          isNot(initialHead),
          reason:
              'Successful Local Git issue creation should append a new commit.',
        );
        expect(
          latestParent,
          initialHead,
          reason:
              'The create commit should be written directly on top of the clean '
              'fixture HEAD.',
        );
        expect(
          latestSubject,
          'Create ${Ts141LocalGitFixture.createdIssueKey}',
          reason:
              'The latest Local Git commit should be dedicated to the create '
              'issue action.',
        );
        expect(
          latestFiles,
          equals([Ts141LocalGitFixture.createdIssuePath]),
          reason:
              'Issue creation should commit only the new issue file. Observed '
              'files: ${latestFiles.join(' | ')}',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'Successful Local Git issue creation should leave the worktree '
              'clean, but `git status --short` returned '
              '${finalStatus.join(' | ')}.',
        );
        expect(
          createdMarkdown,
          contains(createdSummary),
          reason:
              'The generated main.md file should contain the entered Summary.',
        );
        expect(
          createdMarkdown,
          contains(createdDescription),
          reason:
              'The generated main.md file should contain the entered Description.',
        );
        expect(
          createdMarkdown,
          isNot(contains('null')),
          reason:
              'Empty optional custom fields should not persist the literal '
              '`null` value into main.md.\nObserved main.md:\n$createdMarkdown',
        );
        expect(
          createdMarkdown,
          isNot(contains('undefined')),
          reason:
              'Empty optional custom fields should not persist the literal '
              '`undefined` value into main.md.\nObserved main.md:\n$createdMarkdown',
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
