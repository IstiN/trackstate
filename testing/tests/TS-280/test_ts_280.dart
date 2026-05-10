import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../fixtures/repositories/ts280_terminal_transition_default_resolution_fixture.dart';

void main() {
  test(
    'TS-280 transitionIssue applies the only configured resolution when moving an issue to Done without an explicit resolution',
    () async {
      final fixture =
          await Ts280TerminalTransitionDefaultResolutionFixture.create();
      addTearDown(fixture.dispose);

      final beforeTransition = await fixture.observeBeforeTransition();

      expect(
        beforeTransition.issue.key,
        Ts280TerminalTransitionDefaultResolutionFixture.issueKey,
        reason:
            'Precondition failed: ${Ts280TerminalTransitionDefaultResolutionFixture.issueKey} must exist before the transition begins.',
      );
      expect(
        beforeTransition.issue.status,
        IssueStatus.inProgress,
        reason:
            'Precondition failed: the seeded issue must start In Progress before TS-280 transitions it to Done.',
      );
      expect(
        beforeTransition.issue.statusId,
        'in-progress',
        reason:
            'Precondition failed: the seeded issue must store the canonical in-progress status id before transitionIssue runs.',
      );
      expect(
        beforeTransition.issue.resolutionId,
        isNull,
        reason:
            'Precondition failed: the seeded issue must not already have a resolution before the transition omits one.',
      );
      expect(
        beforeTransition.snapshot.project.resolutionDefinitions,
        hasLength(1),
        reason:
            'Precondition failed: TS-280 requires exactly one configured terminal resolution so the service can auto-apply it.',
      );
      expect(
        beforeTransition.snapshot.project.resolutionDefinitions.single.id,
        Ts280TerminalTransitionDefaultResolutionFixture.expectedResolutionId,
        reason:
            'Precondition failed: the only configured resolution should be ${Ts280TerminalTransitionDefaultResolutionFixture.expectedResolutionId}.',
      );
      expect(
        beforeTransition.workflowJson,
        contains('"from":"in-progress"'),
        reason:
            'Precondition failed: config/workflows.json must explicitly allow the transition from In Progress.',
      );
      expect(
        beforeTransition.workflowJson,
        contains('"to":"done"'),
        reason:
            'Precondition failed: config/workflows.json must explicitly allow the transition to Done.',
      );
      expect(
        beforeTransition.resolutionsJson,
        contains('"id":"fixed"'),
        reason:
            'Precondition failed: config/resolutions.json must expose the only allowed terminal resolution.',
      );
      expect(
        beforeTransition.issueMarkdown,
        isNot(contains(RegExp(r'^resolution:', multiLine: true))),
        reason:
            'Precondition failed: the issue markdown must not already persist a resolution before transitionIssue is invoked without one.',
      );
      expect(
        beforeTransition.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must start clean so any later change comes from the transition itself.',
      );

      final afterTransition = await fixture.transitionWithoutResolution();

      expect(
        afterTransition.result.isSuccess,
        isTrue,
        reason:
            'Step 2 failed: transitionIssue should succeed when moving ${Ts280TerminalTransitionDefaultResolutionFixture.issueKey} to Done with one configured resolution.',
      );
      expect(
        afterTransition.result.failure,
        isNull,
        reason:
            'Step 2 failed: transitionIssue unexpectedly returned a failure instead of auto-applying the only configured resolution.',
      );
      expect(
        afterTransition.result.revision,
        isNotNull,
        reason:
            'Step 2 failed: a successful transition should report the written file revision.',
      );
      expect(
        afterTransition.result.value,
        isNotNull,
        reason:
            'Step 2 failed: a successful transition should return the refreshed issue payload.',
      );

      final returnedIssue = afterTransition.result.value!;
      expect(
        returnedIssue.status,
        IssueStatus.done,
        reason:
            'Expected result mismatch: the returned issue payload should expose Done after the transition succeeds.',
      );
      expect(
        returnedIssue.statusId,
        Ts280TerminalTransitionDefaultResolutionFixture.expectedTargetStatusId,
        reason:
            'Expected result mismatch: the returned issue payload should persist the canonical done status id.',
      );
      expect(
        returnedIssue.resolutionId,
        Ts280TerminalTransitionDefaultResolutionFixture.expectedResolutionId,
        reason:
            'Expected result mismatch: the returned issue payload should auto-apply the only configured resolution id.',
      );

      expect(
        afterTransition.issue.status,
        IssueStatus.done,
        reason:
            'Step 3 failed: reloading the issue from the repository should show Done after transitionIssue succeeds.',
      );
      expect(
        afterTransition.issue.statusId,
        Ts280TerminalTransitionDefaultResolutionFixture.expectedTargetStatusId,
        reason:
            'Step 3 failed: the persisted issue should store status: done after the transition.',
      );
      expect(
        afterTransition.issue.resolutionId,
        Ts280TerminalTransitionDefaultResolutionFixture.expectedResolutionId,
        reason:
            'Step 3 failed: the persisted issue should store resolution: fixed after omitting resolutionId on the Done transition.',
      );
      expect(
        afterTransition.issue.description,
        Ts280TerminalTransitionDefaultResolutionFixture.expectedDescription,
        reason:
            'Expected result mismatch: transitioning the issue should preserve the user-visible description content.',
      );
      expect(
        afterTransition.issueMarkdown,
        contains(RegExp(r'^status:\s*done$', multiLine: true)),
        reason:
            'Step 3 failed: main.md must persist `status: done` after the transition.\n'
            'Actual markdown:\n${afterTransition.issueMarkdown}',
      );
      expect(
        afterTransition.issueMarkdown,
        contains(RegExp(r'^resolution:\s*fixed$', multiLine: true)),
        reason:
            'Step 3 failed: main.md must persist `resolution: fixed` when the only configured terminal resolution is auto-applied.\n'
            'Actual markdown:\n${afterTransition.issueMarkdown}',
      );
      expect(
        afterTransition.headRevision,
        isNot(beforeTransition.headRevision),
        reason:
            'Expected result mismatch: a successful transition should create a new Git commit.',
      );
      expect(
        afterTransition.latestCommitSubject,
        Ts280TerminalTransitionDefaultResolutionFixture.expectedCommitSubject,
        reason:
            'Expected result mismatch: the persisted commit message should describe moving the issue to Done.',
      );
      expect(
        afterTransition.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: the successful transition must leave the worktree clean, but `git status --short` returned ${afterTransition.worktreeStatusLines.join(' | ')}.',
      );

      final searchMatches = afterTransition.searchResults
          .where(
            (issue) =>
                issue.key ==
                Ts280TerminalTransitionDefaultResolutionFixture.issueKey,
          )
          .toList(growable: false);
      expect(
        searchMatches,
        hasLength(1),
        reason:
            'Human-style verification failed: a client searching for ${Ts280TerminalTransitionDefaultResolutionFixture.issueKey} should still find exactly one issue after the transition.',
      );
      final visibleIssue = searchMatches.single;
      expect(
        afterTransition.snapshot.project.statusLabel(visibleIssue.statusId),
        Ts280TerminalTransitionDefaultResolutionFixture
            .expectedTargetStatusLabel,
        reason:
            'Human-style verification failed: repository consumers should see the Done status label after the transition.',
      );
      expect(
        afterTransition.snapshot.project.resolutionLabel(
          visibleIssue.resolutionId!,
        ),
        Ts280TerminalTransitionDefaultResolutionFixture.expectedResolutionLabel,
        reason:
            'Human-style verification failed: repository consumers should see the Fixed resolution label after the service auto-applies it.',
      );
      expect(
        visibleIssue.summary,
        'Automatically apply the terminal resolution when moving to Done',
        reason:
            'Human-style verification failed: the issue should remain identifiable by the same summary after the transition.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
