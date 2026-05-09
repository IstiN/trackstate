import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts215_concurrent_legacy_deleted_index_fixture.dart';

void main() {
  testWidgets(
    'TS-241 deletes multiple issues concurrently and preserves every tombstone index entry',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts215ConcurrentLegacyDeletedIndexFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-241 fixture creation did not complete.');
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
        throw StateError('TS-241 pre-delete observation did not complete.');
      }

      expect(
        beforeDeletion.tombstoneIndexExists,
        isFalse,
        reason:
            'Precondition failed: ${beforeDeletion.tombstoneIndexPath} must not exist before concurrent deletion starts.',
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
            'Human-style precondition failed: repository search should show every active issue before concurrent deletion starts.',
      );

      final deletedTombstones = await tester.runAsync(
        () => fixture.deleteIssuesConcurrentlyViaRepositoryService(
          repository: beforeRepository,
        ),
      );
      if (deletedTombstones == null) {
        throw StateError('TS-241 concurrent delete workflow did not complete.');
      }

      final afterDeletionArtifacts = await tester.runAsync(
        fixture.observePostDeletionArtifacts,
      );
      if (afterDeletionArtifacts == null) {
        throw StateError(
          'TS-241 post-delete artifact observation did not complete.',
        );
      }

      expect(
        deletedTombstones.map((tombstone) => tombstone.key).toList(),
        unorderedEquals(Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys),
        reason:
            'Step 1 failed: concurrent delete should return one tombstone result per deleted issue.',
      );
      expect(
        afterDeletionArtifacts.tombstoneIndexExists,
        isTrue,
        reason:
            'Step 3 failed: ${afterDeletionArtifacts.tombstoneIndexPath} was not created after concurrent deletion completed.',
      );
      expect(
        afterDeletionArtifacts.tombstoneIndexJson.length,
        Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys.length,
        reason:
            'Step 3 failed: ${afterDeletionArtifacts.tombstoneIndexPath} should contain one entry for each deleted issue.',
      );
      expect(
        afterDeletionArtifacts.tombstoneIndexJson
            .map((entry) => entry['key'])
            .whereType<String>()
            .toList(),
        unorderedEquals(Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys),
        reason:
            'Step 3 failed: ${afterDeletionArtifacts.tombstoneIndexPath} is missing one or more deleted issue keys after concurrent deletion.',
      );
      expect(
        afterDeletionArtifacts.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: concurrent deletion should leave a clean git worktree, but got ${afterDeletionArtifacts.worktreeStatusLines.join(' | ')}.',
      );

      for (final key
          in Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys) {
        final target = afterDeletionArtifacts.target(key);
        expect(
          target.issueFileExists,
          isFalse,
          reason:
              'Step 2 failed: deleting $key concurrently should remove ${target.issuePath}.',
        );
        expect(
          target.tombstoneFileExists,
          isTrue,
          reason:
              'Step 3 failed: deleting $key concurrently should create ${target.tombstonePath}.',
        );
        expect(
          target.tombstoneJson?['key'],
          key,
          reason:
              'Step 3 failed: ${target.tombstonePath} did not preserve the deleted issue key for $key.',
        );
      }

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
          'TS-241 post-delete repository reload did not complete.',
        );
      }

      expect(
        afterDeletion.allVisibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts215ConcurrentLegacyDeletedIndexFixture.survivingIssueKey],
        reason:
            'Human-style verification failed: repository search should show only the surviving issue after concurrent deletion.',
      );
      for (final key
          in Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys) {
        final target = afterDeletion.target(key);
        expect(
          target.searchResults,
          isEmpty,
          reason:
              'Human-style verification failed: searching for $key should return no visible issues after concurrent deletion.',
        );
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
