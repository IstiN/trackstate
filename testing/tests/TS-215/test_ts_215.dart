import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts215_concurrent_legacy_deleted_index_fixture.dart';

void main() {
  test(
    'TS-215 deletes multiple issues concurrently without mutating the legacy deleted index',
    () async {
      final fixture = await Ts215ConcurrentLegacyDeletedIndexFixture.create();
      addTearDown(fixture.dispose);

      final beforeDeletion = await fixture.observeBeforeDeletionState();

      expect(
        beforeDeletion.legacyDeletedIndexExists,
        isTrue,
        reason:
            'Step 1 failed: ${beforeDeletion.legacyDeletedIndexPath} must exist before the concurrent delete workflow begins.',
      );
      expect(
        beforeDeletion.legacyDeletedIndexContent,
        Ts215ConcurrentLegacyDeletedIndexFixture.legacyDeletedIndexContent,
        reason:
            'Step 1 failed: the legacy deleted index must start with a known payload so the post-delete comparison is meaningful.',
      );
      expect(
        beforeDeletion.tombstoneIndexExists,
        isFalse,
        reason:
            'Precondition failed: ${beforeDeletion.tombstoneIndexPath} must not exist before the concurrent delete workflow runs.',
      );
      expect(
        beforeDeletion.allVisibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        unorderedEquals(<String>[
          ...Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys,
          Ts215ConcurrentLegacyDeletedIndexFixture.survivingIssueKey,
        ]),
        reason:
            'Human-style precondition failed: repository search should show all active issues before the concurrent delete workflow starts.',
      );
      expect(
        beforeDeletion.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must start clean, but git status returned ${beforeDeletion.worktreeStatusLines.join(' | ')}.',
      );

      for (final key in Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys) {
        final target = beforeDeletion.target(key);
        expect(
          target.issueFileExists,
          isTrue,
          reason:
              'Precondition failed: ${target.issuePath} must exist before Step 2 triggers concurrent deletion.',
        );
        expect(
          target.tombstoneFileExists,
          isFalse,
          reason:
              'Precondition failed: ${target.tombstonePath} must not exist before Step 2 triggers concurrent deletion.',
        );
        expect(
          target.searchResults.map((issue) => issue.key).toList(),
          [key],
          reason:
              'Human-style precondition failed: repository search should show $key before Step 2 triggers concurrent deletion.',
        );
      }

      final afterDeletion = await fixture
          .deleteIssuesConcurrentlyViaRepositoryService();

      expect(
        afterDeletion.headRevision,
        isNot(beforeDeletion.headRevision),
        reason:
            'Step 2 failed: the concurrent delete workflow should persist repository changes and move HEAD to a new revision.',
      );
      expect(
        afterDeletion.tombstoneIndexExists,
        isTrue,
        reason:
            'Step 3 failed: ${afterDeletion.tombstoneIndexPath} was not created after the concurrent delete workflow completed.',
      );
      expect(
        afterDeletion.tombstoneIndexJson.length,
        Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys.length,
        reason:
            'Step 3 failed: ${afterDeletion.tombstoneIndexPath} should contain exactly one tombstone entry per deleted issue, but found ${afterDeletion.tombstoneIndexJson.length} entries.',
      );
      expect(
        afterDeletion.tombstoneIndexJson
            .map((entry) => entry['key'])
            .whereType<String>()
            .toList(),
        unorderedEquals(Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys),
        reason:
            'Step 3 failed: ${afterDeletion.tombstoneIndexPath} does not list the expected deleted issue keys.',
      );
      expect(
        afterDeletion.legacyDeletedIndexExists,
        isTrue,
        reason:
            'Step 4 failed: ${afterDeletion.legacyDeletedIndexPath} was removed by the concurrent delete workflow.',
      );
      expect(
        afterDeletion.legacyDeletedIndexContent,
        beforeDeletion.legacyDeletedIndexContent,
        reason:
            'Step 4 failed: ${afterDeletion.legacyDeletedIndexPath} changed during concurrent deletion.\n${_describeLegacyIndexMutation(beforeDeletion, afterDeletion)}',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.deleted
            .map((entry) => entry.key)
            .toSet(),
        containsAll(<String>{
          Ts215ConcurrentLegacyDeletedIndexFixture.legacyDeletedIssueKey,
          ...Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys,
        }),
        reason:
            'Expected result mismatch: repository consumers should still reserve the legacy deleted key and all newly deleted keys after the concurrent workflow completes.',
      );
      expect(
        afterDeletion.allVisibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts215ConcurrentLegacyDeletedIndexFixture.survivingIssueKey],
        reason:
            'Human-style verification failed: repository search should show only the surviving issue after the concurrent delete workflow completes.',
      );
      expect(
        afterDeletion.survivingIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts215ConcurrentLegacyDeletedIndexFixture.survivingIssueKey],
        reason:
            'Human-style verification failed: searching for the surviving issue should still return ${Ts215ConcurrentLegacyDeletedIndexFixture.survivingIssueKey} after concurrent deletion.',
      );
      expect(
        afterDeletion.survivingIssueSearchResults.single.summary,
        'Surviving issue',
        reason:
            'Human-style verification failed: the surviving issue should still expose its visible summary after the concurrent delete workflow completes.',
      );
      expect(
        afterDeletion.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: the concurrent delete workflow should leave the Git worktree clean, but git status returned ${afterDeletion.worktreeStatusLines.join(' | ')}.',
      );

      for (final key in Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys) {
        final target = afterDeletion.target(key);
        expect(
          target.issueFileExists,
          isFalse,
          reason:
              'Step 2 failed: deleting $key concurrently should remove ${target.issuePath} from active storage.',
        );
        expect(
          target.tombstoneFileExists,
          isTrue,
          reason:
              'Step 3 failed: deleting $key concurrently should create ${target.tombstonePath}.',
        );
        expect(
          target.tombstoneJson,
          isNotNull,
          reason:
              'Step 3 failed: ${target.tombstonePath} exists but did not contain deletion metadata for $key.',
        );
        expect(
          target.tombstoneJson?['key'],
          key,
          reason:
              'Step 3 failed: ${target.tombstonePath} did not record the expected deleted issue key.',
        );
        expect(
          target.tombstoneJson?['formerPath'],
          target.issuePath,
          reason:
              'Step 3 failed: ${target.tombstonePath} did not preserve the expected formerPath for $key.',
        );
        expect(
          target.tombstoneJson?['project'],
          Ts215ConcurrentLegacyDeletedIndexFixture.projectKey,
          reason:
              'Step 3 failed: ${target.tombstonePath} did not preserve the project key for $key.',
        );
        expect(
          target.tombstoneJson?['summary'],
          target.summary,
          reason:
              'Step 3 failed: ${target.tombstonePath} did not preserve the visible summary for $key.',
        );
        expect(
          () => DateTime.parse(target.tombstoneJson!['deletedAt']! as String),
          returnsNormally,
          reason:
              'Step 3 failed: ${target.tombstonePath} did not store a valid ISO-8601 deletedAt timestamp for $key.',
        );
        expect(
          target.searchResults,
          isEmpty,
          reason:
              'Human-style verification failed: repository search should no longer return $key after the concurrent delete workflow completes.',
        );
        expect(
          afterDeletion.snapshot.repositoryIndex.pathForKey(key),
          isNull,
          reason:
              'Expected result mismatch: the active repository index should no longer resolve $key after concurrent deletion.',
        );
      }
    },
  );
}

String _describeLegacyIndexMutation(
  Ts215ConcurrentDeleteObservation beforeDeletion,
  Ts215ConcurrentDeleteObservation afterDeletion,
) {
  final beforeContent = beforeDeletion.legacyDeletedIndexContent?.replaceAll(
    '\n',
    r'\n',
  );
  final afterContent = afterDeletion.legacyDeletedIndexContent?.replaceAll(
    '\n',
    r'\n',
  );
  return 'beforeExists=${beforeDeletion.legacyDeletedIndexExists}, '
      'afterExists=${afterDeletion.legacyDeletedIndexExists}, '
      'beforeContent=$beforeContent, '
      'afterContent=$afterContent';
}
