import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts195_archive_directory_artifacts_fixture.dart';

void main() {
  testWidgets(
    'TS-195 archives an issue by relocating its full directory into archive storage',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts195ArchiveDirectoryArtifactsFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-195 fixture creation did not complete.');
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
        throw StateError('TS-195 pre-archive observation did not complete.');
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
            'Precondition failed: the active issue directory must start with both the markdown artifact and the sibling attachment.',
      );
      expect(
        beforeArchival.archivedArtifactPaths,
        isEmpty,
        reason:
            'Precondition failed: archive storage must start empty for ${Ts195ArchiveDirectoryArtifactsFixture.issueKey}.',
      );
      expect(
        beforeArchival.snapshot.repositoryIndex.pathForKey(
          Ts195ArchiveDirectoryArtifactsFixture.issueKey,
        ),
        Ts195ArchiveDirectoryArtifactsFixture.issuePath,
        reason:
            'Precondition failed: TRACK-122 should resolve to its active repository artifact before archiving.',
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
            'Precondition failed: the active issue should report its active storage path before archiving.',
      );
      expect(
        beforeArchival.mainMarkdown,
        isNot(contains('archived: true')),
        reason:
            'Precondition failed: the active markdown must not already be marked archived.',
      );
      expect(
        beforeArchival.attachmentText,
        Ts195ArchiveDirectoryArtifactsFixture.attachmentContents,
        reason:
            'Precondition failed: the sibling attachment should contain the seeded text before archiving.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts195ArchiveDirectoryArtifactsFixture.issueKey],
        reason:
            'From a repository consumer perspective, TRACK-122 should be searchable before archiving.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            'From a repository consumer perspective, TRACK-122 should appear active before archiving.',
      );
      expect(
        beforeArchival.worktreeStatusLines,
        isEmpty,
        reason:
            'The seeded repository must start clean so the archive workflow is the only source of changes.',
      );

      final archivedIssue = await tester.runAsync(
        () => fixture.archiveIssueViaRepositoryService(
          repository: beforeRepository,
        ),
      );
      if (archivedIssue == null) {
        throw StateError('TS-195 archive request did not complete.');
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
        throw StateError('TS-195 post-archive observation did not complete.');
      }

      expect(
        afterArchival.archivedIssue?.key,
        Ts195ArchiveDirectoryArtifactsFixture.issueKey,
        reason:
            'Step 2 failed: archiveIssue should return TRACK-122 without throwing.',
      );
      expect(
        afterArchival.archivedIssue?.isArchived,
        isTrue,
        reason:
            'Step 2 failed: archiveIssue should return TRACK-122 in the archived state.',
      );
      expect(
        afterArchival.issueFileExists,
        isFalse,
        reason:
            'Step 3 failed: ${Ts195ArchiveDirectoryArtifactsFixture.issuePath} still exists in active storage after archiving.',
      );
      expect(
        afterArchival.attachmentFileExists,
        isFalse,
        reason:
            'Step 3 failed: ${Ts195ArchiveDirectoryArtifactsFixture.attachmentPath} still exists in active storage after archiving.',
      );
      expect(
        afterArchival.activeArtifactPaths,
        isEmpty,
        reason:
            'Step 3 failed: the active issue directory still contains artifacts after archiving: ${afterArchival.activeArtifactPaths.join(' | ')}.',
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
            'Step 4 failed: archive storage should contain both relocated artifacts for TRACK-122.',
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
            'Expected result mismatch: the archived issue should report the archive storage path after reloading repository state.',
      );
      expect(
        afterArchival.currentIssue.isArchived,
        isTrue,
        reason:
            'Expected result mismatch: reloading the repository snapshot should resolve TRACK-122 as archived.',
      );
      expect(
        afterArchival.archivedMainMarkdown,
        contains('archived: true'),
        reason:
            'Expected result mismatch: the archived markdown should visibly include archived: true in archive storage.',
      );
      expect(
        afterArchival.archivedAttachmentText,
        Ts195ArchiveDirectoryArtifactsFixture.attachmentContents,
        reason:
            'Expected result mismatch: the sibling attachment should preserve its content after moving into archive storage.',
      );
      expect(
        afterArchival.headIssueMarkdown,
        isNull,
        reason:
            'Expected result mismatch: the active issue markdown should be gone from HEAD after archiving.',
      );
      expect(
        afterArchival.headAttachmentText,
        isNull,
        reason:
            'Expected result mismatch: the active attachment should be gone from HEAD after archiving.',
      );
      expect(
        afterArchival.headArchivedIssueMarkdown,
        contains('archived: true'),
        reason:
            'Expected result mismatch: the committed archive markdown should contain archived: true.',
      );
      expect(
        afterArchival.headArchivedAttachmentText,
        Ts195ArchiveDirectoryArtifactsFixture.attachmentContents.trimRight(),
        reason:
            'Expected result mismatch: the committed archive attachment should preserve its original contents.',
      );
      expect(
        afterArchival.headRevision,
        isNot(beforeArchival.headRevision),
        reason:
            'Expected result mismatch: a successful archive operation should create a new Git revision for TRACK-122.',
      );
      expect(
        afterArchival.latestCommitSubject,
        'Archive ${Ts195ArchiveDirectoryArtifactsFixture.issueKey}',
        reason:
            'Expected result mismatch: the archive workflow should commit the repository change with the standard archive message.',
      );
      expect(
        afterArchival.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: the archive workflow should leave the repository worktree clean, but git status returned ${afterArchival.worktreeStatusLines.join(' | ')}.',
      );
      expect(
        afterArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts195ArchiveDirectoryArtifactsFixture.issueKey],
        reason:
            'From a repository consumer perspective, TRACK-122 should remain searchable after archiving.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.isArchived,
        isTrue,
        reason:
            'From a repository consumer perspective, TRACK-122 should appear archived after the workflow completes.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.storagePath,
        Ts195ArchiveDirectoryArtifactsFixture.archivedIssuePath,
        reason:
            'Human-style verification failed: repository consumers should observe TRACK-122 at the archive storage path after archiving.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
