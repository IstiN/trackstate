import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';

import '../../fixtures/repositories/ts285_stale_revision_conflict_fixture.dart';

void main() {
  test(
    'TS-285 returns a typed conflict result with the current revision after updateFields loses an optimistic concurrency race',
    () async {
      final fixture = await Ts285StaleRevisionConflictFixture.create();
      addTearDown(fixture.dispose);

      final beforeConflict = await fixture.observeBeforeConflict();

      expect(
        beforeConflict.issue.key,
        Ts285StaleRevisionConflictFixture.issueKey,
        reason:
            'Precondition failed: ${Ts285StaleRevisionConflictFixture.issueKey} must exist before the stale revision scenario starts.',
      );
      expect(
        beforeConflict.issue.description,
        Ts285StaleRevisionConflictFixture.originalDescription,
        reason:
            'Precondition failed: the seed issue description must start at the original committed revision before TS-285 injects a concurrent update.',
      );
      expect(
        beforeConflict.issueFileRevision,
        isNotEmpty,
        reason:
            'Precondition failed: the original issue file revision must be readable before updateFields runs.',
      );
      expect(
        beforeConflict.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the repository must start clean so the concurrent commit is the only source of revision drift.',
      );

      final afterConflict = await fixture.triggerStaleRevisionConflict();
      final failure = afterConflict.result.failure;

      expect(
        afterConflict.injectedFileRevision,
        isNotNull,
        reason:
            'Step 1 failed: TS-285 did not inject the concurrent commit needed to make updateFields use a stale expected revision.',
      );
      expect(
        afterConflict.injectedFileRevision,
        isNot(beforeConflict.issueFileRevision),
        reason:
            'Step 1 failed: the injected concurrent commit did not advance the issue file revision.',
      );
      expect(
        afterConflict.issue.description,
        Ts285StaleRevisionConflictFixture.concurrentDescription,
        reason:
            'Human-style verification failed: after the conflict, repository consumers should still see the newer concurrent description instead of the stale updateFields description.',
      );
      expect(
        afterConflict.issue.description,
        isNot(Ts285StaleRevisionConflictFixture.attemptedDescription),
        reason:
            'Human-style verification failed: the stale updateFields attempt should not overwrite the description a user sees after the concurrent save wins.',
      );
      expect(
        afterConflict.latestCommitSubject,
        afterConflict.injectedCommitSubject,
        reason:
            'Human-style verification failed: the most recent visible commit should be the concurrent update that caused the stale revision conflict.',
      );
      expect(
        afterConflict.worktreeStatusLines,
        isEmpty,
        reason:
            'Human-style verification failed: the failed stale save should leave the repository worktree clean, but `git status --short` returned ${afterConflict.worktreeStatusLines.join(' | ')}.',
      );

      expect(
        afterConflict.result.isSuccess,
        isFalse,
        reason:
            'Step 2 failed: updateFields should return a failed typed result after the revision becomes stale, but it returned success with revision ${afterConflict.result.revision}.',
      );
      expect(
        failure,
        isNotNull,
        reason:
            'Step 2 failed: updateFields should populate the failure field when the optimistic concurrency check fails.',
      );
      expect(
        failure!.category,
        IssueMutationErrorCategory.conflict,
        reason:
            'Step 2 failed: the typed result should classify a stale revision as conflict.\n'
            'Actual failure: ${failure.message}\n'
            'Actual details: ${failure.details}',
      );
      expect(
        failure.message,
        contains('changed in the current branch'),
        reason:
            'Human-style verification failed: the visible failure message should explain that another change already updated the issue.\n'
            'Actual message: ${failure.message}',
      );
      expect(
        failure.message,
        contains(afterConflict.currentFileRevision),
        reason:
            'Human-style verification failed: the visible failure message should show the current issue revision the caller needs to recover.\n'
            'Actual message: ${failure.message}',
      );
      expect(
        failure.details['currentRevision'],
        afterConflict.currentFileRevision,
        reason:
            'Expected result failed: the typed conflict result must expose the actual current revision in a machine-readable field so callers can recover without parsing the message.\n'
            'Observed details: ${failure.details}\n'
            'Visible message: ${failure.message}',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
