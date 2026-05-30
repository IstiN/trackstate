import 'dart:convert';

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
    'TS-189 creates a Local Git issue from the JQL Search toolbar with configured custom fields',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts141LocalGitFixture? fixture;

      const createdSummary = 'TS-189 JQL Search toolbar custom fields persist';
      const createdDescription =
          'Created specifically from the JQL Search toolbar and verified through the user-facing search flow.';
      const solutionValue =
          'Render project-configured custom fields when the create dialog starts from JQL Search.';
      const acceptanceCriteriaValue =
          '- JQL Search shows a visible Create issue control.\n- Solution, Acceptance Criteria, and Diagrams are editable.\n- DEMO/DEMO-2/main.md stores every entered value.';
      const diagramsValue =
          'sequenceDiagram\nJQLSearch->>CreateIssue: Open toolbar action';

      try {
        fixture = await tester.runAsync(Ts141LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-189 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-189 requires a clean Local Git repository before opening '
              'Create issue from JQL Search, but `git status --short` returned '
              '${initialStatus.join(' | ')}.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          Ts141LocalGitFixture.existingIssueKey,
          Ts141LocalGitFixture.existingIssueSummary,
        );

        await _expectTopBarControlVisible(
          screen,
          label: 'Create issue',
          failingStep: 2,
          context: 'while viewing JQL Search in Local Git mode',
        );

        final openedFromJqlSearch = await screen.tapTopBarControl(
          'Create issue',
        );
        expect(
          openedFromJqlSearch,
          isTrue,
          reason:
              'Step 2 failed: the visible JQL Search toolbar "Create issue" '
              'control could not be activated. Top bar texts: '
              '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
              'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.expectCreateIssueFormVisible(
          createIssueSection: 'JQL Search',
        );
        await _expectVisibleControl(
          screen,
          label: 'Save',
          failingStep: 3,
          context: 'inside the JQL Search create dialog',
        );
        await _expectVisibleControl(
          screen,
          label: 'Cancel',
          failingStep: 3,
          context: 'inside the JQL Search create dialog',
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Solution',
          createIssueSection: 'JQL Search',
          failingStep: 3,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Acceptance Criteria',
          createIssueSection: 'JQL Search',
          failingStep: 3,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Diagrams',
          createIssueSection: 'JQL Search',
          failingStep: 3,
        );

        await screen.populateCreateIssueForm(
          summary: createdSummary,
          description: createdDescription,
        );
        await screen.enterLabeledTextField('Solution', text: solutionValue);
        await screen.enterLabeledTextField(
          'Acceptance Criteria',
          text: acceptanceCriteriaValue,
        );
        await screen.enterLabeledTextField('Diagrams', text: diagramsValue);

        final saved = await screen.tapVisibleControl('Save');
        expect(
          saved,
          isTrue,
          reason:
              'Step 6 failed: the JQL Search create dialog showed a visible '
              '"Save" action, but the automation could not activate it. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));

        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isFalse,
          reason:
              'Step 6 failed: saving a valid issue from the JQL Search toolbar '
              'showed a user-visible save failure banner. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'Step 6 failed: after saving from the JQL Search toolbar, the '
              'create dialog stayed open with the Summary field still visible.',
        );

        await screen.openSection('JQL Search');
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
        final createdMarkdown =
            await tester.runAsync(
              () => fixture!.readRepositoryFile(
                Ts141LocalGitFixture.createdIssuePath,
              ),
            ) ??
            '';
        final createdCustomFields = _decodeCustomFields(createdMarkdown);

        expect(
          latestHead,
          isNot(initialHead),
          reason:
              'Successful JQL Search Local Git issue creation should append a '
              'new commit to history.',
        );
        expect(
          latestParent,
          initialHead,
          reason:
              'The JQL Search create commit should be appended directly on top '
              'of the clean fixture HEAD.',
        );
        expect(
          latestSubject,
          'Create ${Ts141LocalGitFixture.createdIssueKey}',
          reason:
              'The latest Local Git commit should be dedicated to the JQL '
              'Search issue creation action.',
        );
        expect(
          latestFiles,
          equals([Ts141LocalGitFixture.createdIssuePath]),
          reason:
              'Issue creation from JQL Search should commit only the new issue '
              'file. Observed files: ${latestFiles.join(' | ')}',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'Successful JQL Search issue creation should leave the worktree '
              'clean, but `git status --short` returned '
              '${finalStatus.join(' | ')}.',
        );
        expect(
          createdMarkdown,
          contains(createdSummary),
          reason:
              'Step 7 failed: DEMO/DEMO-2/main.md did not contain the entered '
              'Summary.\nObserved main.md:\n$createdMarkdown',
        );
        expect(
          createdMarkdown,
          contains(createdDescription),
          reason:
              'Step 7 failed: DEMO/DEMO-2/main.md did not contain the entered '
              'Description.\nObserved main.md:\n$createdMarkdown',
        );
        expect(
          createdCustomFields['solution'],
          solutionValue,
          reason:
              'Step 7 failed: DEMO/DEMO-2/main.md did not persist the entered '
              'Solution value in customFields.\nObserved main.md:\n$createdMarkdown',
        );
        expect(
          createdCustomFields['acceptanceCriteria'],
          acceptanceCriteriaValue,
          reason:
              'Step 7 failed: DEMO/DEMO-2/main.md did not persist the entered '
              'Acceptance Criteria value in customFields.\nObserved main.md:\n$createdMarkdown',
        );
        expect(
          createdCustomFields['diagrams'],
          diagramsValue,
          reason:
              'Step 7 failed: DEMO/DEMO-2/main.md did not persist the entered '
              'Diagrams value in customFields.\nObserved main.md:\n$createdMarkdown',
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

Future<void> _expectTopBarControlVisible(
  TrackStateAppComponent screen, {
  required String label,
  required int failingStep,
  required String context,
}) async {
  final topBarVisible =
      await screen.isTopBarSemanticsLabelVisible(label) ||
      await screen.isTopBarTextVisible(label);
  if (topBarVisible) {
    return;
  }
  fail(
    'Step $failingStep failed: no visible "$label" control was rendered in '
    'the top bar $context. Top bar texts: '
    '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible texts: '
    '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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

Map<String, dynamic> _decodeCustomFields(String markdown) {
  final match = RegExp(
    r'^customFields:\s*(\{.*\})$',
    multiLine: true,
  ).firstMatch(markdown);
  if (match == null) {
    fail(
      'Step 7 failed: DEMO/DEMO-2/main.md did not contain a customFields '
      'frontmatter entry.\nObserved main.md:\n$markdown',
    );
  }

  final decoded = jsonDecode(match.group(1)!) as Map<String, dynamic>;
  return decoded;
}
