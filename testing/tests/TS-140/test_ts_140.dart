import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-140 creates an issue after the dirty repository state is resolved',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      LocalTrackStateFixture? fixture;

      const createdIssueKey = 'DEMO-2';
      const createdIssuePath = 'DEMO/DEMO-2/main.md';
      const createdSummary = 'TS-140 recovered dirty local issue';
      const createdDescription =
          'Created after stashing the dirty repository changes.';

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-140 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';

        await tester.runAsync(fixture.makeDirtyMainFileChange);
        final dirtyStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          dirtyStatus,
          contains('M ${LocalTrackStateFixture.issuePath}'),
          reason:
              'TS-140 requires a dirty worktree before the first create '
              'attempt, but `git status --short` returned '
              '${dirtyStatus.join(' | ')}.',
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
        await screen.expectMessageBannerContains('commit');
        await screen.expectMessageBannerContains('stash');
        await screen.expectMessageBannerContains('clean');
        expect(
          await screen.isTextFieldVisible('Summary'),
          isTrue,
          reason:
              'After the dirty-repository warning, the Create issue form should '
              'remain open so the user can resolve the filesystem state and '
              'retry without re-entering the details.',
        );

        await tester.runAsync(
          () =>
              fixture!.stashWorktreeChanges(message: 'TS-140 manual recovery'),
        );
        final cleanStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          cleanStatus,
          isEmpty,
          reason:
              'Stashing the manual filesystem edit should return the Local Git '
              'repository to a clean state before retrying creation, but '
              '`git status --short` returned ${cleanStatus.join(' | ')}.',
        );

        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));
        await screen.submitCreateIssue(createIssueSection: createIssueSection);
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));

        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'The create dialog should close after a successful retry, but '
              'the Summary field is still visible.',
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
              'Retrying issue creation after the repository is cleaned should '
              'append a new commit to history.',
        );
        expect(
          latestParent,
          initialHead,
          reason:
              'The successful retry should create exactly one new commit on top '
              'of the original fixture HEAD.',
        );
        expect(
          latestSubject,
          'Create $createdIssueKey',
          reason:
              'The successful retry should commit the created issue with the '
              'expected Local Git commit subject.',
        );
        expect(
          latestFiles,
          equals([createdIssuePath]),
          reason:
              'The successful retry should commit only the new issue file. '
              'Observed files: ${latestFiles.join(' | ')}',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'The repository should remain clean after successful issue '
              'creation, but `git status --short` returned '
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
