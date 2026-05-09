import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts174_existing_issue_archive_fixture.dart';

void main() {
  testWidgets(
    'TS-174 archives an existing issue and requires the artifact to leave active storage',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts174ExistingIssueArchiveFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-174 fixture creation did not complete.');
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
        throw StateError('TS-174 pre-archive observation did not complete.');
      }

      expect(
        beforeArchival.issueFileExists,
        isTrue,
        reason:
            'TRACK-122 must exist in ${beforeArchival.repositoryPath} before the archive workflow begins.',
      );
      expect(
        beforeArchival.snapshot.repositoryIndex.pathForKey(
          Ts174ExistingIssueArchiveFixture.issueKey,
        ),
        Ts174ExistingIssueArchiveFixture.issuePath,
        reason:
            'Step 1 failed: TRACK-122 should resolve to its active repository artifact before archiveIssue is invoked.',
      );
      expect(
        beforeArchival.snapshot.repositoryIndex
            .entryForKey(Ts174ExistingIssueArchiveFixture.issueKey)
            ?.isArchived,
        isFalse,
        reason:
            'Step 1 failed: the repository index must not already mark TRACK-122 as archived.',
      );
      expect(
        beforeArchival.currentIssue.isArchived,
        isFalse,
        reason:
            'Step 1 failed: TRACK-122 should start active before the archive workflow runs.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts174ExistingIssueArchiveFixture.issueKey],
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
        beforeArchival.mainMarkdown,
        isNot(contains('archived: true')),
        reason:
            'Step 1 failed: the stored issue markdown should not already contain archived: true before archiveIssue runs.',
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
        throw StateError('TS-174 archive request did not complete.');
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
        throw StateError('TS-174 post-archive observation did not complete.');
      }
      final indexedIssuePath = afterArchival.snapshot.repositoryIndex
          .pathForKey(Ts174ExistingIssueArchiveFixture.issueKey);

      expect(
        afterArchival.archivedIssue?.key,
        Ts174ExistingIssueArchiveFixture.issueKey,
        reason:
            'Step 2 failed: archiveIssue should return the archived TRACK-122 issue without throwing.',
      );
      expect(
        afterArchival.archivedIssue?.isArchived,
        isTrue,
        reason:
            'Step 2 failed: archiveIssue should complete successfully and return TRACK-122 in the archived state.',
      );
      expect(
        afterArchival.issueFileExists,
        isFalse,
        reason:
            'Step 3 failed: TS-174 requires TRACK-122 to leave active storage after archiving, but ${afterArchival.issuePath} still exists in ${afterArchival.repositoryPath}. '
            'Observed repository index path: $indexedIssuePath. '
            'Observed reloaded storagePath: ${afterArchival.currentIssue.storagePath}. '
            'Observed archived flags: returned=${afterArchival.archivedIssue?.isArchived}, reloaded=${afterArchival.currentIssue.isArchived}. '
            'Observed HEAD file still readable: ${afterArchival.headIssueMarkdown != null}.',
      );
      expect(
        indexedIssuePath,
        isNot(Ts174ExistingIssueArchiveFixture.issuePath),
        reason:
            'Step 3 failed: the repository index should no longer resolve TRACK-122 to the active storage path after archiving.',
      );
      expect(
        afterArchival.currentIssue.storagePath,
        isNot(Ts174ExistingIssueArchiveFixture.issuePath),
        reason:
            'Step 3 failed: the archived issue returned from repository state should no longer report the active storage path.',
      );
      expect(
        afterArchival.snapshot.repositoryIndex
            .entryForKey(Ts174ExistingIssueArchiveFixture.issueKey)
            ?.isArchived,
        isTrue,
        reason:
            'Expected result mismatch: the repository index should mark TRACK-122 as archived after archiveIssue completes.',
      );
      expect(
        afterArchival.currentIssue.isArchived,
        isTrue,
        reason:
            'Expected result mismatch: reloading the repository snapshot should resolve TRACK-122 as archived.',
      );
      expect(
        afterArchival.mainMarkdown,
        isNull,
        reason:
            'Expected result mismatch: the active storage file should no longer be readable from ${afterArchival.issuePath} after archiving.',
      );
      expect(
        afterArchival.headIssueMarkdown,
        isNull,
        reason:
            'Expected result mismatch: the archived workflow should remove ${afterArchival.issuePath} from HEAD instead of keeping the active artifact in place.',
      );
      expect(
        afterArchival.headRevision,
        isNot(beforeArchival.headRevision),
        reason:
            'Expected result mismatch: a successful archive operation should create a new Git revision for TRACK-122.',
      );
      expect(
        afterArchival.latestCommitSubject,
        'Archive ${Ts174ExistingIssueArchiveFixture.issueKey}',
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
        [Ts174ExistingIssueArchiveFixture.issueKey],
        reason:
            'From a repository consumer perspective, TRACK-122 should remain searchable after archiving.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.isArchived,
        isTrue,
        reason:
            'From a repository consumer perspective, TRACK-122 should appear archived after the workflow completes.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
