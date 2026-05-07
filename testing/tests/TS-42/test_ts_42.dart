import 'package:flutter_test/flutter_test.dart';

import '../../components/screens/read_only_issue_detail_screen.dart';
import 'issue_detail_test_context.dart';

void main() {
  testWidgets(
    'TS-42 shows read-only issue detail actions as unavailable before save',
    (tester) async {
      final semantics = tester.ensureSemantics();
      ReadOnlyIssueDetailScreen? screen;

      try {
        screen = await launchReadOnlyIssueDetailScreen(tester);
        final issueDetailPage = screen.page;
        const targetIssueKey = 'TRACK-12';
        const targetSummary = 'Implement Git sync service';
        const previousIssueKey = 'TRACK-11';
        await issueDetailPage.openSearch();
        expect(
          issueDetailPage.showsAcceptanceCriterion(
            previousIssueKey,
            'Dashboard cards stay interactive during refresh.',
          ),
          isTrue,
          reason:
              'Expected JQL Search to open with a different issue selected so '
              'TS-42 must navigate into TRACK-12 through the search results.',
        );
        expect(
          issueDetailPage.showsAcceptanceCriterion(
            targetIssueKey,
            'Push issue updates as commits.',
          ),
          isFalse,
          reason:
              'Expected TRACK-12-specific detail content to be absent before '
              'opening TRACK-12 from the search results.',
        );
        await issueDetailPage.selectIssue(targetIssueKey, targetSummary);

        expect(
          issueDetailPage.showsIssueDetail(targetIssueKey),
          isTrue,
          reason:
              'Expected opening the TRACK-12 search result to render the '
              'TRACK-12 issue-detail surface.',
        );
        expect(
          issueDetailPage.showsAcceptanceCriterion(
            targetIssueKey,
            'Push issue updates as commits.',
          ),
          isTrue,
          reason:
              'Expected tapping the TRACK-12 search result to replace the '
              'detail panel with TRACK-12-specific content.',
        );
        expect(
          issueDetailPage.showsAcceptanceCriterion(
            targetIssueKey,
            'Dashboard cards stay interactive during refresh.',
          ),
          isFalse,
          reason:
              'Expected TRACK-11-specific detail content to disappear after '
              'opening TRACK-12 from the search results.',
        );
        expect(
          issueDetailPage.showsIssueKey(targetIssueKey),
          isTrue,
          reason:
              'Expected the TRACK-12 issue key to be visible in issue detail.',
        );
        expect(
          issueDetailPage.showsSummary(targetIssueKey, targetSummary),
          isTrue,
          reason:
              'Expected the TRACK-12 summary to be visible in issue detail.',
        );

        final transition = issueDetailPage.transitionAction(targetIssueKey);
        final edit = issueDetailPage.editAction(targetIssueKey);
        final comment = issueDetailPage.commentAction(targetIssueKey);
        final failures = <String>[];

        if (!transition.isUnavailable) {
          failures.add(
            'Transition should be disabled or hidden when canWrite=false. '
            'Observed ${transition.describe()}.',
          );
        }
        if (!edit.isUnavailable) {
          failures.add(
            'Edit should be disabled or hidden when canWrite=false. '
            'Observed ${edit.describe()}.',
          );
        }
        if (!comment.isUnavailable) {
          failures.add(
            'Comments should be disabled or hidden when canWrite=false. '
            'Observed ${comment.describe()}.',
          );
        }
        if (!issueDetailPage.hasReadOnlyExplanation(targetIssueKey)) {
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
            '${issueDetailPage.describeObservedState(targetIssueKey)}.',
          );
        }
      } finally {
        screen?.dispose();
        semantics.dispose();
      }
    },
  );
}
