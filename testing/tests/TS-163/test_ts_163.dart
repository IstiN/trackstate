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

      expect(
        afterArchival.forcedArchiveCommitAttempts,
        1,
        reason:
            'TS-163 must force exactly one low-level archive commit failure to reproduce the provider error path.',
      );
      expect(
        afterArchival.errorType,
        'TrackStateRepositoryException',
        reason:
            'Archiving an existing issue in ${afterArchival.repositoryPath} must surface a repository-domain exception instead of ${afterArchival.errorType}. '
            'Actual message: ${afterArchival.errorMessage}. '
            'Worktree status: ${afterArchival.worktreeStatusLines.join(' | ')}.',
      );
      expect(
        afterArchival.errorMessage,
        isNot(contains('Git command failed')),
        reason:
            'Archive failures must not leak raw provider command details to repository-service consumers.',
      );
      expect(
        afterArchival.errorMessage,
        isNot(contains('fatal:')),
        reason: 'Archive failures must not expose Git stderr to callers.',
      );
      expect(
        afterArchival.errorMessage,
        isNot(contains('.git/index.lock')),
        reason:
            'Archive failures must hide internal Git filesystem details from callers.',
      );
      expect(
        afterArchival.visibleIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts163ArchiveProviderFailureFixture.issueKey],
        reason:
            'From a caller perspective, repository search should still show TRACK-122 after the archive failure.',
      );
      expect(
        afterArchival.visibleIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            'From a caller perspective, TRACK-122 should still appear active after the archive failure.',
      );
      expect(
        afterArchival.headIssueMarkdown,
        beforeArchival.headIssueMarkdown,
        reason:
            'The failed archive must not change the committed version of ${Ts163ArchiveProviderFailureFixture.issuePath}.',
      );
      expect(
        afterArchival.headRevision,
        beforeArchival.headRevision,
        reason:
            'The failed archive must not create a Git commit when the provider write fails.',
      );
    },
  );
}
