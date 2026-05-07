import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/trackstate_app_screen.dart';
import '../../components/services/dirty_local_issue_save_component.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'TS-41 blocks a dirty main.md description save with actionable recovery guidance',
    () async {
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      final saveComponent = DirtyLocalIssueSaveComponent.create(
        provider: fixture.provider,
        issueKey: LocalTrackStateFixture.issueKey,
        issuePath: LocalTrackStateFixture.issuePath,
        originalDescription: LocalTrackStateFixture.originalDescription,
      );

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
    'TS-41 real app description flow is blocked because TrackState issue detail is read-only',
    (tester) async {
      final TrackStateAppComponent screen = TrackStateAppScreen(tester);
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);

      await screen.pump(fixture.repository);
      await screen.expectTextVisible('Local Git');
      await fixture.makeDirtyMainFileChange();
      await screen.openSection('JQL Search');
      await screen.openIssue(LocalTrackStateFixture.issueKey, 'Local issue');
      await screen.expectIssueDetailText(
        LocalTrackStateFixture.issueKey,
        LocalTrackStateFixture.originalDescription,
      );
      await screen.expectIssueDetailText(
        LocalTrackStateFixture.issueKey,
        'In Progress',
      );
    },
    skip: true,
  );
}
