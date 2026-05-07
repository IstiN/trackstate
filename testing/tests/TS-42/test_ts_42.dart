import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/pages/issue_detail_page.dart';
import '../../core/fakes/read_only_trackstate_repository.dart';
import '../../frameworks/flutter/widget_test_driver.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'read-only-token',
    });
  });

  testWidgets(
    'TS-42 shows read-only issue detail actions as unavailable before save',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        final driver = WidgetTestDriver(tester);
        await driver.pumpApp(
          TrackStateApp(repository: ReadOnlyTrackStateRepository()),
        );

        final issueDetailPage = IssueDetailPage(driver);
        await issueDetailPage.openSearch();
        expect(
          issueDetailPage.showsAcceptanceCriterion(
            'Dashboard cards stay interactive during refresh.',
          ),
          isTrue,
          reason:
              'Expected JQL Search to open with a different issue selected so '
              'TS-42 must navigate into TRACK-12 through the search results.',
        );
        expect(
          issueDetailPage.showsAcceptanceCriterion(
            'Push issue updates as commits.',
          ),
          isFalse,
          reason:
              'Expected TRACK-12-specific detail content to be absent before '
              'opening TRACK-12 from the search results.',
        );
        await issueDetailPage.selectIssue(
          'TRACK-12',
          'Implement Git sync service',
        );

        expect(
          issueDetailPage.showsAcceptanceCriterion(
            'Push issue updates as commits.',
          ),
          isTrue,
          reason:
              'Expected tapping the TRACK-12 search result to replace the '
              'detail panel with TRACK-12-specific content.',
        );
        expect(
          issueDetailPage.showsAcceptanceCriterion(
            'Dashboard cards stay interactive during refresh.',
          ),
          isFalse,
          reason:
              'Expected TRACK-11-specific detail content to disappear after '
              'opening TRACK-12 from the search results.',
        );
        expect(
          issueDetailPage.showsIssueKey('TRACK-12'),
          isTrue,
          reason:
              'Expected the TRACK-12 issue key to be visible in issue detail.',
        );
        expect(
          issueDetailPage.showsSummary('Implement Git sync service'),
          isTrue,
          reason:
              'Expected the TRACK-12 summary to be visible in issue detail.',
        );

        final transition = issueDetailPage.transitionAction;
        final edit = issueDetailPage.editAction;
        final comment = issueDetailPage.commentAction;
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
        if (!issueDetailPage.hasReadOnlyExplanation) {
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
            '${issueDetailPage.describeObservedState()}.',
          );
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
