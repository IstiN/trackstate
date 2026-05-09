import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/repositories/ts194_deleted_issue_directory_fixture.dart';

void main() {
  test(
    'TS-194 deletes TRACK-122 by removing the full issue directory from storage',
    () async {
      final fixture = await Ts194DeletedIssueDirectoryFixture.create();
      addTearDown(fixture.dispose);

      final beforeDeletion = await fixture.observeBeforeDeletionState();

      expect(
        beforeDeletion.issueDirectoryExists,
        isTrue,
        reason:
            'Precondition failed: ${beforeDeletion.issueDirectoryPath}/ must exist before deleteIssue runs.',
      );
      expect(
        beforeDeletion.issueDirectoryEntries,
        ['attachment.txt', 'main.md'],
        reason:
            'Precondition failed: ${beforeDeletion.issueDirectoryPath}/ should start with both the markdown artifact and sibling attachment.',
      );
      expect(
        beforeDeletion.deletedIssueFileExists,
        isTrue,
        reason:
            'Precondition failed: ${beforeDeletion.deletedIssuePath} must exist before deleteIssue runs.',
      );
      expect(
        beforeDeletion.attachmentFileExists,
        isTrue,
        reason:
            'Precondition failed: ${beforeDeletion.attachmentPath} must exist before deleteIssue runs.',
      );
      expect(
        beforeDeletion.attachmentText,
        Ts194DeletedIssueDirectoryFixture.attachmentContents,
        reason:
            'Precondition failed: the sibling attachment should contain the seeded text before deletion.',
      );
      expect(
        beforeDeletion.tombstoneFileExists,
        isFalse,
        reason:
            'Precondition failed: ${beforeDeletion.tombstonePath} must not exist before deleteIssue runs.',
      );
      expect(
        beforeDeletion.tombstoneIndexExists,
        isFalse,
        reason:
            'Precondition failed: ${beforeDeletion.tombstoneIndexPath} must not exist before deleteIssue runs.',
      );
      expect(
        beforeDeletion.snapshot.repositoryIndex.pathForKey(
          Ts194DeletedIssueDirectoryFixture.deletedIssueKey,
        ),
        Ts194DeletedIssueDirectoryFixture.deletedIssuePath,
        reason:
            'Precondition failed: TRACK-122 should resolve to its active repository path before deletion.',
      );
      expect(
        beforeDeletion.deletedIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts194DeletedIssueDirectoryFixture.deletedIssueKey],
        reason:
            'Human-style precondition failed: TRACK-122 should be visible to repository consumers before deletion.',
      );
      expect(
        beforeDeletion.survivingIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts194DeletedIssueDirectoryFixture.survivingIssueKey],
        reason:
            'Human-style precondition failed: TRACK-123 should remain visible before deletion.',
      );
      expect(
        beforeDeletion.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must start clean, but git status returned ${beforeDeletion.worktreeStatusLines.join(' | ')}.',
      );

      final afterDeletion = await fixture.deleteIssueViaRepositoryService();

      expect(
        afterDeletion.deletedIssueFileExists,
        isFalse,
        reason:
            'Step 2 failed: deleting TRACK-122 should remove ${afterDeletion.deletedIssuePath} from storage.',
      );
      expect(
        afterDeletion.attachmentFileExists,
        isFalse,
        reason:
            'Step 2 failed: deleting TRACK-122 should remove ${afterDeletion.attachmentPath} from storage.',
      );
      expect(
        afterDeletion.issueDirectoryExists,
        isFalse,
        reason:
            'Step 3 failed: deleting TRACK-122 should remove the full ${afterDeletion.issueDirectoryPath}/ directory, but it still exists with entries ${_formatEntries(afterDeletion.issueDirectoryEntries)}.',
      );
      expect(
        afterDeletion.issueDirectoryEntries,
        isEmpty,
        reason:
            'Expected result mismatch: ${afterDeletion.issueDirectoryPath}/ should not contain orphaned artifacts after deletion, but found ${_formatEntries(afterDeletion.issueDirectoryEntries)}.',
      );
      expect(
        afterDeletion.tombstoneFileExists,
        isTrue,
        reason:
            'Expected result mismatch: deleting TRACK-122 should create ${afterDeletion.tombstonePath}.',
      );
      expect(
        afterDeletion.tombstoneJson,
        isNotNull,
        reason:
            'Expected result mismatch: the tombstone artifact should contain deletion metadata.',
      );
      expect(
        afterDeletion.tombstoneJson?['key'],
        Ts194DeletedIssueDirectoryFixture.deletedIssueKey,
      );
      expect(
        afterDeletion.tombstoneJson?['formerPath'],
        Ts194DeletedIssueDirectoryFixture.deletedIssuePath,
      );
      expect(afterDeletion.tombstoneJson?['project'], 'TRACK');
      expect(afterDeletion.tombstoneJson?['deletedAt'], isNotEmpty);
      expect(
        afterDeletion.tombstoneIndexExists,
        isTrue,
        reason:
            'Expected result mismatch: deleting TRACK-122 should create ${afterDeletion.tombstoneIndexPath}.',
      );
      expect(
        afterDeletion.tombstoneIndexJson,
        contains(
          allOf(
            containsPair(
              'key',
              Ts194DeletedIssueDirectoryFixture.deletedIssueKey,
            ),
            containsPair(
              'path',
              Ts194DeletedIssueDirectoryFixture.tombstonePath,
            ),
          ),
        ),
        reason:
            'Expected result mismatch: the tombstone index must reserve TRACK-122 after deletion.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.pathForKey(
          Ts194DeletedIssueDirectoryFixture.deletedIssueKey,
        ),
        isNull,
        reason:
            'Expected result mismatch: TRACK-122 should be removed from the active repository index after deletion.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.deleted.map(
          (entry) => entry.key,
        ),
        contains(Ts194DeletedIssueDirectoryFixture.deletedIssueKey),
        reason:
            'Expected result mismatch: TRACK-122 should be reserved in deleted-key metadata after deletion.',
      );
      expect(
        afterDeletion.deletedIssueSearchResults,
        isEmpty,
        reason:
            'Human-style verification failed: TRACK-122 should disappear from repository search results after deletion.',
      );
      expect(
        afterDeletion.survivingIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts194DeletedIssueDirectoryFixture.survivingIssueKey],
        reason:
            'Human-style verification failed: deleting TRACK-122 must not remove TRACK-123 from repository search results.',
      );
      expect(
        afterDeletion.latestCommitSubject,
        'Delete ${Ts194DeletedIssueDirectoryFixture.deletedIssueKey} and reserve tombstone',
        reason:
            'Expected result mismatch: the delete workflow should commit the standard tombstone message.',
      );
      expect(
        afterDeletion.headRevision,
        isNot(beforeDeletion.headRevision),
        reason:
            'Expected result mismatch: a successful delete should create a new Git revision.',
      );
      expect(
        afterDeletion.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: the delete workflow should leave the repository worktree clean, but git status returned ${afterDeletion.worktreeStatusLines.join(' | ')}.',
      );
    },
  );

  testWidgets(
    'TS-194 hides the deleted issue from visible JQL Search results',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts194DeletedIssueDirectoryFixture? fixture;

      try {
        fixture = await tester.runAsync(
          Ts194DeletedIssueDirectoryFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-194 fixture creation did not complete.');
        }

        await tester.runAsync(fixture.deleteIssueViaRepositoryService);
        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Launching the app after deleting TRACK-122 should not surface a framework exception.',
        );

        await screen.openSection('JQL Search');
        await screen.searchIssues('project = TRACK');
        screen.expectIssueSearchResultAbsent(
          Ts194DeletedIssueDirectoryFixture.deletedIssueKey,
          'Delete target issue',
        );
        await screen.expectIssueSearchResultVisible(
          Ts194DeletedIssueDirectoryFixture.survivingIssueKey,
          'Surviving issue',
        );
        expect(
          tester.takeException(),
          isNull,
          reason:
              'The real JQL Search flow should hide TRACK-122 and keep TRACK-123 visible after deletion.',
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
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

String _formatEntries(List<String> entries) {
  if (entries.isEmpty) {
    return '<none>';
  }
  return entries.join(' | ');
}
