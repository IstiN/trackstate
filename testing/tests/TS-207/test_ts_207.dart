import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts207_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-207 resets Local Git create-form state after a successful save',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts207LocalGitFixture? fixture;

      const createdSummary = 'Issue 1';
      const solutionValue = 'Static analysis fix';

      try {
        fixture = await tester.runAsync(Ts207LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-207 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-207 requires a clean Local Git repository before opening '
              'Create issue, but `git status --short` returned '
              '${initialStatus.join(' | ')}.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          Ts207LocalGitFixture.existingIssueKey,
          Ts207LocalGitFixture.existingIssueSummary,
        );

        await _openCreateIssueFromJqlSearch(screen);
        await _expectCreateFormVisible(screen, failingStep: 1);
        await _expectCreateFieldVisible(
          screen,
          label: 'Solution',
          failingStep: 2,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Acceptance Criteria',
          failingStep: 2,
        );

        await screen.enterLabeledTextField('Summary', text: createdSummary);
        await screen.enterLabeledTextField('Solution', text: solutionValue);

        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          createdSummary,
          reason:
              'Step 2 failed: the Summary field did not keep the user-entered '
              '"$createdSummary" value before save.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Solution'),
          solutionValue,
          reason:
              'Step 2 failed: the Solution field did not keep the user-entered '
              '"$solutionValue" value before save.',
        );

        await screen.submitCreateIssue(createIssueSection: 'JQL Search');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));

        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isFalse,
          reason:
              'Step 3 failed: saving the new Local Git issue surfaced a save '
              'error instead of completing successfully. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'Step 3 failed: the Create issue dialog stayed open after save, '
              'so the success path was not completed.',
        );

        await screen.searchIssues(Ts207LocalGitFixture.createdIssueKey);
        await screen.expectIssueSearchResultVisible(
          Ts207LocalGitFixture.createdIssueKey,
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
        final createdMarkdown =
            await tester.runAsync(
              () => fixture!.readRepositoryFile(
                Ts207LocalGitFixture.createdIssuePath,
              ),
            ) ??
            '';
        expect(
          latestHead,
          isNot(initialHead),
          reason:
              'Step 3 failed: a successful Local Git create flow should append '
              'a new commit, but HEAD did not change.',
        );
        expect(
          latestParent,
          initialHead,
          reason:
              'Step 3 failed: the create commit should be written directly on '
              'top of the clean fixture HEAD.',
        );
        expect(
          latestSubject,
          'Create ${Ts207LocalGitFixture.createdIssueKey}',
          reason:
              'Step 3 failed: the latest Local Git commit should be dedicated '
              'to the create action.',
        );
        expect(
          latestFiles,
          equals([Ts207LocalGitFixture.createdIssuePath]),
          reason:
              'Step 3 failed: issue creation should commit only the new issue '
              'file. Observed files: ${latestFiles.join(' | ')}',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'Step 3 failed: successful Local Git issue creation should leave '
              'the worktree clean, but `git status --short` returned '
              '${finalStatus.join(' | ')}.',
        );
        expect(
          createdMarkdown,
          contains(createdSummary),
          reason:
              'Step 3 failed: ${Ts207LocalGitFixture.createdIssuePath} was '
              'created, but it did not contain the saved Summary value.\n'
              'Observed main.md:\n$createdMarkdown',
        );
        expect(
          createdMarkdown,
          contains(solutionValue),
          reason:
              'Step 3 failed: ${Ts207LocalGitFixture.createdIssuePath} was '
              'created, but it did not contain the saved Solution value.\n'
              'Observed main.md:\n$createdMarkdown',
        );

        await _openCreateIssueFromJqlSearch(screen);
        await _expectCreateFormVisible(screen, failingStep: 4);

        await _expectFieldCleared(screen, label: 'Summary', failingStep: 5);
        await _expectFieldCleared(screen, label: 'Description', failingStep: 5);
        await _expectFieldCleared(screen, label: 'Solution', failingStep: 5);
        await _expectFieldCleared(
          screen,
          label: 'Acceptance Criteria',
          failingStep: 5,
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

Future<void> _openCreateIssueFromJqlSearch(
  TrackStateAppComponent screen,
) async {
  await screen.openSection('JQL Search');
  final opened = await screen.tapVisibleControl('Create issue');
  if (opened) {
    return;
  }

  fail(
    'Step 1 failed: JQL Search did not expose a visible "Create issue" entry '
    'point. Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
    'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
}

Future<void> _expectCreateFormVisible(
  TrackStateAppComponent screen, {
  required int failingStep,
}) async {
  if (await screen.isTextFieldVisible('Summary')) {
    return;
  }

  fail(
    'Step $failingStep failed: opening the Local Git Create issue dialog did '
    'not render a visible "Summary" field. Visible texts: '
    '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
}

Future<void> _expectCreateFieldVisible(
  TrackStateAppComponent screen, {
  required String label,
  required int failingStep,
}) async {
  if (await screen.isTextFieldVisible(label)) {
    return;
  }

  fail(
    'Step $failingStep failed: the Local Git Create issue dialog did not '
    'render a visible "$label" field. Visible texts: '
    '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
}

Future<void> _expectFieldCleared(
  TrackStateAppComponent screen, {
  required String label,
  required int failingStep,
}) async {
  await _expectCreateFieldVisible(
    screen,
    label: label,
    failingStep: failingStep,
  );
  final value = await screen.readLabeledTextFieldValue(label);
  expect(
    value ?? '',
    isEmpty,
    reason:
        'Step $failingStep failed: the "$label" field still contained '
        '"${value ?? '<null>'}" after reopening the Create issue dialog '
        'following a successful save.',
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
