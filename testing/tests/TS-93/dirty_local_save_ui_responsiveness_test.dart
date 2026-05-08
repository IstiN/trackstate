import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/trackstate_app_screen.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import 'support/ts93_local_issue_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-93 surfaces the dirty-write error promptly and keeps the UI responsive',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen =
          defaultTestingDependencies.createTrackStateAppScreen(tester)
              as TrackStateAppScreen;
      Ts93LocalIssueFixture? fixture;
      var dismissed = false;

      try {
        fixture = await tester.runAsync(Ts93LocalIssueFixture.create);
        if (fixture == null) {
          throw StateError('TS-93 fixture creation did not complete.');
        }

        await tester.runAsync(fixture.makeDirtyMainFileChange);
        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Search');
        await screen.openIssue(
          LocalTrackStateFixture.issueKey,
          LocalTrackStateFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          LocalTrackStateFixture.issueKey,
          LocalTrackStateFixture.originalDescription,
        );
        await screen.tapIssueDetailAction(
          LocalTrackStateFixture.issueKey,
          label: 'Edit',
        );
        await screen.expectIssueDescriptionEditorVisible(
          LocalTrackStateFixture.issueKey,
          label: 'Description',
        );
        await screen.enterIssueDescription(
          LocalTrackStateFixture.issueKey,
          label: 'Description',
          text: LocalTrackStateFixture.updatedDescription,
        );
        await screen.tapIssueDetailAction(
          LocalTrackStateFixture.issueKey,
          label: 'Save',
        );

        await screen.expectMessageBannerContains('Save failed:');
        await screen.expectMessageBannerContains('commit');
        await screen.expectMessageBannerContains('stash');
        await screen.expectMessageBannerContains('clean');

        dismissed = await screen.dismissMessageBanner();

        await screen.searchIssues(Ts93LocalIssueFixture.secondIssueKey);
        await screen.expectIssueSearchResultVisible(
          Ts93LocalIssueFixture.secondIssueKey,
          Ts93LocalIssueFixture.secondIssueSummary,
        );
        await screen.openIssue(
          Ts93LocalIssueFixture.secondIssueKey,
          Ts93LocalIssueFixture.secondIssueSummary,
        );
        await screen.expectIssueDetailText(
          Ts93LocalIssueFixture.secondIssueKey,
          Ts93LocalIssueFixture.secondIssueDescription,
        );

        expect(
          dismissed,
          isTrue,
          reason:
              'Expected the dirty-write error to expose a visible dismiss action before the user continues interacting, but no dismiss or close control was rendered.',
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}
