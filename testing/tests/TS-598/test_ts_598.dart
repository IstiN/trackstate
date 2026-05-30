import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';

import 'support/ts598_missing_issue_mutation_fixture.dart';

void main() {
  test(
    'TS-598 returns a typed not-found mutation result when updateFields targets a non-existent issue',
    () async {
      final fixture = await Ts598MissingIssueMutationFixture.create();
      addTearDown(fixture.dispose);

      final beforeMutation = await fixture.observeBeforeMutation();

      expect(
        beforeMutation.missingIssueFileExists,
        isFalse,
        reason:
            'Precondition failed: ${Ts598MissingIssueMutationFixture.missingIssueKey} must not exist on disk before the missing mutation scenario begins.',
      );
      expect(
        beforeMutation.snapshot.repositoryIndex.pathForKey(
          Ts598MissingIssueMutationFixture.missingIssueKey,
        ),
        isNull,
        reason:
            'Precondition failed: the repository index must not resolve ${Ts598MissingIssueMutationFixture.missingIssueKey} before updateFields runs.',
      );
      expect(
        beforeMutation.survivingIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts598MissingIssueMutationFixture.survivingIssueKey],
        reason:
            'Precondition failed: ${Ts598MissingIssueMutationFixture.survivingIssueKey} must remain searchable before the missing mutation attempt.',
      );
      expect(
        beforeMutation.projectSearchResults.map((issue) => issue.key).toList(),
        [Ts598MissingIssueMutationFixture.survivingIssueKey],
        reason:
            'Precondition failed: repository consumers should see only the seeded surviving issue before the missing mutation attempt.',
      );
      expect(
        beforeMutation.missingIssueSearchResults,
        isEmpty,
        reason:
            'Precondition failed: searching for ${Ts598MissingIssueMutationFixture.missingIssueKey} must return no issues before updateFields runs.',
      );
      expect(
        beforeMutation.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must start clean so the missing mutation attempt is the only possible source of changes.',
      );

      final afterMutation = await fixture.attemptMissingIssueUpdateFields();
      final failure = afterMutation.result?.failure;

      expect(
        afterMutation.result?.isSuccess,
        isFalse,
        reason:
            'Step 1 failed: updateFields should return a failed typed result when ${Ts598MissingIssueMutationFixture.missingIssueKey} is absent from the repository index.',
      );
      expect(
        afterMutation.result?.operation,
        'update-fields',
        reason:
            'Step 1 failed: the mutation envelope should identify updateFields as the failed operation.',
      );
      expect(
        afterMutation.result?.issueKey,
        Ts598MissingIssueMutationFixture.missingIssueKey,
        reason:
            'Step 1 failed: the typed mutation envelope should retain the requested missing issue key.',
      );
      expect(
        failure,
        isNotNull,
        reason:
            'Step 2 failed: a missing issue mutation must populate the typed failure envelope.',
      );
      expect(
        failure!.category,
        IssueMutationErrorCategory.notFound,
        reason:
            'Step 2 failed: the typed mutation result must classify the missing issue as not-found.\n'
            'Actual failure: ${failure.message}',
      );
      expect(
        failure.message,
        'Could not find issue ${Ts598MissingIssueMutationFixture.missingIssueKey} for update-fields.',
        reason:
            'Step 2 failed: the failure message must explain that the requested issue could not be resolved for updateFields.\n'
            'Actual message: ${failure.message}',
      );
      expect(
        failure.details,
        isEmpty,
        reason:
            'Step 2 failed: the not-found envelope should not invent unrelated detail fields when issue resolution fails immediately.',
      );
      expect(
        afterMutation.result?.value,
        isNull,
        reason:
            'Expected result mismatch: a failed missing-issue mutation must not return an updated issue payload.',
      );
      expect(
        afterMutation.result?.revision,
        isNull,
        reason:
            'Expected result mismatch: a failed missing-issue mutation must not report a revision.',
      );

      expect(
        afterMutation.missingIssueFileExists,
        isFalse,
        reason:
            'Expected result mismatch: the failed mutation must not create ${Ts598MissingIssueMutationFixture.missingIssuePath}.',
      );
      expect(
        afterMutation.snapshot.repositoryIndex.pathForKey(
          Ts598MissingIssueMutationFixture.missingIssueKey,
        ),
        isNull,
        reason:
            'Expected result mismatch: the missing issue must still be absent from the repository index after the failed mutation.',
      );
      expect(
        afterMutation.snapshot.repositoryIndex.pathForKey(
          Ts598MissingIssueMutationFixture.survivingIssueKey,
        ),
        Ts598MissingIssueMutationFixture.survivingIssuePath,
        reason:
            'Expected result mismatch: the failed mutation must not disturb the surviving issue index entry.',
      );
      expect(
        afterMutation.survivingIssueMarkdown,
        beforeMutation.survivingIssueMarkdown,
        reason:
            'Expected result mismatch: the failed mutation must not rewrite the surviving issue markdown.',
      );
      expect(
        afterMutation.headRevision,
        beforeMutation.headRevision,
        reason:
            'Expected result mismatch: the failed missing-issue mutation must not create a new Git commit.',
      );
      expect(
        afterMutation.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: the failed missing-issue mutation must leave the Git worktree clean, but `git status --short` returned ${afterMutation.worktreeStatusLines.join(' | ')}.',
      );

      expect(
        afterMutation.missingIssueSearchResults,
        isEmpty,
        reason:
            'Human-style verification failed: repository consumers searching for ${Ts598MissingIssueMutationFixture.missingIssueKey} should still see no matching issue after the failed mutation attempt.',
      );
      expect(
        afterMutation.survivingIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts598MissingIssueMutationFixture.survivingIssueKey],
        reason:
            'Human-style verification failed: searching specifically for the surviving issue should still return ${Ts598MissingIssueMutationFixture.survivingIssueKey} after the missing mutation attempt.',
      );
      expect(
        afterMutation.projectSearchResults.map((issue) => issue.key).toList(),
        [Ts598MissingIssueMutationFixture.survivingIssueKey],
        reason:
            'Human-style verification failed: integrated clients listing project issues should still see only the surviving issue after the failed mutation attempt.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
