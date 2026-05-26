import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts193_archive_permission_failure_fixture.dart';

void main() {
  testWidgets(
    'TS-218 keeps the Git worktree and index clean when archive relocation fails',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts193ArchivePermissionFailureFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-218 fixture creation did not complete.');
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
        throw StateError('TS-218 pre-archive observation did not complete.');
      }

      expect(
        beforeArchival.issueFileExists,
        isTrue,
        reason:
            'Precondition failed: ${Ts193ArchivePermissionFailureFixture.issuePath} must exist before the failed archive attempt begins.',
      );
      expect(
        beforeArchival.snapshot.repositoryIndex.pathForKey(
          Ts193ArchivePermissionFailureFixture.issueKey,
        ),
        Ts193ArchivePermissionFailureFixture.issuePath,
        reason:
            'Precondition failed: TRACK-122 should resolve to its active storage path before archiveIssue runs.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts193ArchivePermissionFailureFixture.issueKey],
        reason:
            'Precondition failed: repository consumers should be able to find TRACK-122 before the failed archive attempt.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            'Precondition failed: TRACK-122 should appear active before the failed archive attempt.',
      );
      expect(
        beforeArchival.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must start clean, but git status returned ${beforeArchival.worktreeStatusLines.join(' | ')}.',
      );
      expect(
        beforeArchival.stagedIndexStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the Git index must start clean, but git diff --cached --name-status returned ${beforeArchival.stagedIndexStatusLines.join(' | ')}.',
      );
      expect(
        beforeArchival.untrackedFiles,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must not start with untracked files, but git ls-files --others --exclude-standard returned ${beforeArchival.untrackedFiles.join(' | ')}.',
      );

      final archiveFailure = await tester.runAsync(
        () => fixture.archiveIssueViaRepositoryService(
          repository: beforeRepository,
        ),
      );
      if (archiveFailure == null) {
        throw StateError('TS-218 archive request did not complete.');
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
        throw StateError('TS-218 post-archive observation did not complete.');
      }

      expect(
        afterArchival.errorType,
        'TrackStateRepositoryException',
        reason:
            'Step 2 failed: archiveIssue should throw TrackStateRepositoryException when archive relocation cannot write to the destination directory, but got ${afterArchival.errorType}. Actual message: ${afterArchival.errorMessage}.',
      );
      expect(
        afterArchival.headRevision,
        beforeArchival.headRevision,
        reason:
            'Step 3 failed: the failed archive attempt must not create a new Git commit.',
      );
      expect(
        afterArchival.headIssueMarkdown,
        beforeArchival.headIssueMarkdown,
        reason:
            'Step 3 failed: the committed version of ${Ts193ArchivePermissionFailureFixture.issuePath} must remain unchanged after the failed archive attempt.',
      );
      expect(
        afterArchival.worktreeIssueMarkdown,
        beforeArchival.worktreeIssueMarkdown,
        reason:
            'Step 4 failed: the worktree copy of ${Ts193ArchivePermissionFailureFixture.issuePath} changed even though archive relocation failed.',
      );
      expect(
        afterArchival.worktreeStatusLines,
        beforeArchival.worktreeStatusLines,
        reason:
            'Step 4 failed: git status changed after the failed archive attempt. Before: ${beforeArchival.worktreeStatusLines.join(' | ')}. After: ${afterArchival.worktreeStatusLines.join(' | ')}.',
      );
      expect(
        afterArchival.stagedIndexStatusLines,
        beforeArchival.stagedIndexStatusLines,
        reason:
            'Step 4 failed: the staged Git index changed after the failed archive attempt. Before: ${beforeArchival.stagedIndexStatusLines.join(' | ')}. After: ${afterArchival.stagedIndexStatusLines.join(' | ')}.',
      );
      expect(
        afterArchival.unstagedDiffStatusLines,
        isEmpty,
        reason:
            'Step 4 failed: git diff --name-status should stay empty after the failed archive attempt, but returned ${afterArchival.unstagedDiffStatusLines.join(' | ')}.',
      );
      expect(
        afterArchival.untrackedFiles,
        beforeArchival.untrackedFiles,
        reason:
            'Step 4 failed: untracked files changed after the failed archive attempt. Before: ${beforeArchival.untrackedFiles.join(' | ')}. After: ${afterArchival.untrackedFiles.join(' | ')}.',
      );
      expect(
        afterArchival.stagedIndexStatusLines.any(
          (line) =>
              line.startsWith('D') &&
              line.contains(Ts193ArchivePermissionFailureFixture.issueKey),
        ),
        isFalse,
        reason:
            'Step 4 failed: the failed archive attempt left a staged deletion for ${Ts193ArchivePermissionFailureFixture.issueKey}. Actual staged index: ${afterArchival.stagedIndexStatusLines.join(' | ')}.',
      );
      expect(
        afterArchival.untrackedFiles.any(
          (path) =>
              path.contains(Ts193ArchivePermissionFailureFixture.issueKey),
        ),
        isFalse,
        reason:
            'Step 4 failed: the failed archive attempt left untracked files for ${Ts193ArchivePermissionFailureFixture.issueKey}. Actual untracked files: ${afterArchival.untrackedFiles.join(' | ')}.',
      );
      expect(
        afterArchival.issueFileExists,
        isTrue,
        reason:
            'Step 4 failed: ${Ts193ArchivePermissionFailureFixture.issuePath} should still exist in active storage after the failed archive attempt.',
      );
      expect(
        afterArchival.snapshot.repositoryIndex.pathForKey(
          Ts193ArchivePermissionFailureFixture.issueKey,
        ),
        Ts193ArchivePermissionFailureFixture.issuePath,
        reason:
            'Step 4 failed: the repository index should still resolve TRACK-122 to the active storage path after the failed archive attempt.',
      );
      expect(
        afterArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts193ArchivePermissionFailureFixture.issueKey],
        reason:
            'Human-style verification failed: repository consumers should still find TRACK-122 after the failed archive attempt.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            'Human-style verification failed: repository consumers should still see TRACK-122 as active after the failed archive attempt.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.storagePath,
        Ts193ArchivePermissionFailureFixture.issuePath,
        reason:
            'Human-style verification failed: repository consumers should still see TRACK-122 at ${Ts193ArchivePermissionFailureFixture.issuePath} after the failed archive attempt.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
