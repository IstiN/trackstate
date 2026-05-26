import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts163_archive_provider_failure_fixture.dart';

void main() {
  test(
    'TS-163 maps archive provider failures to a repository exception without leaking Git details',
    () async {
      final fixture = await Ts163ArchiveProviderFailureFixture.create();
      addTearDown(fixture.dispose);

      final beforeArchival = await fixture.observeBeforeArchiveState();

      expect(
        beforeArchival.issueFileExists,
        isTrue,
        reason:
            'TRACK-122 must exist in ${beforeArchival.repositoryPath} before the archive failure scenario begins.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts163ArchiveProviderFailureFixture.issueKey],
        reason:
            'The precondition requires ${Ts163ArchiveProviderFailureFixture.issueKey} to be visible to repository-service consumers before archiving.',
      );
      expect(
        beforeArchival.visibleIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            '${Ts163ArchiveProviderFailureFixture.issueKey} must start active before the archive attempt.',
      );
      expect(
        beforeArchival.worktreeStatusLines,
        isEmpty,
        reason:
            'The seeded repository must start clean so the forced provider failure is the only source of archive errors.',
      );

      final afterArchival = await fixture.archiveIssueViaRepositoryService();
      final failures = <String>[];
      final errorMessage = afterArchival.errorMessage ?? '<null>';
      final visibleIssueKeys = afterArchival.visibleIssueSearchResults
          .map((issue) => issue.key)
          .toList(growable: false);

      if (afterArchival.forcedArchiveCommitAttempts != 1) {
        failures.add(
          'Step 1 failed: expected exactly one forced archive commit failure, '
          'but observed ${afterArchival.forcedArchiveCommitAttempts}.',
        );
      }
      if (afterArchival.errorType != 'TrackStateRepositoryException') {
        failures.add(
          'Step 3 failed: expected TrackStateRepositoryException, but the caller '
          'received ${afterArchival.errorType}. Visible message: $errorMessage. '
          'Worktree status: ${afterArchival.worktreeStatusLines.join(' | ')}.',
        );
      }
      if (errorMessage.contains('Git command failed')) {
        failures.add(
          'Expected-result mismatch: the caller-visible message leaked the raw '
          'Git/provider command: $errorMessage',
        );
      }
      if (errorMessage.contains('fatal:')) {
        failures.add(
          'Expected-result mismatch: the caller-visible message leaked raw Git '
          'stderr: $errorMessage',
        );
      }
      if (errorMessage.contains('.git/index.lock')) {
        failures.add(
          'Expected-result mismatch: the caller-visible message leaked internal '
          'Git filesystem details: $errorMessage',
        );
      }
      if (!_listsEqual(
        visibleIssueKeys,
        const [Ts163ArchiveProviderFailureFixture.issueKey],
      )) {
        failures.add(
          'Repository-state regression: expected search to keep returning '
          '${Ts163ArchiveProviderFailureFixture.issueKey} after the archive '
          'failure, but observed $visibleIssueKeys.',
        );
      }
      if (afterArchival.visibleIssueSearchResults.length != 1) {
        failures.add(
          'Repository-state regression: expected exactly one visible issue after '
          'the failed archive, but observed '
          '${afterArchival.visibleIssueSearchResults.length}.',
        );
      } else if (afterArchival.visibleIssueSearchResults.single.isArchived) {
        failures.add(
          'Repository-state regression: expected '
          '${Ts163ArchiveProviderFailureFixture.issueKey} to remain active after '
          'the archive failure, but it was marked archived.',
        );
      }
      if (afterArchival.headIssueMarkdown != beforeArchival.headIssueMarkdown) {
        failures.add(
          'Commit-history regression: the failed archive rewrote committed '
          'content at ${Ts163ArchiveProviderFailureFixture.issuePath}.',
        );
      }
      if (afterArchival.headRevision != beforeArchival.headRevision) {
        failures.add(
          'Commit-history regression: the failed archive created a new Git '
          'revision (${afterArchival.headRevision}) instead of preserving '
          '${beforeArchival.headRevision}.',
        );
      }

      if (failures.isNotEmpty) {
        fail(failures.join('\n'));
      }
    },
  );
}

bool _listsEqual<T>(List<T> actual, List<T> expected) {
  if (actual.length != expected.length) {
    return false;
  }
  for (var index = 0; index < actual.length; index += 1) {
    if (actual[index] != expected[index]) {
      return false;
    }
  }
  return true;
}
