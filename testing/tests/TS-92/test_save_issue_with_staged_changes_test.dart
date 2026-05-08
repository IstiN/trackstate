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
    'TS-92 blocks a staged main.md description save with actionable recovery guidance',
    () async {
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      final saveComponent = createDirtyLocalIssueSaveComponentFixture(fixture);

      await fixture.makeStagedMainFileChange();

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

      expect(
        await fixture.readMainFile(),
        isNot(contains(LocalTrackStateFixture.updatedDescription)),
      );
    },
  );

  testWidgets(
    'TS-92 blocks the staged-change save in the real issue-detail flow',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-92 fixture creation did not complete.');
        }

        await tester.runAsync(fixture.makeStagedMainFileChange);
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
        await screen.expectMessageBannerContains('commit');
        await screen.expectMessageBannerContains('stash');
        await screen.expectMessageBannerContains('clean');
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
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
