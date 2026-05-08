import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/read_only_issue_detail_screen.dart';
import '../../core/models/action_availability.dart';
import '../../fixtures/read_only_issue_detail_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-42 shows read-only issue detail actions as unavailable before save',
    (tester) async {
      final semantics = tester.ensureSemantics();
      ReadOnlyIssueDetailScreenHandle? writableScreen;
      ReadOnlyIssueDetailScreenHandle? readOnlyScreen;

      try {
        const targetIssueKey = 'TRACK-12';
        const targetSummary = 'Implement Git sync service';
        const previousIssueKey = 'TRACK-11';
        const previousSummary = 'Stabilize dashboard polling';
        writableScreen = await launchWritableIssueDetailFixture(tester);
        final writableState = await _openTargetIssue(
          screen: writableScreen,
          previousIssueKey: previousIssueKey,
          previousSummary: previousSummary,
          targetIssueKey: targetIssueKey,
          targetSummary: targetSummary,
          requireNavigationProof: false,
        );
        writableScreen.dispose();
        writableScreen = null;

        readOnlyScreen = await launchReadOnlyIssueDetailFixture(tester);
        final readOnlyState = await _openTargetIssue(
          screen: readOnlyScreen,
          previousIssueKey: previousIssueKey,
          previousSummary: previousSummary,
          targetIssueKey: targetIssueKey,
          targetSummary: targetSummary,
          requireNavigationProof: true,
        );

        final failures = <String>[];

        if (!writableState.transition.enabled) {
          failures.add(
            'TS-42 requires Transition to be a real write action before the '
            'read-only check, but the writable baseline did not expose it as '
            'enabled. Observed ${writableState.transition.describe()}.',
          );
        }
        if (!readOnlyState.transition.isUnavailable) {
          failures.add(
            'Transition should be disabled or hidden when canWrite=false. '
            'Observed ${readOnlyState.transition.describe()}.',
          );
        }
        if (!writableState.edit.enabled) {
          failures.add(
            'TS-42 cannot verify Edit is capability-guarded because the '
            'writable baseline does not expose Edit as an enabled action. '
            'Observed ${writableState.edit.describe()}.',
          );
        } else if (!readOnlyState.edit.isUnavailable) {
          failures.add(
            'Edit should be disabled or hidden when canWrite=false. '
            'Observed ${readOnlyState.edit.describe()}.',
          );
        }
        if (writableState.comment.visible && !writableState.comment.enabled) {
          failures.add(
            'Comments is rendered for writable users but is not enabled. '
            'Observed ${writableState.comment.describe()}.',
          );
        }
        if (!readOnlyState.comment.isUnavailable) {
          failures.add(
            'Comments should be disabled or hidden when canWrite=false. '
            'Observed ${readOnlyState.comment.describe()}.',
          );
        }
        if (readOnlyState.hasReadOnlyExplanation) {
          // no-op
        } else {
          failures.add(
            'A visible read-only explanation should be rendered as text or '
            'tooltip, for example messaging that mentions permission, '
            'read-only mode, or write access.',
          );
        }

        if (failures.isNotEmpty) {
          fail(
            'Expected read-only issue detail UI to guard all write actions '
            'up front for canWrite=false. ${failures.join(' ')} Observed '
            'writable baseline: ${writableState.describe()}. Observed '
            'read-only state: ${readOnlyState.describe()}.',
          );
        }
      } finally {
        writableScreen?.dispose();
        readOnlyScreen?.dispose();
        semantics.dispose();
      }
    },
  );
}

Future<_IssueDetailState> _openTargetIssue({
  required ReadOnlyIssueDetailScreenHandle screen,
  required String previousIssueKey,
  required String previousSummary,
  required String targetIssueKey,
  required String targetSummary,
  required bool requireNavigationProof,
}) async {
  await screen.openSearch();
  if (requireNavigationProof) {
    await screen.selectIssue(previousIssueKey, previousSummary);
    expect(
      screen.showsIssueDetail(previousIssueKey),
      isTrue,
      reason:
          'Expected the search result for TRACK-11 to open its issue-detail '
          'surface before navigating to TRACK-12.',
    );
    expect(
      screen.showsAcceptanceCriterion(
        previousIssueKey,
        'Dashboard cards stay interactive during refresh.',
      ),
      isTrue,
      reason:
          'Expected TRACK-11 to render its own issue detail after selecting '
          'it from the search results.',
    );
    expect(
      screen.showsAcceptanceCriterion(
        targetIssueKey,
        'Push issue updates as commits.',
      ),
      isFalse,
      reason:
          'Expected TRACK-12-specific detail content to stay absent until '
          'the test opens TRACK-12 from the search results.',
    );
  }
  await screen.selectIssue(targetIssueKey, targetSummary);

  expect(
    screen.showsIssueDetail(targetIssueKey),
    isTrue,
    reason:
        'Expected opening the TRACK-12 search result to render the '
        'TRACK-12 issue-detail surface.',
  );
  expect(
    screen.showsAcceptanceCriterion(
      targetIssueKey,
      'Push issue updates as commits.',
    ),
    isTrue,
    reason:
        'Expected tapping the TRACK-12 search result to replace the '
        'detail panel with TRACK-12-specific content.',
  );
  if (requireNavigationProof) {
    expect(
      screen.showsAcceptanceCriterion(
        targetIssueKey,
        'Dashboard cards stay interactive during refresh.',
      ),
      isFalse,
      reason:
          'Expected TRACK-11-specific detail content to disappear after '
          'opening TRACK-12 from the search results.',
    );
  }
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
