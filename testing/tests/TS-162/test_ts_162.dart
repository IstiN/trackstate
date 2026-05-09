import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts162_missing_issue_update_fixture.dart';

void main() {
  test(
    'TS-162 rejects updating a missing issue with a repository not-found error instead of a low-level provider error',
    () async {
      final fixture = await Ts162MissingIssueUpdateFixture.create();
      addTearDown(fixture.dispose);

      final beforeUpdate = await fixture.observeBeforeUpdateState();

      expect(
        beforeUpdate.missingIssueFileExists,
        isFalse,
        reason:
            '${Ts162MissingIssueUpdateFixture.missingIssueKey} must be absent before the update attempt begins.',
      );
      expect(
        beforeUpdate.snapshot.repositoryIndex.pathForKey(
          Ts162MissingIssueUpdateFixture.missingIssueKey,
        ),
        isNull,
        reason:
            'A non-existent issue must not appear in the active repository index before updating.',
      );
      expect(
        beforeUpdate.snapshot.repositoryIndex.pathForKey(
          Ts162MissingIssueUpdateFixture.survivingIssueKey,
        ),
        Ts162MissingIssueUpdateFixture.survivingIssuePath,
        reason:
            'TRACK-122 should resolve to its active repository file before the missing update attempt.',
      );
      expect(
        beforeUpdate.missingIssueSearchResults,
        isEmpty,
        reason:
            'Searching for ${Ts162MissingIssueUpdateFixture.missingIssueKey} should return no active issues before updating.',
      );
      expect(
        beforeUpdate.activeIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts162MissingIssueUpdateFixture.survivingIssueKey],
        reason:
            'TRACK-122 should remain searchable before the missing update attempt.',
      );
      expect(
        beforeUpdate.activeIssueSearchResults.single.isArchived,
        isFalse,
        reason:
            'TRACK-122 should remain active before the missing update attempt.',
      );
      expect(
        beforeUpdate.worktreeStatusLines,
        isEmpty,
        reason:
            'The seeded repository must start clean so the update attempt is the only possible source of changes.',
      );

      final afterUpdate = await fixture
          .updateMissingIssueViaRepositoryService();

      expect(
        afterUpdate.errorType,
        'TrackStateRepositoryException',
        reason:
            'Updating a missing issue should surface a repository-domain not-found error instead of ${afterUpdate.errorType}.',
      );
      expect(
        afterUpdate.errorType,
        isNot('TrackStateProviderException'),
        reason:
            'Updating a missing issue must not leak a low-level provider error to clients.',
      );
      expect(
        afterUpdate.errorMessage,
        'Could not find repository artifacts for ${Ts162MissingIssueUpdateFixture.missingIssueKey}.',
        reason:
            'Updating a missing issue should report a clear not-found error to clients.',
      );
      expect(
        afterUpdate.errorMessage,
        isNot(contains('Git command failed: git show')),
        reason:
            'The user-visible error must not expose the raw Git provider command.',
      );
      expect(
        afterUpdate.missingIssueFileExists,
        isFalse,
        reason:
            'The failed update must not create or restore ${afterUpdate.missingIssuePath}.',
      );
      expect(
        afterUpdate.snapshot.repositoryIndex.pathForKey(
          Ts162MissingIssueUpdateFixture.missingIssueKey,
        ),
        isNull,
        reason:
            'A missing issue must still be absent from the active repository index after the failed update.',
      );
      expect(
        afterUpdate.snapshot.repositoryIndex.pathForKey(
          Ts162MissingIssueUpdateFixture.survivingIssueKey,
        ),
        Ts162MissingIssueUpdateFixture.survivingIssuePath,
        reason:
            'The failed update must not disturb TRACK-122 in the active repository index.',
      );
      expect(
        afterUpdate.missingIssueSearchResults,
        isEmpty,
        reason:
            'Searching for ${Ts162MissingIssueUpdateFixture.missingIssueKey} should still return no active issues after the failed update.',
      );
      expect(
        afterUpdate.activeIssueSearchResults.map((issue) => issue.key).toList(),
        [Ts162MissingIssueUpdateFixture.survivingIssueKey],
        reason:
            'TRACK-122 must remain searchable after the missing update attempt fails.',
      );
      expect(
        afterUpdate.activeIssueSearchResults.single.isArchived,
        isFalse,
        reason: 'The failed update must not mark TRACK-122 as archived.',
      );
      expect(
        afterUpdate.survivingIssueMarkdown,
        beforeUpdate.survivingIssueMarkdown,
        reason:
            'The failed update must not rewrite ${afterUpdate.survivingIssuePath}.',
      );
      expect(
        afterUpdate.headRevision,
        beforeUpdate.headRevision,
        reason: 'The failed update must not create a new Git commit.',
      );
      expect(
        afterUpdate.worktreeStatusLines,
        isEmpty,
        reason:
            'The failed update must leave the Git worktree clean, but `git status --short` returned ${afterUpdate.worktreeStatusLines.join(' | ')}.',
      );
    },
  );
}
