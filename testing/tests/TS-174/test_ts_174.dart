import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts174_existing_issue_archive_fixture.dart';

void main() {
  test(
    'TS-174 archives an existing issue and exposes the archived state to repository consumers',
    () async {
      final fixture = await Ts174ExistingIssueArchiveFixture.create();
      addTearDown(fixture.dispose);

      final beforeArchival = await fixture.observeBeforeArchiveState();

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

      final afterArchival = await fixture.archiveIssueViaRepositoryService();

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
        isTrue,
        reason:
            'Step 3 failed: the archived issue artifact should still exist in repository storage after archiving.',
      );
      expect(
        afterArchival.snapshot.repositoryIndex.pathForKey(
          Ts174ExistingIssueArchiveFixture.issueKey,
        ),
        Ts174ExistingIssueArchiveFixture.issuePath,
        reason:
            'Step 3 failed: the repository index should continue to resolve TRACK-122 to its stored artifact after archiving.',
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
        contains('archived: true'),
        reason:
            'Expected result mismatch: the persisted issue markdown should contain archived: true after archiveIssue completes.',
      );
      expect(
        afterArchival.headIssueMarkdown,
        contains('archived: true'),
        reason:
            'Expected result mismatch: the committed repository artifact should contain archived: true after archiveIssue completes.',
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
  );
}
