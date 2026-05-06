import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/pages/issue_detail_page.dart';
import '../../core/fakes/read_only_trackstate_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-42 shows read-only issue detail actions as unavailable before save',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          const TrackStateApp(repository: ReadOnlyTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        final issueDetailPage = IssueDetailPage(tester);
        await issueDetailPage.open();

        expect(issueDetailPage.issueSummary, findsWidgets);

        final transitionVisible = issueDetailPage.transitionButton
            .evaluate()
            .isNotEmpty;
        final transitionDisabled = issueDetailPage.transitionActionUnavailable;
        final editVisible = issueDetailPage.editActionVisible;
        final commentVisible = issueDetailPage.commentActionVisible;
        final permissionMessageVisible =
            issueDetailPage.permissionMessageVisible;

        if (!transitionDisabled || !permissionMessageVisible) {
          fail(
            'Expected read-only issue detail UI to disable or hide write '
            'actions and show an explanatory permission message. Observed '
            'transitionVisible=$transitionVisible, '
            'transitionDisabled=$transitionDisabled, '
            'editVisible=$editVisible, '
            'commentVisible=$commentVisible, '
            'permissionMessageVisible=$permissionMessageVisible.',
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
