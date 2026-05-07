import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
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
    'TS-41 shows actionable recovery guidance in the tracker banner after a dirty local mutation',
    (tester) async {
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      await fixture.makeDirtyMainFileChange();

      await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
      await screen.expectTextVisible('Local Git');
      await screen.openSection('Board');
      await screen.dragIssueToStatusColumn(
        key: LocalTrackStateFixture.issueKey,
        summary: LocalTrackStateFixture.issueSummary,
        sourceStatusLabel: 'In Progress',
        statusLabel: 'Done',
      );
      await screen.expectTrackerMessageContaining('Move failed:');
      await screen.expectTrackerMessageContaining('commit');
      await screen.expectTrackerMessageContaining('stash');
      await screen.expectTrackerMessageContaining('clean');
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
