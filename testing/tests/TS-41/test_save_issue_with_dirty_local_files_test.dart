import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/trackstate_app_screen.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_git_test_repository.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import 'support/ts41_dirty_local_issue_component_factory.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'TS-41 blocks a dirty main.md description save with actionable recovery guidance',
    () async {
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      final saveComponent = createTs41DirtyLocalIssueSaveComponent(fixture);

      await fixture.makeDirtyMainFileChange();

      await expectLater(
        () => saveComponent.attemptDescriptionSave(
          LocalTrackStateFixture.updatedDescription,
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            allOf(contains('commit'), contains('stash'), contains('clean')),
          ),
        ),
      );
    },
  );

  testWidgets(
    'TS-41 lets a user edit the same dirty issue description and click Save',
    (tester) async {
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      final TrackStateAppComponent screen = TrackStateAppScreen(tester);

      await fixture.makeDirtyMainFileChange();

      await screen.pump(
        LocalTrackStateRepository(
          repositoryPath: fixture.repositoryPath,
          processRunner: const SyncGitProcessRunner(),
        ),
      );
      await screen.expectTextVisible('Local Git');
      await screen.openSection('JQL Search');
      await screen.openIssue(
        LocalTrackStateFixture.issueKey,
        LocalTrackStateFixture.issueSummary,
      );
      await screen.expectIssueDetailText(
        LocalTrackStateFixture.issueKey,
        LocalTrackStateFixture.originalDescription,
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
        'Save',
      );
      await screen.expectMessageBannerContains('commit');
      await screen.expectMessageBannerContains('stash');
      await screen.expectMessageBannerContains('clean');
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
