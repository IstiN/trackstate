import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/trackstate_app_screen.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import 'support/ts41_dirty_local_issue_component_factory.dart';

void main() {
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
    'TS-41 attempts the live description save flow for a dirty local DEMO-1 issue',
    (tester) async {
      final fixture = (await tester.runAsync(LocalTrackStateFixture.create))!;
      final TrackStateAppComponent screen = TrackStateAppScreen(tester);
      addTearDown(fixture.dispose);
      addTearDown(screen.resetView);

      await tester.runAsync(fixture.makeDirtyMainFileChange);
      await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
      await screen.expectTextVisible('Local Git');
      await screen.openSection('JQL Search');
      await screen.openIssue('DEMO-1', 'Local issue');
      await screen.expectIssueDetailText('DEMO-1', 'Loaded from local git.');
      await screen.replaceIssueDetailDescription(
        'DEMO-1',
        LocalTrackStateFixture.updatedDescription,
      );
      await screen.tapIssueDetailAction('DEMO-1', 'Save');
      await screen.expectMessageBannerText('commit');
      await screen.expectMessageBannerText('stash');
      await screen.expectMessageBannerText('clean');
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
