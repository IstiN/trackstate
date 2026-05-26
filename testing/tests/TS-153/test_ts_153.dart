import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts153_missing_issue_archive_fixture.dart';

void main() {
  test(
    'TS-153 rejects archiving a missing issue with a repository not-found error instead of a low-level interface crash',
    () async {
      final fixture = await Ts153MissingIssueArchiveFixture.create();
      addTearDown(fixture.dispose);

      final beforeArchival = await fixture.observeBeforeArchivalState();

      expect(
        beforeArchival.missingIssueFileExists,
        isFalse,
        reason:
            '${Ts153MissingIssueArchiveFixture.missingIssueKey} must be absent before the archive attempt begins.',
      );
      expect(
        beforeArchival.snapshot.repositoryIndex.pathForKey(
          Ts153MissingIssueArchiveFixture.missingIssueKey,
        ),
        isNull,
        reason:
            'A non-existent issue must not appear in the active repository index before archiving.',
      );
      expect(
        beforeArchival.snapshot.repositoryIndex.pathForKey(
          Ts153MissingIssueArchiveFixture.survivingIssueKey,
        ),
        Ts153MissingIssueArchiveFixture.survivingIssuePath,
        reason:
            'TRACK-122 should resolve to its active repository file before the missing archive attempt.',
      );
      expect(
        beforeArchival.missingIssueSearchResults,
        isEmpty,
        reason:
            'Searching for ${Ts153MissingIssueArchiveFixture.missingIssueKey} should return no active issues before archiving.',
      );
      expect(
        beforeArchival.activeIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts153MissingIssueArchiveFixture.survivingIssueKey],
        reason:
            'TRACK-122 should remain searchable before the missing archive attempt.',
      );
      expect(
        beforeArchival.activeIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            'TRACK-122 should remain active before the missing archive attempt.',
      );
      expect(
        beforeArchival.worktreeStatusLines,
        isEmpty,
        reason:
            'The seeded repository must start clean so the archive attempt is the only possible source of changes.',
      );

      final afterArchival = await fixture
          .archiveMissingIssueViaRepositoryService();

      expect(
        afterArchival.errorType,
        'TrackStateRepositoryException',
        reason:
            'Archiving a missing issue should surface a repository-domain not-found error instead of ${afterArchival.errorType}. '
            'Observed message: ${afterArchival.errorMessage}',
      );
      expect(
        afterArchival.errorType,
        isNot('NoSuchMethodError'),
        reason:
            'Archiving a missing issue must not regress to a low-level interface crash.',
      );
      expect(
        afterArchival.errorMessage,
        'Could not find repository artifacts for ${Ts153MissingIssueArchiveFixture.missingIssueKey}.',
        reason:
            'Archiving a missing issue should report a clear not-found error to clients.',
      );
      expect(
        afterArchival.errorStackTrace,
        isNot(contains("NoSuchMethodError: Class 'LocalTrackStateRepository'")),
        reason:
            'The stack trace should not contain the original missing-method regression.',
      );
      expect(
        afterArchival.missingIssueFileExists,
        isFalse,
        reason:
            'The failed archive must not create or restore ${afterArchival.missingIssuePath}.',
      );
      expect(
        afterArchival.snapshot.repositoryIndex.pathForKey(
          Ts153MissingIssueArchiveFixture.missingIssueKey,
        ),
        isNull,
        reason:
            'A missing issue must still be absent from the active repository index after the failed archive.',
      );
      expect(
        afterArchival.snapshot.repositoryIndex.pathForKey(
          Ts153MissingIssueArchiveFixture.survivingIssueKey,
        ),
        Ts153MissingIssueArchiveFixture.survivingIssuePath,
        reason:
            'The failed archive must not disturb TRACK-122 in the active repository index.',
      );
      expect(
        afterArchival.missingIssueSearchResults,
        isEmpty,
        reason:
            'Searching for ${Ts153MissingIssueArchiveFixture.missingIssueKey} should still return no active issues after the failed archive.',
      );
      expect(
        afterArchival.activeIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts153MissingIssueArchiveFixture.survivingIssueKey],
        reason:
            'TRACK-122 must remain searchable after the missing archive attempt fails.',
      );
      expect(
        afterArchival.activeIssueSearchResults.single.isArchived,
        isFalse,
        reason: 'The failed archive must not mark TRACK-122 as archived.',
      );
      expect(
        afterArchival.survivingIssueMarkdown,
        beforeArchival.survivingIssueMarkdown,
        reason:
            'The failed archive must not rewrite ${afterArchival.survivingIssuePath}.',
      );
      expect(
        afterArchival.headRevision,
        beforeArchival.headRevision,
        reason: 'The failed archive must not create a new Git commit.',
      );
      expect(
        afterArchival.worktreeStatusLines,
        isEmpty,
        reason:
            'The failed archive must leave the Git worktree clean, but `git status --short` returned ${afterArchival.worktreeStatusLines.join(' | ')}.',
      );
    },
  );
}
