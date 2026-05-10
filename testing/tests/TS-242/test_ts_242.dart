import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts242_concurrent_active_index_fixture.dart';

void main() {
  testWidgets(
    'TS-242 deletes multiple issues concurrently and removes them from active search index',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts242ConcurrentActiveIndexFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-242 fixture creation did not complete.');
      }
      addTearDown(() async {
        await tester.runAsync(fixture.dispose);
      });

      const dependencies = defaultTestingDependencies;
      final LocalGitRepositoryPort repositoryPort = dependencies
          .createLocalGitRepositoryPort(tester);
      final beforeRepository = await repositoryPort.openRepository(
        repositoryPath: fixture.directory.path,
      );

      final beforeDeletion = await tester.runAsync(
        () => fixture.observeBeforeDeletionState(repository: beforeRepository),
      );
      if (beforeDeletion == null) {
        throw StateError('TS-242 pre-delete observation did not complete.');
      }

      // Human-style precondition: verify search returns all active issues
      expect(
        beforeDeletion.allVisibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        unorderedEquals(<String>[
          ...Ts242ConcurrentActiveIndexFixture.deleteIssueKeys,
          Ts242ConcurrentActiveIndexFixture.survivingIssueKey,
        ]),
        reason:
            'Human-style precondition: repository search should show all active issues before concurrent deletion.',
      );

      expect(
        beforeDeletion.activeIndexExists,
        isTrue,
        reason:
            'Precondition: ${beforeDeletion.activeIndexPath} must exist before concurrent deletion starts.',
      );

      final beforeIssueKeys = beforeDeletion.activeIndexJson
          .map((entry) => entry['key'])
          .whereType<String>()
          .toSet();
      expect(
        beforeIssueKeys,
        unorderedEquals(<String>{
          ...Ts242ConcurrentActiveIndexFixture.deleteIssueKeys,
          Ts242ConcurrentActiveIndexFixture.survivingIssueKey,
        }),
        reason:
            'Precondition: ${beforeDeletion.activeIndexPath} must include TRACK-4 and TRACK-5 delete targets before Step 1.',
      );

      expect(
        beforeDeletion.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition: the seeded repository must start clean, but git status returned ${beforeDeletion.worktreeStatusLines.join(' | ')}.',
      );

      // Step 1: Trigger concurrent delete operations
      final deletedTombstones = await tester.runAsync(
        () => fixture.deleteIssuesConcurrentlyViaRepositoryService(
          repository: beforeRepository,
        ),
      );
      if (deletedTombstones == null) {
        throw StateError('TS-242 concurrent delete workflow did not complete.');
      }

      // Step 1: Verify that delete operations returned tombstones for all issues
      expect(
        deletedTombstones.map((tombstone) => tombstone.key).toList(),
        unorderedEquals(Ts242ConcurrentActiveIndexFixture.deleteIssueKeys),
        reason:
            'Step 1: concurrent delete should return one tombstone result per deleted issue.',
      );

      // Step 2: Observe the post-deletion state
      final afterDeletionArtifacts = await tester.runAsync(
        fixture.observePostDeletionArtifacts,
      );
      if (afterDeletionArtifacts == null) {
        throw StateError(
          'TS-242 post-delete artifact observation did not complete.',
        );
      }

      // Step 2: Verify that issues.json no longer contains TRACK-4 or TRACK-5
      expect(
        afterDeletionArtifacts.activeIndexExists,
        isTrue,
        reason:
            'Expected: ${afterDeletionArtifacts.activeIndexPath} should still exist after concurrent deletion.',
      );

      final afterIssueKeys = afterDeletionArtifacts.activeIndexJson
          .map((entry) => entry['key'])
          .whereType<String>()
          .toSet();

      for (final deletedKey
          in Ts242ConcurrentActiveIndexFixture.deleteIssueKeys) {
        expect(
          afterIssueKeys,
          isNot(contains(deletedKey)),
          reason:
              'Expected Result: ${afterDeletionArtifacts.activeIndexPath} should no longer contain $deletedKey after concurrent deletion.',
        );
      }

      expect(
        afterIssueKeys,
        contains(Ts242ConcurrentActiveIndexFixture.survivingIssueKey),
        reason:
            'Expected Result: ${afterDeletionArtifacts.activeIndexPath} should still contain the surviving issue (${Ts242ConcurrentActiveIndexFixture.survivingIssueKey}).',
      );

      expect(
        afterDeletionArtifacts.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result: the concurrent delete workflow should leave the Git worktree clean, but git status returned ${afterDeletionArtifacts.worktreeStatusLines.join(' | ')}.',
      );

      // Reload repository and verify human-style search results
      final LocalGitRepositoryPort reloadedRepositoryPort = dependencies
          .createLocalGitRepositoryPort(tester);
      final afterRepository = await reloadedRepositoryPort.openRepository(
        repositoryPath: fixture.directory.path,
      );
      final afterDeletion = await tester.runAsync(
        () =>
            fixture.observeReloadedRepositoryState(repository: afterRepository),
      );
      if (afterDeletion == null) {
        throw StateError(
          'TS-242 post-delete repository reload did not complete.',
        );
      }

      // Human-style verification: search no longer returns deleted issues
      final afterSearchKeys = afterDeletion.allVisibleIssueSearchResults
          .map((issue) => issue.key)
          .toList();
      expect(
        afterSearchKeys,
        [Ts242ConcurrentActiveIndexFixture.survivingIssueKey],
        reason:
            'Human-style verification: repository search should show only the surviving issue after concurrent deletion.',
      );

      // Verify that the active index entries match search results
      final finalIndexKeys = afterDeletion.activeIndexJson
          .map((entry) => entry['key'])
          .whereType<String>()
          .toSet();
      expect(
        finalIndexKeys,
        unorderedEquals(afterSearchKeys.toSet()),
        reason:
            'Expected result: the active search index should be strictly tied to the existence of issues in the underlying Git tree.',
      );

      expect(
        afterDeletion.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result: the concurrent delete workflow should leave the Git worktree clean after reload, but git status returned ${afterDeletion.worktreeStatusLines.join(' | ')}.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
