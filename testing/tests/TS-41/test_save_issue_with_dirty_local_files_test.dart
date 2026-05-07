import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_git_test_repository.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import 'support/ts41_dirty_local_issue_component_factory.dart';
import 'support/ts41_live_app_repository.dart';

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
    'TS-41 shows actionable visible guidance when a real app mutation hits a dirty main.md',
    (tester) async {
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final semantics = tester.ensureSemantics();
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-41 fixture creation did not complete.');
        }

        await tester.runAsync(() => fixture!.makeDirtyMainFileChange());

        await screen.pump(
          createTs41LiveAppRepository(
            tester: tester,
            repository: LocalTrackStateRepository(
              repositoryPath: fixture.repositoryPath,
              processRunner: const SyncGitProcessRunner(),
            ),
          ),
        );
        await screen.openSection('JQL Search');
        await screen.openIssue(
          LocalTrackStateFixture.issueKey,
          LocalTrackStateFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          LocalTrackStateFixture.issueKey,
          LocalTrackStateFixture.originalDescription,
        );

        await screen.openSection('Board');
        await screen.dragIssueToStatusColumn(
          key: LocalTrackStateFixture.issueKey,
          summary: LocalTrackStateFixture.issueSummary,
          sourceStatusLabel: 'In Progress',
          statusLabel: 'Done',
        );

        await screen.expectTrackerMessageContaining('commit');
        await screen.expectTrackerMessageContaining('stash');
        await screen.expectTrackerMessageContaining('clean');
      } finally {
        if (fixture != null) {
          await fixture.dispose();
        }
        screen.resetView();
        semantics.dispose();
      }
    },
  );
}
