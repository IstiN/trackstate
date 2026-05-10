import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts281_reopen_issue_resolution_fixture.dart';

void main() {
  test(
    'TS-281 reopens a done issue to to-do and clears the persisted resolution',
    () async {
      final fixture = await Ts281ReopenIssueResolutionFixture.create();
      addTearDown(fixture.dispose);

      final beforeTransition = await fixture.observeRepositoryState();

      expect(
        beforeTransition.issue.statusId,
        Ts281ReopenIssueResolutionFixture.doneStatusId,
        reason:
            'Precondition failed: ${Ts281ReopenIssueResolutionFixture.issueKey} must start in done before Step 1 reopens it.',
      );
      expect(
        beforeTransition.issue.resolutionId,
        Ts281ReopenIssueResolutionFixture.resolutionId,
        reason:
            'Precondition failed: ${Ts281ReopenIssueResolutionFixture.issueKey} must start with resolution=${Ts281ReopenIssueResolutionFixture.resolutionId} before Step 1 reopens it.',
      );
      expect(
        beforeTransition.issueMarkdown,
        allOf(contains('status: done'), contains('resolution: fixed')),
        reason:
            'Precondition failed: ${Ts281ReopenIssueResolutionFixture.issuePath} must persist a done/fixed frontmatter state before Step 1 runs.\nObserved markdown:\n${beforeTransition.issueMarkdown}',
      );
      expect(
        beforeTransition.searchResults.map((issue) => issue.key).toList(),
        [Ts281ReopenIssueResolutionFixture.issueKey],
        reason:
            'Human-style precondition failed: repository search should show only ${Ts281ReopenIssueResolutionFixture.issueKey} before reopening.',
      );
      expect(
        beforeTransition.worktreeStatusLines,
        isEmpty,
        reason:
            'Precondition failed: the seeded repository must start clean, but `git status --short` returned ${beforeTransition.worktreeStatusLines.join(' | ')}.',
      );

      final result = await fixture.reopenIssue();
      final afterTransition = await fixture.observeRepositoryState();

      expect(
        result.isSuccess,
        isTrue,
        reason:
            'Step 1 failed: transitionIssue should succeed when reopening ${Ts281ReopenIssueResolutionFixture.issueKey} from done to to-do, but returned ${result.failure?.message ?? 'an unknown failure'}.',
      );
      expect(
        result.value,
        isNotNull,
        reason:
            'Step 1 failed: transitionIssue succeeded without returning the updated issue payload.',
      );
      expect(
        result.revision,
        isNotEmpty,
        reason:
            'Step 1 failed: transitionIssue should expose the persisted revision after reopening ${Ts281ReopenIssueResolutionFixture.issueKey}.',
      );
      expect(
        result.value?.statusId,
        Ts281ReopenIssueResolutionFixture.reopenedStatusId,
        reason:
            'Step 1 failed: transitionIssue did not return status=${Ts281ReopenIssueResolutionFixture.reopenedStatusId}.',
      );
      expect(
        result.value?.resolutionId,
        isNull,
        reason:
            'Step 1 failed: transitionIssue should clear resolution in the returned issue payload when moving away from done.',
      );

      expect(
        afterTransition.issue.statusId,
        Ts281ReopenIssueResolutionFixture.reopenedStatusId,
        reason:
            'Step 2 failed: the reloaded issue should persist status=${Ts281ReopenIssueResolutionFixture.reopenedStatusId} after reopening.',
      );
      expect(
        afterTransition.issue.resolutionId,
        isNull,
        reason:
            'Step 2 failed: the reloaded issue should persist a cleared resolution after reopening from done.',
      );
      expect(
        afterTransition.issueMarkdown,
        contains(
          'status: ${Ts281ReopenIssueResolutionFixture.reopenedStatusId}',
        ),
        reason:
            'Step 2 failed: ${Ts281ReopenIssueResolutionFixture.issuePath} did not persist the reopened status in frontmatter.\nObserved markdown:\n${afterTransition.issueMarkdown}',
      );
      expect(
        afterTransition.issueMarkdown,
        contains('resolution: null'),
        reason:
            'Step 2 failed: ${Ts281ReopenIssueResolutionFixture.issuePath} did not nullify resolution in frontmatter after reopening.\nObserved markdown:\n${afterTransition.issueMarkdown}',
      );
      expect(
        afterTransition.issueMarkdown.contains('resolution: fixed'),
        isFalse,
        reason:
            'Step 2 failed: ${Ts281ReopenIssueResolutionFixture.issuePath} still persisted resolution=fixed after reopening.\nObserved markdown:\n${afterTransition.issueMarkdown}',
      );
      expect(
        afterTransition.latestCommitSubject,
        'Move ${Ts281ReopenIssueResolutionFixture.issueKey} to ${Ts281ReopenIssueResolutionFixture.reopenedStatusLabel}',
        reason:
            'Step 2 failed: reopening should create the expected persistence commit subject.',
      );
      expect(
        afterTransition.worktreeStatusLines,
        isEmpty,
        reason:
            'Expected result mismatch: reopening should leave the repository worktree clean, but `git status --short` returned ${afterTransition.worktreeStatusLines.join(' | ')}.',
      );

      expect(
        afterTransition.searchResults.map((issue) => issue.key).toList(),
        [Ts281ReopenIssueResolutionFixture.issueKey],
        reason:
            'Human-style verification failed: repository search should still show ${Ts281ReopenIssueResolutionFixture.issueKey} after reopening.',
      );
      expect(
        afterTransition.searchResults.single.summary,
        Ts281ReopenIssueResolutionFixture.issueSummary,
        reason:
            'Human-style verification failed: repository search should still expose the visible issue summary after reopening.',
      );
      expect(
        afterTransition.snapshot.project.statusLabel(
          afterTransition.issue.statusId,
        ),
        Ts281ReopenIssueResolutionFixture.reopenedStatusLabel,
        reason:
            'Human-style verification failed: repository consumers should label the reopened issue as "${Ts281ReopenIssueResolutionFixture.reopenedStatusLabel}".',
      );
      expect(
        afterTransition.searchResults.single.resolutionId,
        isNull,
        reason:
            'Human-style verification failed: repository consumers should observe no resolution after reopening the issue.',
      );
      expect(
        afterTransition.headRevision,
        isNot(beforeTransition.headRevision),
        reason:
            'Expected result mismatch: reopening should persist a new Git revision.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
