import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';

import '../../fixtures/repositories/ts283_delete_parent_with_children_fixture.dart';

void main() {
  test(
    'TS-283 blocks deleting a parent issue while active child issues still exist',
    () async {
      final fixture = await Ts283DeleteParentWithChildrenFixture.create();
      addTearDown(fixture.dispose);

      final beforeDelete = await fixture.observeBeforeDeleteAttempt();

      expect(
        beforeDelete.parentIssue?.key,
        Ts283DeleteParentWithChildrenFixture.parentIssueKey,
        reason:
            'Precondition failed: ${Ts283DeleteParentWithChildrenFixture.parentIssueKey} must exist before the delete attempt starts.',
      );
      expect(
        beforeDelete.childIssue?.key,
        Ts283DeleteParentWithChildrenFixture.childIssueKey,
        reason:
            'Precondition failed: ${Ts283DeleteParentWithChildrenFixture.childIssueKey} must exist before the delete attempt starts.',
      );
      expect(
        beforeDelete.snapshot.repositoryIndex
            .entryForKey(Ts283DeleteParentWithChildrenFixture.parentIssueKey)
            ?.childKeys,
        [Ts283DeleteParentWithChildrenFixture.childIssueKey],
        reason:
            'Precondition failed: the repository index must expose ${Ts283DeleteParentWithChildrenFixture.childIssueKey} as an active child of ${Ts283DeleteParentWithChildrenFixture.parentIssueKey}.',
      );
      expect(
        beforeDelete.parentIssueFileExists,
        isTrue,
        reason:
            'Precondition failed: ${Ts283DeleteParentWithChildrenFixture.parentIssuePath} must exist before deletion is attempted.',
      );
      expect(
        beforeDelete.childIssueFileExists,
        isTrue,
        reason:
            'Precondition failed: ${Ts283DeleteParentWithChildrenFixture.childIssuePath} must exist before deletion is attempted.',
      );
      expect(
        beforeDelete.tombstoneDirectoryExists,
        isFalse,
        reason:
            'Precondition failed: no tombstone directory should exist before the blocked delete scenario begins.',
      );
      expect(
        beforeDelete.tombstoneFileExists,
        isFalse,
        reason:
            'Precondition failed: no tombstone file should exist before the blocked delete scenario begins.',
      );
      expect(
        beforeDelete.tombstoneIndexExists,
        isFalse,
        reason:
            'Precondition failed: no tombstone index should exist before the blocked delete scenario begins.',
      );
      expect(
        beforeDelete.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must start clean so any observed change comes from the delete attempt.',
      );

      final afterDelete = await fixture.attemptDeleteViaService();
      final failure = afterDelete.result?.failure;

      expect(
        afterDelete.result?.isSuccess,
        isFalse,
        reason:
            'Step 1 failed: deleteIssue should return a failed result when ${Ts283DeleteParentWithChildrenFixture.parentIssueKey} still has child issues.',
      );
      expect(
        failure,
        isNotNull,
        reason:
            'Step 2 failed: deleteIssue should populate a typed failure when deletion is blocked by child issues.',
      );
      expect(
        failure!.category,
        IssueMutationErrorCategory.validation,
        reason:
            'Expected result mismatch: the blocked delete must be classified as a validation failure.\n'
            'Actual failure: ${failure.message}',
      );
      expect(
        failure.message,
        Ts283DeleteParentWithChildrenFixture.expectedFailureMessage,
        reason:
            'Expected result mismatch: the failure message must explicitly state that deletion is blocked because child issues exist.\n'
            'Actual message: ${failure.message}',
      );
      expect(
        afterDelete.result?.value,
        isNull,
        reason:
            'Expected result mismatch: a blocked delete must not return a tombstone payload.',
      );

      expect(
        afterDelete.parentIssue?.key,
        Ts283DeleteParentWithChildrenFixture.parentIssueKey,
        reason:
            'Expected result mismatch: ${Ts283DeleteParentWithChildrenFixture.parentIssueKey} must still exist in the refreshed snapshot after the blocked delete.',
      );
      expect(
        afterDelete.childIssue?.key,
        Ts283DeleteParentWithChildrenFixture.childIssueKey,
        reason:
            'Expected result mismatch: ${Ts283DeleteParentWithChildrenFixture.childIssueKey} must still exist in the refreshed snapshot after the blocked delete.',
      );
      expect(
        afterDelete.parentIssueFileExists,
        isTrue,
        reason:
            'Expected result mismatch: ${Ts283DeleteParentWithChildrenFixture.parentIssuePath} must remain on disk after the blocked delete.',
      );
      expect(
        afterDelete.childIssueFileExists,
        isTrue,
        reason:
            'Expected result mismatch: ${Ts283DeleteParentWithChildrenFixture.childIssuePath} must remain on disk after the blocked delete.',
      );
      expect(
        afterDelete.parentIssueMarkdown,
        beforeDelete.parentIssueMarkdown,
        reason:
            'Expected result mismatch: the blocked delete must not rewrite the parent issue markdown.',
      );
      expect(
        afterDelete.childIssueMarkdown,
        beforeDelete.childIssueMarkdown,
        reason:
            'Expected result mismatch: the blocked delete must not rewrite the child issue markdown.',
      );
      expect(
        afterDelete.tombstoneDirectoryExists,
        isFalse,
        reason:
            'Expected result mismatch: the blocked delete must not create ${Ts283DeleteParentWithChildrenFixture.tombstoneDirectoryPath}.',
      );
      expect(
        afterDelete.tombstoneFileExists,
        isFalse,
        reason:
            'Expected result mismatch: the blocked delete must not create ${Ts283DeleteParentWithChildrenFixture.tombstonePath}.',
      );
      expect(
        afterDelete.tombstoneIndexExists,
        isFalse,
        reason:
            'Expected result mismatch: the blocked delete must not create ${Ts283DeleteParentWithChildrenFixture.tombstoneIndexPath}.',
      );
      expect(
        afterDelete.snapshot.repositoryIndex.deleted,
        isEmpty,
        reason:
            'Expected result mismatch: the blocked delete must not reserve a deleted tombstone entry in repository metadata.',
      );
      expect(
        afterDelete.headRevision,
        beforeDelete.headRevision,
        reason:
            'Expected result mismatch: the blocked delete must not create a new Git commit.',
      );
      expect(
        afterDelete.latestCommitSubject,
        beforeDelete.latestCommitSubject,
        reason:
            'Expected result mismatch: the latest visible commit should remain the original fixture seed commit after the blocked delete.',
      );
      expect(
        afterDelete.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: the blocked delete must leave the Git worktree clean, but `git status --short` returned ${afterDelete.worktreeStatusLines.join(' | ')}.',
      );

      expect(
        afterDelete.projectSearchResults.map((issue) => issue.key).toList(),
        containsAll(<String>[
          Ts283DeleteParentWithChildrenFixture.parentIssueKey,
          Ts283DeleteParentWithChildrenFixture.childIssueKey,
        ]),
        reason:
            'Human-style verification failed: integrated clients searching the project should still see both the parent issue and its active child after the blocked delete.',
      );
      expect(
        afterDelete.parentSearchResults.map((issue) => issue.key).toList(),
        [Ts283DeleteParentWithChildrenFixture.parentIssueKey],
        reason:
            'Human-style verification failed: searching specifically for the parent issue should still return ${Ts283DeleteParentWithChildrenFixture.parentIssueKey} after deletion is blocked.',
      );
      expect(
        afterDelete.childSearchResults.map((issue) => issue.key).toList(),
        [Ts283DeleteParentWithChildrenFixture.childIssueKey],
        reason:
            'Human-style verification failed: searching specifically for the child issue should still return ${Ts283DeleteParentWithChildrenFixture.childIssueKey} after deletion is blocked.',
      );
      expect(
        afterDelete.snapshot.repositoryIndex
            .entryForKey(Ts283DeleteParentWithChildrenFixture.parentIssueKey)
            ?.childKeys,
        [Ts283DeleteParentWithChildrenFixture.childIssueKey],
        reason:
            'Human-style verification failed: the parent issue should still expose its active child relationship after the blocked delete.',
      );
      expect(
        afterDelete.childIssue?.epicKey,
        Ts283DeleteParentWithChildrenFixture.parentIssueKey,
        reason:
            'Human-style verification failed: the child issue should still belong to ${Ts283DeleteParentWithChildrenFixture.parentIssueKey} after the blocked delete.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
