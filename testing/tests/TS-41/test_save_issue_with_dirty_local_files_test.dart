import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import '../../components/factories/testing_dependencies.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import '../../fixtures/dirty_local_issue_save_component_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'TS-41 blocks a dirty main.md description save with actionable recovery guidance',
    () async {
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      final saveComponent = createDirtyLocalIssueSaveComponentFixture(fixture);

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
    'TS-41 current TrackState issue detail exposes no live Edit/Save path for main.md',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-41 fixture creation did not complete.');
        }

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
        screen.expectIssueDetailActionAbsent(
          key: LocalTrackStateFixture.issueKey,
          label: 'Edit',
        );
        screen.expectIssueDetailActionAbsent(
          key: LocalTrackStateFixture.issueKey,
          label: 'Save',
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
  );
}
