import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-123 creates an issue successfully in a clean Local Git repository',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      LocalTrackStateFixture? fixture;

      const createdIssueKey = 'DEMO-2';
      const createdIssuePath = 'DEMO/DEMO-2/main.md';
      const createdSummary = 'TS-123 clean local issue';
      const createdDescription =
          'Created through the clean Local Git issue creation flow.';

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-123 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-123 requires a clean Local Git repository before the user '
              'opens Create issue, but `git status --short` returned '
              '${initialStatus.join(' | ')}.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          LocalTrackStateFixture.issueKey,
          LocalTrackStateFixture.issueSummary,
        );

        final createIssueSection = await screen.openCreateIssueFlow();
        await screen.expectCreateIssueFormVisible(
          createIssueSection: createIssueSection,
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
              'A clean repository should not show the dirty-repository failure '
              'banner after issue creation. Visible texts: '
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
              'Successful Local Git issue creation should add a new commit to '
              'history.',
        );
        expect(
          latestParent,
          initialHead,
          reason:
              'The create commit should be appended directly on top of the '
              'clean fixture HEAD.',
        );
        expect(
          latestSubject,
          'Create $createdIssueKey',
          reason:
              'The latest Local Git commit should be dedicated to the issue '
              'creation action.',
        );
        expect(
          latestFiles,
          equals([createdIssuePath]),
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
