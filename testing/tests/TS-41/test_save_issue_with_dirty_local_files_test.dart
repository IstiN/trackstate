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
    'TS-41 surfaces actionable dirty-file guidance in the live local Git banner after a user mutation',
    (tester) async {
      final fixture = (await tester.runAsync(LocalTrackStateFixture.create))!;
      final TrackStateAppComponent app = TrackStateAppScreen(tester);
      addTearDown(fixture.dispose);
      addTearDown(app.resetView);

      await tester.runAsync(fixture.makeDirtyMainFileChange);

      await app.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
      await app.openSection('Board');
      await app.expectTextVisible('Local issue');

      await app.dragIssueToStatusColumn(
        key: LocalTrackStateFixture.issueKey,
        summary: 'Local issue',
        sourceStatusLabel: 'In Progress',
        statusLabel: 'Done',
      );

      await app.expectMessageBannerContains(LocalTrackStateFixture.issuePath);
      await app.expectMessageBannerContains('commit');
      await app.expectMessageBannerContains('stash');
      await app.expectMessageBannerContains('clean');
      await app.expectTextVisible('Local issue');
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
