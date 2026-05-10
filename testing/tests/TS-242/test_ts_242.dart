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
      final afterIssueKeys = afterDeletionArtifacts.activeIndexJson
          .map((entry) => entry['key'])
          .whereType<String>()
          .toSet();
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
      final afterSearchKeys = afterDeletion.allVisibleIssueSearchResults
          .map((issue) => issue.key)
          .toList();
      final finalIndexKeys = afterDeletion.activeIndexJson
          .map((entry) => entry['key'])
          .whereType<String>()
          .toSet();

      final failures = <String>[];

      if (!afterDeletionArtifacts.activeIndexExists) {
        failures.add(
          'Step 2 failed: ${afterDeletionArtifacts.activeIndexPath} should still exist after concurrent deletion.',
        );
      }

      for (final deletedKey
          in Ts242ConcurrentActiveIndexFixture.deleteIssueKeys) {
        if (afterIssueKeys.contains(deletedKey)) {
          failures.add(
            'Step 2 failed: ${afterDeletionArtifacts.activeIndexPath} still contained $deletedKey after concurrent deletion.',
          );
        }
      }

      if (!afterIssueKeys.contains(
        Ts242ConcurrentActiveIndexFixture.survivingIssueKey,
      )) {
        failures.add(
          'Step 2 failed: ${afterDeletionArtifacts.activeIndexPath} no longer contained the surviving issue (${Ts242ConcurrentActiveIndexFixture.survivingIssueKey}).',
        );
      }

      if (afterDeletionArtifacts.worktreeStatusLines.isNotEmpty) {
        failures.add(
          'Step 2 failed: the concurrent delete workflow left the Git worktree dirty before reload (${afterDeletionArtifacts.worktreeStatusLines.join(' | ')}).',
        );
      }

      if (!_sameKeys(afterSearchKeys.toSet(), <String>{
        Ts242ConcurrentActiveIndexFixture.survivingIssueKey,
      })) {
        failures.add(
          'Human-style verification failed: repository search after reload returned $afterSearchKeys instead of only ${Ts242ConcurrentActiveIndexFixture.survivingIssueKey}.',
        );
      }

      if (!_sameKeys(finalIndexKeys, afterSearchKeys.toSet())) {
        failures.add(
          'Expected result failed: the reloaded active search index keys $finalIndexKeys did not match the user-visible search results $afterSearchKeys.',
        );
      }

      if (afterDeletion.worktreeStatusLines.isNotEmpty) {
        failures.add(
          'Expected result failed: the concurrent delete workflow left the Git worktree dirty after reload (${afterDeletion.worktreeStatusLines.join(' | ')}).',
        );
      }

      if (failures.isNotEmpty) {
        fail(
          'Expected concurrent deletes to remove TRACK-4 and TRACK-5 from the active issues index and leave only TRACK-3 visible after reload. '
          '${failures.join(' ')} '
          '${_describePostDeleteState(afterDeletionArtifacts, afterDeletion)}',
        );
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

bool _sameKeys(Set<String> actual, Set<String> expected) =>
    actual.length == expected.length && actual.containsAll(expected);

String _describePostDeleteState(
  Ts242ConcurrentDeleteArtifactsObservation afterDeletionArtifacts,
  Ts242ConcurrentDeleteObservation afterDeletion,
) {
  final artifactIndexKeys = afterDeletionArtifacts.activeIndexJson
      .map((entry) => entry['key'])
      .whereType<String>()
      .toList(growable: false);
  final reloadedIndexKeys = afterDeletion.activeIndexJson
      .map((entry) => entry['key'])
      .whereType<String>()
      .toList(growable: false);
  final searchKeys = afterDeletion.allVisibleIssueSearchResults
      .map((issue) => issue.key)
      .toList(growable: false);
  return 'Observed artifactState(activeIndexExists=${afterDeletionArtifacts.activeIndexExists}, '
      'activeIndexKeys=$artifactIndexKeys, head=${afterDeletionArtifacts.headRevision}, '
      'worktreeStatus=${afterDeletionArtifacts.worktreeStatusLines}) '
      'and reloadedState(searchKeys=$searchKeys, activeIndexKeys=$reloadedIndexKeys, '
      'head=${afterDeletion.headRevision}, worktreeStatus=${afterDeletion.worktreeStatusLines}).';
}
