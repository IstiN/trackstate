import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/reactive_issue_detail_screen.dart';
import '../../core/models/action_availability.dart';
import '../../fixtures/reactive_issue_detail_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-104 updates issue detail write affordances when canWrite becomes false during an active session',
    (tester) async {
      final semantics = tester.ensureSemantics();
      ReactiveIssueDetailScreenHandle? screen;

      try {
        const issueKey = 'TRACK-12';
        const issueSummary = 'Implement Git sync service';
        const issueCriterion = 'Push issue updates as commits.';

        screen = await launchReactiveIssueDetailFixture(tester);
        final writableState = await _openTargetIssue(
          screen: screen,
          targetIssueKey: issueKey,
          targetSummary: issueSummary,
        );

        await screen.synchronizeSessionToReadOnly();

        final readOnlyState = _IssueDetailState(
          transition: screen.transitionAction(issueKey),
          edit: screen.editAction(issueKey),
          comment: screen.commentAction(issueKey),
          hasReadOnlyExplanation: screen.hasReadOnlyExplanation(issueKey),
        );

        final failures = <String>[];

        if (!writableState.transition.enabled) {
          failures.add(
            'Step 1 failed: Transition was not enabled before the capability downgrade. '
            'Observed writable state: ${writableState.describe()}.',
          );
        }
        if (!writableState.edit.enabled) {
          failures.add(
            'Step 1 failed: Edit was not enabled before the capability downgrade. '
            'Observed writable state: ${writableState.describe()}.',
          );
        }
        if (writableState.hasReadOnlyExplanation) {
          failures.add(
            'Step 1 failed: the read-only explanation banner was already visible before permissions changed. '
            'Observed writable state: ${writableState.describe()}.',
          );
        }

        if (!screen.showsIssueDetail(issueKey) ||
            !screen.showsIssueKey(issueKey) ||
            !screen.showsSummary(issueKey, issueSummary) ||
            !screen.showsAcceptanceCriterion(issueKey, issueCriterion)) {
          failures.add(
            'Step 3 failed: the open issue detail surface did not stay on TRACK-12 after the capability sync, so the scenario no longer reflects a live in-place permission update.',
          );
        }

        if (!readOnlyState.transition.isUnavailable) {
          failures.add(
            'Step 3 failed: Transition stayed available after canWrite changed to false. '
            'Observed read-only state: ${readOnlyState.describe()}.',
          );
        }
        if (!readOnlyState.edit.isUnavailable) {
          failures.add(
            'Step 3 failed: Edit stayed available after canWrite changed to false. '
            'Observed read-only state: ${readOnlyState.describe()}.',
          );
        }
        if (!readOnlyState.comment.isUnavailable) {
          failures.add(
            'Step 3 failed: Comments stayed available after canWrite changed to false. '
            'Observed read-only state: ${readOnlyState.describe()}.',
          );
        }
        if (!readOnlyState.hasReadOnlyExplanation) {
          failures.add(
            'Step 3 failed: the issue detail surface did not render the scoped read-only explanation after the session became read-only. '
            'Observed read-only state: ${readOnlyState.describe()}.',
          );
        }

        if (failures.isNotEmpty) {
          fail(
            'Expected issue detail write affordances to react immediately to a live capability downgrade without reopening the issue. '
            '${failures.join(' ')} Writable baseline: ${writableState.describe()}. '
            'Observed after capability sync: ${readOnlyState.describe()}.',
          );
        }
      } finally {
        screen?.dispose();
        semantics.dispose();
      }
    },
  );
}

Future<_IssueDetailState> _openTargetIssue({
  required ReactiveIssueDetailScreenHandle screen,
  required String targetIssueKey,
  required String targetSummary,
}) async {
  await screen.openSearch();
  await screen.selectIssue(targetIssueKey, targetSummary);

  expect(
    screen.showsIssueDetail(targetIssueKey),
    isTrue,
    reason:
        'Expected opening the TRACK-12 search result to render the TRACK-12 issue-detail surface.',
  );
  expect(
    screen.showsIssueKey(targetIssueKey),
    isTrue,
    reason: 'Expected the TRACK-12 issue key to be visible in issue detail.',
  );
  expect(
    screen.showsSummary(targetIssueKey, targetSummary),
    isTrue,
    reason: 'Expected the TRACK-12 summary to be visible in issue detail.',
  );

  return _IssueDetailState(
    transition: screen.transitionAction(targetIssueKey),
    edit: screen.editAction(targetIssueKey),
    comment: screen.commentAction(targetIssueKey),
    hasReadOnlyExplanation: screen.hasReadOnlyExplanation(targetIssueKey),
  );
}

class _IssueDetailState {
  const _IssueDetailState({
    required this.transition,
    required this.edit,
    required this.comment,
    required this.hasReadOnlyExplanation,
  });

  final ActionAvailability transition;
  final ActionAvailability edit;
  final ActionAvailability comment;
  final bool hasReadOnlyExplanation;

  String describe() => [
    transition.describe(),
    edit.describe(),
    comment.describe(),
    'readOnlyExplanationVisible=$hasReadOnlyExplanation',
  ].join(', ');
}
