import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-112 keeps the dirty-save error banner visible until the user dismisses it',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-112 fixture creation did not complete.');
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

        await screen.waitWithoutInteraction(const Duration(seconds: 10));

        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isTrue,
          reason:
              'Step 3 failed: after waiting 10 seconds with no interaction, the '
              'visible dirty-save banner was no longer on screen. Expected the '
              '"Save failed:" notification to remain persistent until the user '
              'manually dismissed it.',
        );

        expect(
          await screen.dismissMessageBannerContaining('Save failed:'),
          isTrue,
          reason:
              'Step 4 failed: clicking the visible dismiss or close control did '
              'not clear the dirty-save banner from the screen.',
        );

        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isFalse,
          reason:
              'Step 4 failed: the dirty-save banner remained visible after the '
              'manual dismiss action completed.',
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
    timeout: const Timeout(Duration(seconds: 35)),
  );
}
