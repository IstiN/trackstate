import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/dirty_local_issue_flow_robot.dart';
import '../../components/services/dirty_local_issue_save_service.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import '../../frameworks/providers/trackstate_provider_dirty_local_issue_write_client.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'TS-41 blocks a dirty main.md description save with actionable recovery guidance',
    () async {
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      final service = DirtyLocalIssueSaveService(
        provider: TrackStateProviderDirtyLocalIssueWriteClient(
          provider: fixture.provider,
        ),
        issueKey: LocalTrackStateFixture.issueKey,
        issuePath: LocalTrackStateFixture.issuePath,
        originalDescription: LocalTrackStateFixture.originalDescription,
      );

      await fixture.makeDirtyMainFileChange();

      await expectLater(
        () => service.attemptDescriptionSave(
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
    'TS-41 surfaces actionable dirty-file guidance in the real app mutation flow',
    (tester) async {
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });
      final robot = DirtyLocalIssueFlowRobot(tester);

      await fixture.makeDirtyMainFileChange();
      await robot.pumpApp(repository: fixture.repository);
      await robot.openBoard();

      expect(
        find.descendant(
          of: robot.inProgressColumn,
          matching: robot.issueCard(
            LocalTrackStateFixture.issueKey,
            'Local issue',
          ),
        ),
        findsOneWidget,
      );

      await robot.moveIssueToDone(
        LocalTrackStateFixture.issueKey,
        'Local issue',
      );

      final bannerText = robot.currentBannerText();
      expect(bannerText, isNotNull);
      expect(bannerText, contains('commit'));
      expect(bannerText, contains('stash'));
      expect(bannerText, contains('clean'));
      expect(
        find.descendant(
          of: robot.inProgressColumn,
          matching: robot.issueCard(
            LocalTrackStateFixture.issueKey,
            'Local issue',
          ),
        ),
        findsOneWidget,
      );
    },
  );
}
