import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts174_existing_issue_archive_fixture.dart';

void main() {
  testWidgets(
    'TS-184 archives an existing issue successfully without throwing',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts174ExistingIssueArchiveFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-184 fixture creation did not complete.');
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
      final beforeArchival = await tester.runAsync(
        () => fixture.observeRepositoryState(repository: repository),
      );
      if (beforeArchival == null) {
        throw StateError('TS-184 pre-archive observation did not complete.');
      }

      expect(
        beforeArchival.issueFileExists,
        isTrue,
        reason:
            'Precondition failed: TRACK-122 must exist in ${beforeArchival.repositoryPath} before archiveIssue runs.',
      );
      expect(
        beforeArchival.currentIssue.isArchived,
        isFalse,
        reason:
            'Precondition failed: TRACK-122 must start active before the archive workflow runs.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts174ExistingIssueArchiveFixture.issueKey],
        reason:
            'Precondition failed: TRACK-122 must be visible to repository consumers before archiving.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            'Precondition failed: repository search must show TRACK-122 as active before archiving.',
      );

      final archivedIssue = await tester.runAsync(
        () => fixture.archiveIssueViaRepositoryService(repository: repository),
      );
      if (archivedIssue == null) {
        throw StateError('TS-184 archive request did not complete.');
      }

      final reloadedRepository = await repositoryPort.openRepository(
        repositoryPath: fixture.directory.path,
      );
      final afterArchival = await tester.runAsync(
        () => fixture.observeRepositoryState(
          repository: reloadedRepository,
          archivedIssue: archivedIssue,
        ),
      );
      if (afterArchival == null) {
        throw StateError('TS-184 post-archive observation did not complete.');
      }

      expect(
        afterArchival.archivedIssue?.key,
        Ts174ExistingIssueArchiveFixture.issueKey,
        reason:
            'Step 1 failed: archiveIssue should complete and return TRACK-122 without throwing an exception.',
      );
      expect(
        afterArchival.archivedIssue?.isArchived,
        isTrue,
        reason:
            'Step 1 failed: the returned issue should already be marked archived when archiveIssue succeeds.',
      );
      expect(
        afterArchival.issueFileExists,
        isFalse,
        reason:
            'Step 2 failed: the active issue artifact ${afterArchival.issuePath} should be removed after archiving.',
      );
      expect(
        afterArchival.snapshot.repositoryIndex
            .entryForKey(Ts174ExistingIssueArchiveFixture.issueKey)
            ?.isArchived,
        isTrue,
        reason:
            'Step 2 failed: the repository index should mark TRACK-122 as archived after archiveIssue completes.',
      );
      expect(
        afterArchival.currentIssue.isArchived,
        isTrue,
        reason:
            'Step 2 failed: reloading repository state should resolve TRACK-122 as archived.',
      );
      expect(
        afterArchival.visibleIssueSearchResults
            .map((issue) => '${issue.key}:${issue.isArchived}')
            .toList(),
        ['${Ts174ExistingIssueArchiveFixture.issueKey}:true'],
        reason:
            'Human-style verification failed: repository search should still show TRACK-122 and present it as archived to callers after archiving.',
      );
      expect(
        afterArchival.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: the successful archive flow should leave the repository worktree clean.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
