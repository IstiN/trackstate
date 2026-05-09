import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-183 creates a Local Git issue successfully from the Board view',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      const createdIssueKey = 'DEMO-2';
      const createdIssuePath = 'DEMO/DEMO-2/main.md';
      const createdSummary = 'TS-183 board create flow persists issue';
      const createdDescription =
          'Created from the Board view and verified through JQL Search.';

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-183 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'Precondition failed: TS-183 requires a clean Local Git '
              'repository before opening the Board create flow, but '
              '`git status --short` returned ${initialStatus.join(' | ')}.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Board');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        await _expectVisibleControl(
          screen,
          label: 'Create issue',
          failingStep: 2,
          context: 'after navigating to the Board section in Local Git mode',
        );

        final openedFromBoard = await screen.tapVisibleControl('Create issue');
        expect(
          openedFromBoard,
          isTrue,
          reason:
              'Step 2 failed: the visible "Create issue" control in Board '
              'could not be activated. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.expectCreateIssueFormVisible(createIssueSection: 'Board');
        await _expectTextFieldVisible(
          screen,
          label: 'Description',
          failingStep: 3,
          context: 'after opening Create issue from Board',
        );
        await _expectVisibleControl(
          screen,
          label: 'Save',
          failingStep: 4,
          context: 'inside the Board-origin Create issue dialog',
        );
        await _expectVisibleControl(
          screen,
          label: 'Cancel',
          failingStep: 4,
          context: 'inside the Board-origin Create issue dialog',
        );

        await screen.populateCreateIssueForm(
          summary: createdSummary,
          description: createdDescription,
        );

        final saved = await screen.tapVisibleControl('Save');
        expect(
          saved,
          isTrue,
          reason:
              'Step 4 failed: the Create issue dialog displayed a visible '
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
              'Step 4 failed: saving a valid issue from the Board view showed '
              'a user-visible save failure banner. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'Step 4 failed: after saving from the Board view, the create '
              'dialog stayed open with the Summary field still visible.',
        );

        await screen.openSection('JQL Search');
        await screen.searchIssues(createdIssueKey);
        await screen.expectIssueSearchResultVisible(
          createdIssueKey,
          createdSummary,
        );
        await screen.openIssue(createdIssueKey, createdSummary);
        await screen.expectIssueDetailVisible(createdIssueKey);
        await screen.expectIssueDetailText(createdIssueKey, createdSummary);

        final latestHead = await tester.runAsync(fixture.headRevision) ?? '';
        final latestParent = await tester.runAsync(fixture.parentOfHead) ?? '';
        final latestSubject =
            await tester.runAsync(fixture.latestCommitSubject) ?? '';
        final latestFiles =
            await tester.runAsync(fixture.latestCommitFiles) ?? <String>[];
        final finalStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final createdMarkdown = await tester.runAsync(
          () => fixture!.readRepositoryFile(createdIssuePath),
        );

        expect(
          latestHead,
          isNot(initialHead),
          reason:
              'Expected the Board-origin Local Git create flow to append a new '
              'commit, but HEAD did not change.',
        );
        expect(
          latestParent,
          initialHead,
          reason:
              'Expected the new create commit to be written directly on top of '
              'the clean fixture HEAD.',
        );
        expect(
          latestSubject,
          'Create $createdIssueKey',
          reason:
              'Expected the Board-origin create flow to persist the new issue '
              'with the dedicated Local Git create commit subject.',
        );
        expect(
          latestFiles,
          equals([createdIssuePath]),
          reason:
              'Expected the Local Git storage layer to persist only the new '
              'issue file for TS-183. Observed files: ${latestFiles.join(' | ')}',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'Expected the Local Git worktree to remain clean after successful '
              'Board issue creation, but `git status --short` returned '
              '${finalStatus.join(' | ')}.',
        );
        expect(createdMarkdown, contains('key: $createdIssueKey'));
        expect(createdMarkdown, contains('summary: "$createdSummary"'));
        expect(createdMarkdown, contains('# Summary'));
        expect(createdMarkdown, contains(createdSummary));
        expect(createdMarkdown, contains('# Description'));
        expect(createdMarkdown, contains(createdDescription));
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

Future<void> _expectTextFieldVisible(
  TrackStateAppComponent screen, {
  required String label,
  required int failingStep,
  required String context,
}) async {
  if (await screen.isTextFieldVisible(label)) {
    return;
  }
  fail(
    'Step $failingStep failed: no visible "$label" field was rendered '
    '$context. Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
    'Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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
