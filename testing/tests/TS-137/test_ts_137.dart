import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts137_missing_issue_delete_fixture.dart';

void main() {
  test(
    'TS-137 rejects a missing issue delete without writing tombstones or dirtying the repository',
    () async {
      final fixture = await Ts137MissingIssueDeleteFixture.create();
      addTearDown(fixture.dispose);

      final beforeDeletion = await fixture.observeBeforeDeletionState();

      expect(
        beforeDeletion.missingIssueFileExists,
        isFalse,
        reason:
            '${Ts137MissingIssueDeleteFixture.missingIssueKey} must be absent before the delete attempt begins.',
      );
      expect(
        beforeDeletion.tombstoneDirectoryExists,
        isFalse,
        reason:
            'The repository should not contain ${beforeDeletion.tombstoneDirectoryPath} before the delete attempt.',
      );
      expect(
        beforeDeletion.tombstoneFileExists,
        isFalse,
        reason:
            'The repository should not contain ${beforeDeletion.tombstonePath} before the delete attempt.',
      );
      expect(
        beforeDeletion.tombstoneIndexExists,
        isFalse,
        reason:
            'The repository should not contain ${beforeDeletion.tombstoneIndexPath} before the delete attempt.',
      );
      expect(
        beforeDeletion.snapshot.repositoryIndex.deleted,
        isEmpty,
        reason:
            'No deleted-key reservation should exist before the missing delete is attempted.',
      );
      expect(
        beforeDeletion.snapshot.repositoryIndex.pathForKey(
          Ts137MissingIssueDeleteFixture.missingIssueKey,
        ),
        isNull,
        reason:
            'A non-existent issue must not appear in the active repository index before deletion.',
      );
      expect(
        beforeDeletion.snapshot.repositoryIndex.pathForKey(
          Ts137MissingIssueDeleteFixture.survivingIssueKey,
        ),
        Ts137MissingIssueDeleteFixture.survivingIssuePath,
        reason:
            'TRACK-122 should resolve to its active repository file before the missing delete attempt.',
      );
      expect(
        beforeDeletion.missingIssueSearchResults,
        isEmpty,
        reason:
            'Searching for ${Ts137MissingIssueDeleteFixture.missingIssueKey} should return no active issues before deletion.',
      );
      expect(
        beforeDeletion.activeIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts137MissingIssueDeleteFixture.survivingIssueKey],
        reason:
            'TRACK-122 should remain searchable before the missing delete attempt.',
      );
      expect(
        beforeDeletion.worktreeStatusLines,
        isEmpty,
        reason:
            'The seeded repository must start clean so the delete attempt is the only possible source of changes.',
      );

      final afterDeletion = await fixture
          .deleteMissingIssueViaRepositoryService();

      expect(
        afterDeletion.errorMessage,
        'Could not find repository artifacts for ${Ts137MissingIssueDeleteFixture.missingIssueKey}.',
        reason:
            'Deleting a missing issue should surface the repository-service not-found error exactly.',
      );
      expect(
        afterDeletion.missingIssueFileExists,
        isFalse,
        reason:
            'The failed delete must not create or restore ${afterDeletion.missingIssuePath}.',
      );
      expect(
        afterDeletion.tombstoneDirectoryExists,
        isFalse,
        reason:
            'The failed delete must not create ${afterDeletion.tombstoneDirectoryPath}.',
      );
      expect(
        afterDeletion.tombstoneFileExists,
        isFalse,
        reason:
            'The failed delete must not create ${afterDeletion.tombstonePath}.',
      );
      expect(
        afterDeletion.tombstoneIndexExists,
        isFalse,
        reason:
            'The failed delete must not create ${afterDeletion.tombstoneIndexPath}.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.deleted,
        isEmpty,
        reason:
            'The failed delete must not reserve ${Ts137MissingIssueDeleteFixture.missingIssueKey} in deleted-key metadata.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.pathForKey(
          Ts137MissingIssueDeleteFixture.missingIssueKey,
        ),
        isNull,
        reason:
            'A missing issue must still be absent from the active repository index after the failed delete.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.pathForKey(
          Ts137MissingIssueDeleteFixture.survivingIssueKey,
        ),
        Ts137MissingIssueDeleteFixture.survivingIssuePath,
        reason:
            'The failed delete must not disturb TRACK-122 in the active repository index.',
      );
      expect(
        afterDeletion.missingIssueSearchResults,
        isEmpty,
        reason:
            'Searching for ${Ts137MissingIssueDeleteFixture.missingIssueKey} should still return no active issues after the failed delete.',
      );
      expect(
        afterDeletion.activeIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts137MissingIssueDeleteFixture.survivingIssueKey],
        reason:
            'TRACK-122 must remain searchable after the missing delete attempt fails.',
      );
      expect(
        afterDeletion.survivingIssueMarkdown,
        beforeDeletion.survivingIssueMarkdown,
        reason:
            'The failed delete must not rewrite ${afterDeletion.survivingIssuePath}.',
      );
      expect(
        afterDeletion.headRevision,
        beforeDeletion.headRevision,
        reason: 'The failed delete must not create a new Git commit.',
      );
      expect(
        afterDeletion.worktreeStatusLines,
        isEmpty,
        reason:
            'The failed delete must leave the Git worktree clean, but `git status --short` returned ${afterDeletion.worktreeStatusLines.join(' | ')}.',
      );
    },
  );
}
