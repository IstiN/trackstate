import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts215_concurrent_legacy_deleted_index_fixture.dart';

void main() {
  testWidgets(
    'TS-243 deletes multiple issues concurrently and verifies repository reload and search remain functional',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts215ConcurrentLegacyDeletedIndexFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-243 fixture creation did not complete.');
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

      // Precondition: Verify initial state with active issues
      final beforeSnapshot = await tester.runAsync(
        () => fixture.observeBeforeDeletionState(repository: beforeRepository),
      );
      if (beforeSnapshot == null) {
        throw StateError('TS-243 pre-delete observation did not complete.');
      }

      expect(
        beforeSnapshot.allVisibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        unorderedEquals(<String>[
          ...Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys,
          Ts215ConcurrentLegacyDeletedIndexFixture.survivingIssueKey,
        ]),
        reason:
            'Precondition failed: repository should show all active issues before the concurrent delete workflow starts.',
      );

      // Step 1: Perform stress test with concurrent delete operations
      final deletedTombstones = await tester.runAsync(
        () => fixture.deleteIssuesConcurrentlyViaRepositoryService(
          repository: beforeRepository,
        ),
      );
      if (deletedTombstones == null) {
        throw StateError('TS-243 concurrent delete workflow did not complete.');
      }

      expect(
        deletedTombstones.isNotEmpty,
        isTrue,
        reason: 'Step 1 failed: concurrent delete should return tombstone results.',
      );

      // Step 2: Attempt to reload the repository
      final LocalGitRepositoryPort reloadedRepositoryPort = dependencies
          .createLocalGitRepositoryPort(tester);
      
      // This should NOT throw "fatal: path does not exist in 'HEAD'"
      final afterRepository = await reloadedRepositoryPort.openRepository(
        repositoryPath: fixture.directory.path,
      );

      final reloadedSnapshot = await tester.runAsync(
        () => fixture.observeReloadedRepositoryState(repository: afterRepository),
      );
      if (reloadedSnapshot == null) {
        throw StateError(
          'TS-243 repository reload did not complete.',
        );
      }

      expect(
        reloadedSnapshot.snapshot.issues,
        isNotEmpty,
        reason:
            'Step 2 failed: repository reload should successfully load the snapshot without Git errors.',
      );

      // Step 3: Execute integrated search query (project = TRACK)
      final searchResults = await tester.runAsync(
        () async => await afterRepository.searchIssues(
          'project = ${Ts215ConcurrentLegacyDeletedIndexFixture.projectKey}',
        ),
      );

      // Expected Result: search returns only surviving issues
      expect(
        searchResults?.map((issue) => issue.key).toList(),
        [Ts215ConcurrentLegacyDeletedIndexFixture.survivingIssueKey],
        reason:
            'Expected result failed: search should return only surviving issues after concurrent delete.',
      );

      // Human-style verification: Verify the surviving issue is usable
      expect(
        searchResults?.single.summary,
        'Surviving issue',
        reason:
            'Human-style verification: the surviving issue should have correct metadata after repository reload.',
      );

      // Verify that deleted issues are no longer searchable
      for (final deletedKey
          in Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys) {
        final deletedSearchResults = await tester.runAsync(
          () async => await afterRepository.searchIssues(
            'project = ${Ts215ConcurrentLegacyDeletedIndexFixture.projectKey} $deletedKey',
          ),
        );
        expect(
          deletedSearchResults,
          isEmpty,
          reason:
              'Human-style verification: deleted issue $deletedKey should not be searchable after concurrent delete.',
        );
      }

      // Verify repository index no longer references deleted issues
      for (final deletedKey
          in Ts215ConcurrentLegacyDeletedIndexFixture.deleteIssueKeys) {
        final pathForKey = reloadedSnapshot.snapshot.repositoryIndex
            .pathForKey(deletedKey);
        expect(
          pathForKey,
          isNull,
          reason:
              'Expected result: the repository index should not resolve $deletedKey after concurrent deletion.',
        );
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
