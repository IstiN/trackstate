import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/trackstate_app_screen.dart';
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
    'TS-41 shows the current issue detail remains read-only in the real app UI',
    (tester) async {
      final fixture = (await tester.runAsync(LocalTrackStateFixture.create))!;
      addTearDown(fixture.dispose);
      final screen = TrackStateAppScreen(tester);

      await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
      await screen.expectTextVisible('Local Git');
      await screen.openSection('JQL Search');
      await screen.openIssue('DEMO-1', 'Local issue');
      await screen.expectIssueDetailText('DEMO-1', 'Loaded from local git.');
      await screen.expectIssueDetailActionVisible('DEMO-1', 'Transition');
      await screen.expectIssueDetailDescriptionEditorAbsent('DEMO-1');
      await screen.expectIssueDetailActionAbsent('DEMO-1', 'Save');
    },
  );
}
