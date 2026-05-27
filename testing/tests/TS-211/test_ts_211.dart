import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/services/issue_key_resolution_service.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts174_existing_issue_archive_fixture.dart';

void main() {
  testWidgets(
    'TS-211 updates repository key resolution to the archive storage path after archiving an issue',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts174ExistingIssueArchiveFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-211 fixture creation did not complete.');
      }
      addTearDown(() async {
        await tester.runAsync(fixture.dispose);
      });

      const dependencies = defaultTestingDependencies;
      final LocalGitRepositoryPort repositoryPort = dependencies
          .createLocalGitRepositoryPort(tester);
      final repository = await repositoryPort.openRepository(
        repositoryPath: fixture.directory.path,
      );

      final beforeResolution = await tester.runAsync(
        () => IssueKeyResolutionService(
          repository: repository,
        ).resolveIssueByKey(Ts174ExistingIssueArchiveFixture.issueKey),
      );
      if (beforeResolution == null) {
        throw StateError('TS-211 pre-archive resolution did not complete.');
      }

      const activeIssuePath = Ts174ExistingIssueArchiveFixture.issuePath;
      const archivedIssuePath =
          'TRACK/.trackstate/archive/${Ts174ExistingIssueArchiveFixture.issueKey}/main.md';

      expect(
        beforeResolution.indexPath,
        activeIssuePath,
        reason:
            'Step 1 failed: the repository path resolution service should map TRACK-122 to its active storage path before archiveIssue runs.',
      );
      expect(
        beforeResolution.storagePath,
        activeIssuePath,
        reason:
            'Step 1 failed: TRACK-122 metadata should report the active storage path before archiveIssue runs.',
      );
      expect(
        beforeResolution.searchResultKeys,
        [Ts174ExistingIssueArchiveFixture.issueKey],
        reason:
            'Human-style verification failed before archiving: integrated repository search should find TRACK-122 while it is still active.',
      );

      final archivedIssue = await tester.runAsync(
        () => fixture.archiveIssueViaRepositoryService(repository: repository),
      );
      if (archivedIssue == null) {
        throw StateError('TS-211 archive request did not complete.');
      }

      final afterResolution = await tester.runAsync(
        () => IssueKeyResolutionService(
          repository: repository,
        ).resolveIssueByKey(Ts174ExistingIssueArchiveFixture.issueKey),
      );
      if (afterResolution == null) {
        throw StateError('TS-211 post-archive resolution did not complete.');
      }

      final visibleIssueSearchResults = await tester.runAsync(
        () => repository.searchIssues(
          'project = TRACK ${Ts174ExistingIssueArchiveFixture.issueKey}',
        ),
      );
      if (visibleIssueSearchResults == null) {
        throw StateError('TS-211 post-archive search did not complete.');
      }

      expect(
        archivedIssue.key,
        Ts174ExistingIssueArchiveFixture.issueKey,
        reason:
            'Step 1 failed: archiveIssue should return TRACK-122 without throwing.',
      );
      expect(
        archivedIssue.isArchived,
        isTrue,
        reason:
            'Step 1 failed: archiveIssue should return TRACK-122 in the archived state.',
      );
      expect(
        afterResolution.key,
        beforeResolution.key,
        reason:
            'Step 2 failed: the repository path resolution service should still resolve the same issue key after archiving.',
      );
      expect(
        afterResolution.summary,
        beforeResolution.summary,
        reason:
            'Step 2 failed: resolving TRACK-122 after archiving should still return the same issue metadata.',
      );
      expect(
        afterResolution.indexPath,
        archivedIssuePath,
        reason:
            'Step 2 failed: the repository index still resolves TRACK-122 to ${afterResolution.indexPath} instead of the archive storage path $archivedIssuePath.',
      );
      expect(
        afterResolution.storagePath,
        archivedIssuePath,
        reason:
            'Step 2 failed: the repository path resolution service still reports TRACK-122 at ${afterResolution.storagePath} instead of the archive storage path $archivedIssuePath.',
      );
      expect(
        afterResolution.indexPath,
        isNot(activeIssuePath),
        reason:
            'Step 3 failed: the repository index should no longer point TRACK-122 to the previous active storage path after archiving.',
      );
      expect(
        afterResolution.storagePath,
        isNot(activeIssuePath),
        reason:
            'Step 3 failed: resolved issue metadata should no longer expose the previous active storage path after archiving.',
      );
      expect(
        visibleIssueSearchResults.map((issue) => issue.key).toList(),
        [Ts174ExistingIssueArchiveFixture.issueKey],
        reason:
            'Human-style verification failed after archiving: integrated repository search should still find TRACK-122.',
      );
      expect(
        visibleIssueSearchResults.single.isArchived,
        isTrue,
        reason:
            'Human-style verification failed after archiving: integrated repository search should show TRACK-122 as archived.',
      );
      expect(
        visibleIssueSearchResults.single.storagePath,
        archivedIssuePath,
        reason:
            'Human-style verification failed after archiving: integrated repository search still shows TRACK-122 at ${visibleIssueSearchResults.single.storagePath} instead of the archive storage path $archivedIssuePath.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
