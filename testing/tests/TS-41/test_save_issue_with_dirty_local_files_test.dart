import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/trackstate_app_screen.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import 'package:shared_preferences/shared_preferences.dart';
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
    'TS-41 surfaces actionable dirty-save guidance from the real app description flow',
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
      await screen.enterIssueDetailDescription(
        LocalTrackStateFixture.issueKey,
        LocalTrackStateFixture.updatedDescription,
      );
      await screen.tapIssueDetailAction(
        LocalTrackStateFixture.issueKey,
        'Save',
      );
      await screen.expectTextVisible('commit');
      await screen.expectTextVisible('stash');
      await screen.expectTextVisible('clean');
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
