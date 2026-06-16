import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/read_only_issue_detail_screen.dart';
import '../../core/models/action_availability.dart';
import '../../fixtures/read_only_issue_detail_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-103 exposes writable issue detail actions and hides read-only guidance when canWrite=true',
    (tester) async {
      final semantics = tester.ensureSemantics();
      ReadOnlyIssueDetailScreenHandle? screen;

      try {
        const targetIssueKey = 'TRACK-12';
        const targetSummary = 'Implement Git sync service';
        const targetAcceptanceCriterion = 'Push issue updates as commits.';

        screen = await launchWritableIssueDetailFixture(tester);
        final observedState = await _openTargetIssue(
          screen: screen,
          targetIssueKey: targetIssueKey,
          targetSummary: targetSummary,
          targetAcceptanceCriterion: targetAcceptanceCriterion,
        );

        final failures = <String>[];

        if (!observedState.edit.visible) {
          failures.add(
            'Step 2 failed: Edit was not visible on the writable issue detail surface. '
            'Observed ${observedState.edit.describe()}.',
          );
        } else if (!observedState.edit.enabled) {
          failures.add(
            'Step 2 failed: Edit was visible but disabled even though canWrite=true. '
            'Observed ${observedState.edit.describe()}.',
          );
        }

        if (!observedState.transition.visible) {
          failures.add(
            'Step 2 failed: Transition was not visible on the writable issue detail surface. '
            'Observed ${observedState.transition.describe()}.',
          );
        } else if (!observedState.transition.enabled) {
          failures.add(
            'Step 2 failed: Transition was visible but disabled even though canWrite=true. '
            'Observed ${observedState.transition.describe()}.',
          );
        }

        if (!observedState.comment.visible) {
          failures.add(
            'Step 2 failed: Comment control was not visible on the writable issue detail surface. '
            'Observed ${observedState.comment.describe()}.',
          );
        } else if (!observedState.comment.enabled) {
          failures.add(
            'Step 2 failed: Comment control was visible but disabled even though canWrite=true. '
            'Observed ${observedState.comment.describe()}.',
          );
        }

        if (observedState.hasReadOnlyExplanation) {
          failures.add(
            'Step 3 failed: read-only guidance was visible even though the session had write permission. '
            'Observed ${observedState.describe()}.',
          );
        }

        if (failures.isNotEmpty) {
          fail(
            'Expected writable issue detail access to expose enabled mutation actions and hide read-only guidance. '
            '${failures.join(' ')} Observed writable state: ${observedState.describe()}.',
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
  required ReadOnlyIssueDetailScreenHandle screen,
  required String targetIssueKey,
  required String targetSummary,
  required String targetAcceptanceCriterion,
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
  expect(
    screen.showsAcceptanceCriterion(targetIssueKey, targetAcceptanceCriterion),
    isTrue,
    reason:
        'Expected the TRACK-12 acceptance criterion to be visible in issue detail for user-facing verification.',
  );

  return _IssueDetailState(
    edit: screen.editAction(targetIssueKey),
    transition: screen.transitionAction(targetIssueKey),
    comment: screen.commentAction(targetIssueKey),
    hasReadOnlyExplanation: screen.hasReadOnlyExplanation(targetIssueKey),
  );
}

class _IssueDetailState {
  const _IssueDetailState({
    required this.edit,
    required this.transition,
    required this.comment,
    required this.hasReadOnlyExplanation,
  });

  final ActionAvailability edit;
  final ActionAvailability transition;
  final ActionAvailability comment;
  final bool hasReadOnlyExplanation;

  String describe() => [
    edit.describe(),
    transition.describe(),
    comment.describe(),
    'readOnlyExplanationVisible=$hasReadOnlyExplanation',
  ].join(', ');
}
