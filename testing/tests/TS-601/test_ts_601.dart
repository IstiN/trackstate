import 'package:flutter_test/flutter_test.dart';

import 'support/ts601_archive_parent_with_children_fixture.dart';

void main() {
  test(
    'TS-601 archives a parent issue successfully while child issues remain active',
    () async {
      final fixture = await Ts601ArchiveParentWithChildrenFixture.create();
      addTearDown(fixture.dispose);

      final beforeArchive = await fixture.observeBeforeArchiveAttempt();

      expect(
        beforeArchive.parentIssue?.key,
        Ts601ArchiveParentWithChildrenFixture.parentIssueKey,
        reason:
            'Precondition failed: ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} must exist before the archive attempt starts.',
      );
      expect(
        beforeArchive.childIssue?.key,
        Ts601ArchiveParentWithChildrenFixture.childIssueKey,
        reason:
            'Precondition failed: ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} must exist before the archive attempt starts.',
      );
      expect(
        beforeArchive.parentIssue?.isArchived,
        isFalse,
        reason:
            'Precondition failed: ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} must start active before archiveIssue runs.',
      );
      expect(
        beforeArchive.childIssue?.isArchived,
        isFalse,
        reason:
            'Precondition failed: ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} must start active before archiveIssue runs.',
      );
      expect(
        beforeArchive.snapshot.repositoryIndex
            .entryForKey(Ts601ArchiveParentWithChildrenFixture.parentIssueKey)
            ?.childKeys,
        [Ts601ArchiveParentWithChildrenFixture.childIssueKey],
        reason:
            'Precondition failed: the repository index must expose ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} as an active child of ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey}.',
      );
      expect(
        beforeArchive.snapshot.repositoryIndex.pathForKey(
          Ts601ArchiveParentWithChildrenFixture.parentIssueKey,
        ),
        Ts601ArchiveParentWithChildrenFixture.parentIssuePath,
        reason:
            'Precondition failed: ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} should resolve to active storage before archiving.',
      );
      expect(
        beforeArchive.snapshot.repositoryIndex.pathForKey(
          Ts601ArchiveParentWithChildrenFixture.childIssueKey,
        ),
        Ts601ArchiveParentWithChildrenFixture.childIssuePath,
        reason:
            'Precondition failed: ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} should resolve to active storage before archiving.',
      );
      expect(
        beforeArchive.parentIssueFileExists,
        isTrue,
        reason:
            'Precondition failed: ${Ts601ArchiveParentWithChildrenFixture.parentIssuePath} must exist before the archive attempt.',
      );
      expect(
        beforeArchive.childIssueFileExists,
        isTrue,
        reason:
            'Precondition failed: ${Ts601ArchiveParentWithChildrenFixture.childIssuePath} must exist before the archive attempt.',
      );
      expect(
        beforeArchive.archivedParentIssueFileExists,
        isFalse,
        reason:
            'Precondition failed: ${Ts601ArchiveParentWithChildrenFixture.archivedParentIssuePath} must not exist before archiveIssue runs.',
      );
      expect(
        beforeArchive.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must start clean so any observed change comes from the archive attempt.',
      );

      final afterArchive = await fixture.attemptArchiveViaService();

      expect(
        afterArchive.result?.isSuccess,
        isTrue,
        reason:
            'Step 1 failed: archiveIssue should return a successful mutation result for ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} even while child issues still exist.',
      );
      expect(
        afterArchive.result?.failure,
        isNull,
        reason:
            'Step 1 failed: archiveIssue should not populate a failure when archiving a parent issue with child issues is supported.',
      );
      expect(
        afterArchive.result?.value?.key,
        Ts601ArchiveParentWithChildrenFixture.parentIssueKey,
        reason:
            'Step 1 failed: archiveIssue should return the archived ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} issue payload.',
      );
      expect(
        afterArchive.result?.value?.isArchived,
        isTrue,
        reason:
            'Expected result mismatch: the mutation payload should mark ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} as archived.',
      );
      expect(
        afterArchive.result?.value?.storagePath,
        Ts601ArchiveParentWithChildrenFixture.archivedParentIssuePath,
        reason:
            'Expected result mismatch: the mutation payload should move ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} into archive storage.',
      );

      expect(
        afterArchive.parentIssue?.key,
        Ts601ArchiveParentWithChildrenFixture.parentIssueKey,
        reason:
            'Step 2 failed: the refreshed snapshot must still expose ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} after archiving.',
      );
      expect(
        afterArchive.parentIssue?.isArchived,
        isTrue,
        reason:
            'Step 2 failed: the refreshed snapshot must mark ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} as archived.',
      );
      expect(
        afterArchive.parentIssue?.storagePath,
        Ts601ArchiveParentWithChildrenFixture.archivedParentIssuePath,
        reason:
            'Step 2 failed: the refreshed snapshot must move ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} into archive storage.',
      );
      expect(
        afterArchive.snapshot.repositoryIndex
            .entryForKey(Ts601ArchiveParentWithChildrenFixture.parentIssueKey)
            ?.isArchived,
        isTrue,
        reason:
            'Expected result mismatch: the repository index should mark ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} as archived.',
      );
      expect(
        afterArchive.snapshot.repositoryIndex.pathForKey(
          Ts601ArchiveParentWithChildrenFixture.parentIssueKey,
        ),
        Ts601ArchiveParentWithChildrenFixture.archivedParentIssuePath,
        reason:
            'Expected result mismatch: the repository index should resolve ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} to archive storage after archiving.',
      );
      expect(
        afterArchive.parentIssueFileExists,
        isFalse,
        reason:
            'Step 3 failed: ${Ts601ArchiveParentWithChildrenFixture.parentIssuePath} should leave active storage after archiveIssue succeeds.',
      );
      expect(
        afterArchive.archivedParentIssueFileExists,
        isTrue,
        reason:
            'Step 3 failed: ${Ts601ArchiveParentWithChildrenFixture.archivedParentIssuePath} should be created in archive storage.',
      );
      expect(
        afterArchive.archivedParentIssueMarkdown,
        contains('archived: true'),
        reason:
            'Expected result mismatch: the archived parent markdown should persist archived: true in archive storage.',
      );

      expect(
        afterArchive.childIssue?.key,
        Ts601ArchiveParentWithChildrenFixture.childIssueKey,
        reason:
            'Step 4 failed: the refreshed snapshot must still expose ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} after the parent archive succeeds.',
      );
      expect(
        afterArchive.childIssue?.isArchived,
        isFalse,
        reason:
            'Step 4 failed: ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} must remain active after the parent issue is archived.',
      );
      expect(
        afterArchive.childIssue?.epicKey,
        Ts601ArchiveParentWithChildrenFixture.parentIssueKey,
        reason:
            'Expected result mismatch: ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} should still belong to ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} after archiving the parent.',
      );
      expect(
        afterArchive.childIssue?.storagePath,
        Ts601ArchiveParentWithChildrenFixture.childIssuePath,
        reason:
            'Expected result mismatch: ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} should remain in active storage.',
      );
      expect(
        afterArchive.snapshot.repositoryIndex
            .entryForKey(Ts601ArchiveParentWithChildrenFixture.childIssueKey)
            ?.isArchived,
        isFalse,
        reason:
            'Expected result mismatch: the repository index must keep ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} active after the parent archive.',
      );
      expect(
        afterArchive.snapshot.repositoryIndex.pathForKey(
          Ts601ArchiveParentWithChildrenFixture.childIssueKey,
        ),
        Ts601ArchiveParentWithChildrenFixture.childIssuePath,
        reason:
            'Expected result mismatch: the repository index must keep ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} in the active index path.',
      );
      expect(
        afterArchive.snapshot.repositoryIndex
            .entryForKey(Ts601ArchiveParentWithChildrenFixture.parentIssueKey)
            ?.childKeys,
        [Ts601ArchiveParentWithChildrenFixture.childIssueKey],
        reason:
            'Expected result mismatch: the archived parent entry should still expose ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} in repository metadata.',
      );
      expect(
        afterArchive.childIssueFileExists,
        isTrue,
        reason:
            'Step 4 failed: ${Ts601ArchiveParentWithChildrenFixture.childIssuePath} must remain on disk after archiving the parent issue.',
      );
      expect(
        afterArchive.childIssueMarkdown,
        beforeArchive.childIssueMarkdown,
        reason:
            'Expected result mismatch: archiving the parent issue must not rewrite the child issue markdown.',
      );
      expect(
        afterArchive.headRevision,
        isNot(beforeArchive.headRevision),
        reason:
            'Expected result mismatch: a successful archive operation should create a new Git revision.',
      );
      expect(
        afterArchive.latestCommitSubject,
        'Archive ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey}',
        reason:
            'Expected result mismatch: the archive workflow should commit the repository change with the standard archive message.',
      );
      expect(
        afterArchive.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: the archive workflow should leave the Git worktree clean, but `git status --short` returned ${afterArchive.worktreeStatusLines.join(' | ')}.',
      );

      expect(
        afterArchive.projectSearchResults.map((issue) => issue.key).toList(),
        containsAll(<String>[
          Ts601ArchiveParentWithChildrenFixture.parentIssueKey,
          Ts601ArchiveParentWithChildrenFixture.childIssueKey,
        ]),
        reason:
            'Human-style verification failed: integrated clients searching the project should still see both the archived parent issue and its active child task.',
      );
      expect(
        afterArchive.projectSearchResults
            .singleWhere(
              (issue) =>
                  issue.key ==
                  Ts601ArchiveParentWithChildrenFixture.parentIssueKey,
            )
            .isArchived,
        isTrue,
        reason:
            'Human-style verification failed: project search should show ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} as archived after the mutation succeeds.',
      );
      expect(
        afterArchive.projectSearchResults
            .singleWhere(
              (issue) =>
                  issue.key ==
                  Ts601ArchiveParentWithChildrenFixture.childIssueKey,
            )
            .isArchived,
        isFalse,
        reason:
            'Human-style verification failed: project search should keep ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} visible as active after the parent archive.',
      );
      expect(
        afterArchive.parentSearchResults.map((issue) => issue.key).toList(),
        [Ts601ArchiveParentWithChildrenFixture.parentIssueKey],
        reason:
            'Human-style verification failed: searching specifically for the parent issue should still return ${Ts601ArchiveParentWithChildrenFixture.parentIssueKey} after archiving.',
      );
      expect(
        afterArchive.parentSearchResults.single.storagePath,
        Ts601ArchiveParentWithChildrenFixture.archivedParentIssuePath,
        reason:
            'Human-style verification failed: searching for the parent issue should show it from archive storage.',
      );
      expect(
        afterArchive.childSearchResults.map((issue) => issue.key).toList(),
        [Ts601ArchiveParentWithChildrenFixture.childIssueKey],
        reason:
            'Human-style verification failed: searching specifically for the child issue should still return ${Ts601ArchiveParentWithChildrenFixture.childIssueKey} after the parent archive.',
      );
      expect(
        afterArchive.childSearchResults.single.storagePath,
        Ts601ArchiveParentWithChildrenFixture.childIssuePath,
        reason:
            'Human-style verification failed: searching for the child issue should still show the active storage path.',
      );
      expect(
        afterArchive.childSearchResults.single.isArchived,
        isFalse,
        reason:
            'Human-style verification failed: searching for the child issue should still show it as active.',
      );
      expect(
        afterArchive.childSearchResults.single.epicKey,
        Ts601ArchiveParentWithChildrenFixture.parentIssueKey,
        reason:
            'Human-style verification failed: searching for the child issue should still expose the archived parent relationship clients rely on.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
