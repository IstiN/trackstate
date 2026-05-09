import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts193_archive_permission_failure_fixture.dart';

void main() {
  testWidgets(
    'TS-193 keeps issue metadata active when archive storage relocation fails',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts193ArchivePermissionFailureFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-193 fixture creation did not complete.');
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
      final beforeArchival = await tester.runAsync(
        () => fixture.observeRepositoryState(repository: beforeRepository),
      );
      if (beforeArchival == null) {
        throw StateError('TS-193 pre-archive observation did not complete.');
      }

      expect(
        beforeArchival.issueFileExists,
        isTrue,
        reason:
            'TRACK-122 must exist in ${beforeArchival.repositoryPath} before the archive permission-failure scenario begins.',
      );
      expect(
        beforeArchival.issuePath,
        Ts193ArchivePermissionFailureFixture.issuePath,
        reason:
            'Step 1 precondition failed: TRACK-122 should resolve to its active repository artifact before archiveIssue is invoked.',
      );
      expect(
        beforeArchival.snapshot.repositoryIndex.pathForKey(
          Ts193ArchivePermissionFailureFixture.issueKey,
        ),
        Ts193ArchivePermissionFailureFixture.issuePath,
        reason:
            'Step 1 precondition failed: the repository index must point TRACK-122 at active storage before the failure is induced.',
      );
      expect(
        beforeArchival.snapshot.repositoryIndex
            .entryForKey(Ts193ArchivePermissionFailureFixture.issueKey)
            ?.isArchived,
        isFalse,
        reason:
            'Step 1 precondition failed: TRACK-122 must not already be marked archived before archiveIssue runs.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts193ArchivePermissionFailureFixture.issueKey],
        reason:
            'The precondition requires TRACK-122 to be visible to repository consumers before the archive attempt.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            'The precondition requires TRACK-122 to appear active before the archive attempt.',
      );
      expect(
        beforeArchival.worktreeIssueMarkdown,
        isNot(contains('archived: true')),
        reason:
            'Step 1 precondition failed: the active markdown should not already contain archived: true.',
      );
      expect(
        beforeArchival.worktreeStatusLines,
        isEmpty,
        reason:
            'The seeded repository must start clean so the archive permission failure is the only source of changes.',
      );

      final archiveFailure = await tester.runAsync(
        () => fixture.archiveIssueViaRepositoryService(
          repository: beforeRepository,
        ),
      );
      if (archiveFailure == null) {
        throw StateError('TS-193 archive request did not complete.');
      }
      final afterRepository = await repositoryPort.openRepository(
        repositoryPath: fixture.directory.path,
      );
      final afterArchival = await tester.runAsync(
        () => fixture.observeRepositoryState(
          repository: afterRepository,
          archiveFailure: archiveFailure,
        ),
      );
      if (afterArchival == null) {
        throw StateError('TS-193 post-archive observation did not complete.');
      }

      expect(
        afterArchival.issuePath,
        Ts193ArchivePermissionFailureFixture.issuePath,
        reason:
            'Step 3 failed: reloading repository state after the failed archive should still resolve TRACK-122 to ${Ts193ArchivePermissionFailureFixture.issuePath}.',
      );
      expect(
        afterArchival.snapshot.repositoryIndex.pathForKey(
          Ts193ArchivePermissionFailureFixture.issueKey,
        ),
        Ts193ArchivePermissionFailureFixture.issuePath,
        reason:
            'Step 3 failed: the repository index should keep TRACK-122 in active storage when archive relocation fails.',
      );
      expect(
        afterArchival.snapshot.repositoryIndex
            .entryForKey(Ts193ArchivePermissionFailureFixture.issueKey)
            ?.isArchived,
        isFalse,
        reason:
            'Step 3 failed: the repository index must keep TRACK-122 active when archive relocation fails.',
      );
      expect(
        afterArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts193ArchivePermissionFailureFixture.issueKey],
        reason:
            'Step 3 failed: repository consumers should still find TRACK-122 after the failed archive attempt.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            'Step 3 failed: repository consumers should still observe TRACK-122 as active after the failed archive attempt.',
      );
      expect(
        afterArchival.issueFileExists,
        isTrue,
        reason:
            'Step 4 failed: ${Ts193ArchivePermissionFailureFixture.issuePath} should remain in active storage when archive relocation fails.',
      );
      expect(
        afterArchival.worktreeIssueMarkdown,
        beforeArchival.worktreeIssueMarkdown,
        reason:
            'Step 4 failed: the active worktree copy of ${Ts193ArchivePermissionFailureFixture.issuePath} should remain unchanged when archive relocation fails.',
      );
      expect(
        afterArchival.worktreeIssueMarkdown,
        isNot(contains('archived: true')),
        reason:
            'Expected result mismatch: the active issue markdown should still show archived: false after the failed archive attempt.',
      );
      expect(
        afterArchival.headIssueMarkdown,
        beforeArchival.headIssueMarkdown,
        reason:
            'Expected result mismatch: the committed version of ${Ts193ArchivePermissionFailureFixture.issuePath} should remain unchanged after the failed archive attempt.',
      );
      expect(
        afterArchival.headRevision,
        beforeArchival.headRevision,
        reason:
            'Expected result mismatch: the failed archive attempt must not create a new Git commit.',
      );
      expect(
        afterArchival.worktreeStatusLines.any(
          (line) =>
              line.contains(Ts193ArchivePermissionFailureFixture.issuePath),
        ),
        isFalse,
        reason:
            'Expected result mismatch: the failed archive attempt must not leave a dirty worktree entry for ${Ts193ArchivePermissionFailureFixture.issuePath}. Actual git status: ${afterArchival.worktreeStatusLines.join(' | ')}.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.storagePath,
        Ts193ArchivePermissionFailureFixture.issuePath,
        reason:
            'Human-style verification failed: from an integrated-client perspective, TRACK-122 should still be surfaced at its active storage path after archive relocation fails.',
      );
      expect(
        afterArchival.errorType,
        'TrackStateRepositoryException',
        reason:
            'Step 2 failed: archiveIssue should throw TrackStateRepositoryException when archive relocation cannot write to the destination directory, but got ${afterArchival.errorType}. Actual message: ${afterArchival.errorMessage}.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
