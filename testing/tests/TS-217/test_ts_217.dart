import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts195_archive_directory_artifacts_fixture.dart';

void main() {
  testWidgets(
    'TS-217 archives TRACK-122 by relocating physical artifacts and updating metadata',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts195ArchiveDirectoryArtifactsFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-217 fixture creation did not complete.');
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
        throw StateError('TS-217 pre-archive observation did not complete.');
      }

      expect(
        beforeArchival.issueFileExists,
        isTrue,
        reason:
            'Precondition failed: ${Ts195ArchiveDirectoryArtifactsFixture.issuePath} must exist before archiveIssue runs.',
      );
      expect(
        beforeArchival.attachmentFileExists,
        isTrue,
        reason:
            'Precondition failed: ${Ts195ArchiveDirectoryArtifactsFixture.attachmentPath} must exist before archiveIssue runs.',
      );
      expect(
        beforeArchival.activeArtifactPaths,
        [
          Ts195ArchiveDirectoryArtifactsFixture.attachmentPath,
          Ts195ArchiveDirectoryArtifactsFixture.issuePath,
        ],
        reason:
            'Precondition failed: TRACK-122 must start with both its main content artifact and associated sibling artifact in active storage.',
      );
      expect(
        beforeArchival.snapshot.repositoryIndex.pathForKey(
          Ts195ArchiveDirectoryArtifactsFixture.issueKey,
        ),
        Ts195ArchiveDirectoryArtifactsFixture.issuePath,
        reason:
            'Precondition failed: TRACK-122 should resolve to its active repository artifact before archiveIssue is invoked.',
      );
      expect(
        beforeArchival.currentIssue.isArchived,
        isFalse,
        reason:
            'Precondition failed: TRACK-122 should start active before the archive workflow runs.',
      );
      expect(
        beforeArchival.currentIssue.storagePath,
        Ts195ArchiveDirectoryArtifactsFixture.issuePath,
        reason:
            'Precondition failed: TRACK-122 should report the active storage path before archiveIssue runs.',
      );
      expect(
        beforeArchival.mainMarkdown,
        isNot(contains('archived: true')),
        reason:
            'Precondition failed: the active markdown must not already be marked archived.',
      );
      expect(
        beforeArchival.archivedArtifactPaths,
        isEmpty,
        reason:
            'Precondition failed: archive storage must start empty for TRACK-122.',
      );

      final archivedIssue = await tester.runAsync(
        () => fixture.archiveIssueViaRepositoryService(
          repository: beforeRepository,
        ),
      );
      if (archivedIssue == null) {
        throw StateError('TS-217 archive request did not complete.');
      }

      final afterRepository = await repositoryPort.openRepository(
        repositoryPath: fixture.directory.path,
      );
      final afterArchival = await tester.runAsync(
        () => fixture.observeRepositoryState(
          repository: afterRepository,
          archivedIssue: archivedIssue,
        ),
      );
      if (afterArchival == null) {
        throw StateError('TS-217 post-archive observation did not complete.');
      }

      expect(
        afterArchival.archivedIssue?.key,
        Ts195ArchiveDirectoryArtifactsFixture.issueKey,
        reason:
            'Step 2 failed: archiveIssue should complete without throwing and return TRACK-122.',
      );
      expect(
        afterArchival.archivedIssue?.isArchived,
        isTrue,
        reason:
            'Step 3 failed: archiveIssue should return TRACK-122 with archived metadata set to true.',
      );
      expect(
        afterArchival.currentIssue.isArchived,
        isTrue,
        reason:
            'Step 3 failed: reloading repository state should keep TRACK-122 archived after archiveIssue succeeds.',
      );
      expect(
        afterArchival.snapshot.repositoryIndex.pathForKey(
          Ts195ArchiveDirectoryArtifactsFixture.issueKey,
        ),
        Ts195ArchiveDirectoryArtifactsFixture.archivedIssuePath,
        reason:
            'Expected result mismatch: the repository index should resolve TRACK-122 to the archive storage path after archiving.',
      );
      expect(
        afterArchival.currentIssue.storagePath,
        Ts195ArchiveDirectoryArtifactsFixture.archivedIssuePath,
        reason:
            'Human-style verification failed: integrated clients should observe TRACK-122 at the archive storage path after the archive completes.',
      );
      expect(
        afterArchival.issueFileExists,
        isFalse,
        reason:
            'Step 5 failed: ${Ts195ArchiveDirectoryArtifactsFixture.issuePath} still exists in active storage after archiving.',
      );
      expect(
        afterArchival.attachmentFileExists,
        isFalse,
        reason:
            'Step 5 failed: ${Ts195ArchiveDirectoryArtifactsFixture.attachmentPath} still exists in active storage after archiving.',
      );
      expect(
        afterArchival.activeArtifactPaths,
        isEmpty,
        reason:
            'Step 5 failed: the active issue directory still contains physical artifacts after archiving: ${afterArchival.activeArtifactPaths.join(' | ')}.',
      );
      expect(
        afterArchival.archivedIssueFileExists,
        isTrue,
        reason:
            'Step 4 failed: ${Ts195ArchiveDirectoryArtifactsFixture.archivedIssuePath} was not created in archive storage.',
      );
      expect(
        afterArchival.archivedAttachmentFileExists,
        isTrue,
        reason:
            'Step 4 failed: ${Ts195ArchiveDirectoryArtifactsFixture.archivedAttachmentPath} was not created in archive storage.',
      );
      expect(
        afterArchival.archivedArtifactPaths,
        [
          Ts195ArchiveDirectoryArtifactsFixture.archivedAttachmentPath,
          Ts195ArchiveDirectoryArtifactsFixture.archivedIssuePath,
        ],
        reason:
            'Step 4 failed: archive storage should contain the relocated main content artifact and sibling artifact for TRACK-122.',
      );
      expect(
        afterArchival.archivedMainMarkdown,
        contains('archived: true'),
        reason:
            'Expected result mismatch: the archived markdown should visibly include archived: true after the move.',
      );
      expect(
        afterArchival.archivedAttachmentText,
        Ts195ArchiveDirectoryArtifactsFixture.attachmentContents,
        reason:
            'Expected result mismatch: the relocated sibling artifact should preserve its contents after moving into archive storage.',
      );
      expect(
        afterArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts195ArchiveDirectoryArtifactsFixture.issueKey],
        reason:
            'Human-style verification failed: repository consumers should still be able to find TRACK-122 after archiving.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.isArchived,
        isTrue,
        reason:
            'Human-style verification failed: repository consumers should observe TRACK-122 as archived after archiving.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.storagePath,
        Ts195ArchiveDirectoryArtifactsFixture.archivedIssuePath,
        reason:
            'Human-style verification failed: repository consumers should observe TRACK-122 at the archived storage path, not the former active path.',
      );
      expect(
        afterArchival.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: the archive workflow should leave the repository worktree clean, but git status returned ${afterArchival.worktreeStatusLines.join(' | ')}.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
