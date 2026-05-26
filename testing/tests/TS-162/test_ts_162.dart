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

      final failures = <String>[];
      final activeIssueKeys = afterUpdate.activeIssueSearchResults
          .map((issue) => issue.key)
          .toList(growable: false);

      if (!_isAcceptedDomainNotFoundError(afterUpdate.errorType)) {
        failures.add(
          'Step 2 failed: expected a repository-domain not-found error '
          '(TrackStateRepositoryException or a dedicated issue-not-found '
          'exception), but received ${afterUpdate.errorType}. Error message: '
          '${afterUpdate.errorMessage}.',
        );
      }
      if (afterUpdate.errorType == 'TrackStateProviderException') {
        failures.add(
          'Step 2 failed: the repository leaked TrackStateProviderException to '
          'the caller instead of translating it to a repository-domain error.',
        );
      }
      if (afterUpdate.errorMessage !=
          'Could not find repository artifacts for ${Ts162MissingIssueUpdateFixture.missingIssueKey}.') {
        failures.add(
          'Step 2 failed: expected the user-visible error message '
          '"Could not find repository artifacts for '
          '${Ts162MissingIssueUpdateFixture.missingIssueKey}." but observed '
          '"${afterUpdate.errorMessage}".',
        );
      }
      if ((afterUpdate.errorMessage ?? '').contains(
        'Git command failed: git show',
      )) {
        failures.add(
          'Step 2 failed: the user-visible error still exposed the raw Git '
          'provider command: "${afterUpdate.errorMessage}".',
        );
      }
      if (afterUpdate.missingIssueFileExists) {
        failures.add(
          'Postcondition failed: the update attempt created or restored '
          '${afterUpdate.missingIssuePath}.',
        );
      }
      if (afterUpdate.snapshot.repositoryIndex.pathForKey(
            Ts162MissingIssueUpdateFixture.missingIssueKey,
          ) !=
          null) {
        failures.add(
          'Postcondition failed: ${Ts162MissingIssueUpdateFixture.missingIssueKey} '
          'appeared in the active repository index after the failed update.',
        );
      }
      if (afterUpdate.snapshot.repositoryIndex.pathForKey(
            Ts162MissingIssueUpdateFixture.survivingIssueKey,
          ) !=
          Ts162MissingIssueUpdateFixture.survivingIssuePath) {
        failures.add(
          'Postcondition failed: TRACK-122 no longer resolved to '
          '${Ts162MissingIssueUpdateFixture.survivingIssuePath} after the failed update.',
        );
      }
      if (afterUpdate.missingIssueSearchResults.isNotEmpty) {
        failures.add(
          'Postcondition failed: searching for '
          '${Ts162MissingIssueUpdateFixture.missingIssueKey} returned '
          '${afterUpdate.missingIssueSearchResults.map((issue) => issue.key).toList()} '
          'after the failed update.',
        );
      }
      if (activeIssueKeys.length != 1 ||
          activeIssueKeys.single !=
              Ts162MissingIssueUpdateFixture.survivingIssueKey) {
        failures.add(
          'Postcondition failed: active issue search returned '
          '$activeIssueKeys '
          'instead of [${Ts162MissingIssueUpdateFixture.survivingIssueKey}] '
          'after the failed update.',
        );
      }
      if (afterUpdate.activeIssueSearchResults.length != 1 ||
          afterUpdate.activeIssueSearchResults.single.isArchived) {
        failures.add(
          'Postcondition failed: TRACK-122 should remain the sole active '
          'non-archived issue after the failed update, but observed '
          '${afterUpdate.activeIssueSearchResults.map((issue) => '${issue.key}(archived=${issue.isArchived})').toList()}.',
        );
      }
      if (afterUpdate.survivingIssueMarkdown !=
          beforeUpdate.survivingIssueMarkdown) {
        failures.add(
          'Postcondition failed: ${afterUpdate.survivingIssuePath} was rewritten '
          'by the failed update attempt.',
        );
      }
      if (afterUpdate.headRevision != beforeUpdate.headRevision) {
        failures.add(
          'Postcondition failed: Git HEAD changed from '
          '${beforeUpdate.headRevision} to ${afterUpdate.headRevision}.',
        );
      }
      if (afterUpdate.worktreeStatusLines.isNotEmpty) {
        failures.add(
          'Postcondition failed: git status --short returned '
          '${afterUpdate.worktreeStatusLines.join(' | ')} after the failed update.',
        );
      }

      if (failures.isNotEmpty) {
        fail(failures.join(' '));
      }
    },
  );
}

bool _isAcceptedDomainNotFoundError(String? errorType) {
  if (errorType == 'TrackStateRepositoryException') {
    return true;
  }
  if (errorType == null) {
    return false;
  }

  final normalizedType = errorType.toLowerCase();
  return normalizedType.contains('notfound') &&
      (normalizedType.contains('issue') ||
          normalizedType.contains('repository'));
}
