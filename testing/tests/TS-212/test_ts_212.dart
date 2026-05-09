import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts212_missing_archive_directory_fixture.dart';

void main() {
  testWidgets(
    'TS-212 creates the missing archive directory and relocates TRACK-122 into it',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts212MissingArchiveDirectoryFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-212 fixture creation did not complete.');
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
        throw StateError('TS-212 pre-archive observation did not complete.');
      }

      expect(
        beforeArchival.issueFileExists,
        isTrue,
        reason:
            'Precondition failed: ${Ts212MissingArchiveDirectoryFixture.issuePath} must exist before archiveIssue runs.',
      );
      expect(
        beforeArchival.archiveRootExists,
        isFalse,
        reason:
            'Precondition failed: ${Ts212MissingArchiveDirectoryFixture.archiveRootPath} must not exist before the missing-directory scenario starts.',
      );
      expect(
        beforeArchival.archivedIssueDirectoryExists,
        isFalse,
        reason:
            'Precondition failed: archive storage for ${Ts212MissingArchiveDirectoryFixture.issueKey} must not already exist.',
      );
      expect(
        beforeArchival.archivedIssueFileExists,
        isFalse,
        reason:
            'Precondition failed: ${Ts212MissingArchiveDirectoryFixture.archivedIssuePath} must not exist before archiveIssue runs.',
      );
      expect(
        beforeArchival.snapshot.repositoryIndex.pathForKey(
          Ts212MissingArchiveDirectoryFixture.issueKey,
        ),
        Ts212MissingArchiveDirectoryFixture.issuePath,
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
        Ts212MissingArchiveDirectoryFixture.issuePath,
        reason:
            'Precondition failed: TRACK-122 should start on the active storage path before archiveIssue runs.',
      );
      expect(
        beforeArchival.mainMarkdown,
        isNot(contains('archived: true')),
        reason:
            'Precondition failed: the active issue markdown should not already contain archived: true before archiveIssue runs.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts212MissingArchiveDirectoryFixture.issueKey],
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
        throw StateError('TS-212 archive request did not complete.');
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
        throw StateError('TS-212 post-archive observation did not complete.');
      }

      expect(
        afterArchival.archivedIssue?.key,
        Ts212MissingArchiveDirectoryFixture.issueKey,
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
            'Step 4 failed: ${Ts212MissingArchiveDirectoryFixture.issuePath} still exists in active storage after archiving.',
      );
      expect(
        afterArchival.archiveRootExists,
        isTrue,
        reason:
            'Step 3 failed: ${Ts212MissingArchiveDirectoryFixture.archiveRootPath} was not created when archiveIssue ran against a repository without archive storage.',
      );
      expect(
        afterArchival.archivedIssueDirectoryExists,
        isTrue,
        reason:
            'Step 4 failed: ${Ts212MissingArchiveDirectoryFixture.archivedIssueDirectoryPath} was not created for TRACK-122 after archiving.',
      );
      expect(
        afterArchival.archivedIssueFileExists,
        isTrue,
        reason:
            'Step 4 failed: ${Ts212MissingArchiveDirectoryFixture.archivedIssuePath} was not created in the new archive directory.',
      );
      expect(
        afterArchival.archivedMainMarkdown,
        contains('archived: true'),
        reason:
            'Expected result mismatch: the archived markdown should visibly contain archived: true after the move.',
      );
      expect(
        afterArchival.snapshot.repositoryIndex.pathForKey(
          Ts212MissingArchiveDirectoryFixture.issueKey,
        ),
        Ts212MissingArchiveDirectoryFixture.archivedIssuePath,
        reason:
            'Expected result mismatch: the repository index should resolve TRACK-122 to the archived storage path after the move.',
      );
      expect(
        afterArchival.currentIssue.storagePath,
        Ts212MissingArchiveDirectoryFixture.archivedIssuePath,
        reason:
            'Expected result mismatch: reloading the repository should expose TRACK-122 at the archived storage path after the move.',
      );
      expect(
        afterArchival.currentIssue.isArchived,
        isTrue,
        reason:
            'Expected result mismatch: reloading the repository snapshot should resolve TRACK-122 as archived.',
      );
      expect(
        afterArchival.headIssueMarkdown,
        isNull,
        reason:
            'Expected result mismatch: the active issue markdown should be removed from HEAD after archiving.',
      );
      expect(
        afterArchival.headArchivedIssueMarkdown,
        contains('archived: true'),
        reason:
            'Expected result mismatch: the committed archive markdown should contain archived: true.',
      );
      expect(
        afterArchival.headRevision,
        isNot(beforeArchival.headRevision),
        reason:
            'Expected result mismatch: a successful archive operation should create a new Git revision for TRACK-122.',
      );
      expect(
        afterArchival.latestCommitSubject,
        'Archive ${Ts212MissingArchiveDirectoryFixture.issueKey}',
        reason:
            'Expected result mismatch: the archive workflow should commit the repository change with the standard archive message.',
      );
      expect(
        afterArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts212MissingArchiveDirectoryFixture.issueKey],
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
        Ts212MissingArchiveDirectoryFixture.archivedIssuePath,
        reason:
            'Human-style verification failed: repository consumers should observe TRACK-122 in the newly created archive directory after archiving.',
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
