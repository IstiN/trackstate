import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts185_archive_git_lock_fixture.dart';

void main() {
  test(
    'TS-185 archives with a real Git lock file and returns a sanitized repository exception',
    () async {
      final fixture = await Ts185ArchiveGitLockFixture.create();
      addTearDown(fixture.dispose);

      final beforeArchival = await fixture.observeBeforeArchiveState();

      expect(
        beforeArchival.issueFileExists,
        isTrue,
        reason:
            'TRACK-122 must exist in ${beforeArchival.repositoryPath} before the Git lock failure scenario begins.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts185ArchiveGitLockFixture.issueKey],
        reason:
            'The precondition requires ${Ts185ArchiveGitLockFixture.issueKey} to be visible to repository-service consumers before archiving.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            '${Ts185ArchiveGitLockFixture.issueKey} must start active before the archive attempt.',
      );
      expect(
        beforeArchival.worktreeStatusLines,
        isEmpty,
        reason:
            'The seeded repository must start clean so the Git lock failure is the only source of the archive error.',
      );
      expect(
        File(fixture.gitLockPath).existsSync(),
        isFalse,
        reason:
            'Step 1 precondition failed: .git/index.lock should not exist before TS-185 creates it.',
      );

      final afterArchival = await fixture.archiveIssueViaRepositoryService();

      expect(
        File(fixture.gitLockPath).existsSync(),
        isTrue,
        reason:
            'Step 1 failed: TS-185 must create .git/index.lock before archiveIssue runs.',
      );
      expect(
        afterArchival.errorType,
        'TrackStateRepositoryException',
        reason:
            'Step 3 failed: archiving an existing issue with a real Git lock must surface a repository-domain exception instead of ${afterArchival.errorType}. Actual message: ${afterArchival.errorMessage}.',
      );
      expect(
        afterArchival.errorMessage,
        contains('Could not archive ${Ts185ArchiveGitLockFixture.issueKey}'),
        reason:
            'Step 3 failed: callers should receive a repository-level archive failure message when Git is locked.',
      );
      expect(
        afterArchival.errorMessage,
        isNot(contains('Git command failed')),
        reason:
            'Expected result mismatch: the archive failure message must not leak raw Git command details.',
      );
      expect(
        afterArchival.errorMessage,
        isNot(contains('fatal:')),
        reason:
            'Expected result mismatch: the archive failure message must not expose Git stderr.',
      );
      expect(
        afterArchival.errorMessage,
        isNot(contains('.git/index.lock')),
        reason:
            'Expected result mismatch: the archive failure message must not expose internal Git filesystem details.',
      );
      expect(
        afterArchival.errorMessage,
        isNot(contains('unable to create')),
        reason:
            'Expected result mismatch: the archive failure message must not echo the raw Git lock-file error text.',
      );
      expect(
        afterArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts185ArchiveGitLockFixture.issueKey],
        reason:
            'From a repository consumer perspective, TRACK-122 should still be visible after the failed archive attempt.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            'From a repository consumer perspective, TRACK-122 should still appear active after the failed archive attempt.',
      );
      expect(
        afterArchival.issuePath,
        Ts185ArchiveGitLockFixture.issuePath,
        reason:
            'The post-failure observation must inspect the original active issue artifact instead of a path resolved from repository reload state.',
      );
      expect(
        afterArchival.issueFileExists,
        isTrue,
        reason:
            'The failed archive must leave ${Ts185ArchiveGitLockFixture.issuePath} in place in the worktree.',
      );
      expect(
        afterArchival.worktreeIssueMarkdown,
        beforeArchival.worktreeIssueMarkdown,
        reason:
            'The failed archive must not partially rewrite the worktree copy of ${Ts185ArchiveGitLockFixture.issuePath}.',
      );
      expect(
        afterArchival.worktreeStatusLines.any(
          (line) => line.contains(Ts185ArchiveGitLockFixture.issuePath),
        ),
        isFalse,
        reason:
            'The failed archive must not leave a Git status entry for ${Ts185ArchiveGitLockFixture.issuePath}. Actual git status: ${afterArchival.worktreeStatusLines.join(' | ')}.',
      );
      expect(
        afterArchival.headIssueMarkdown,
        beforeArchival.headIssueMarkdown,
        reason:
            'The failed archive must not change the committed version of ${Ts185ArchiveGitLockFixture.issuePath}.',
      );
      expect(
        afterArchival.headRevision,
        beforeArchival.headRevision,
        reason:
            'The failed archive must not create a Git commit when .git/index.lock blocks the write.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
