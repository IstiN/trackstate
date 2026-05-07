import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/pages/dirty_local_issue_save_page.dart';
import '../../components/services/dirty_local_issue_save_service.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'TS-41 blocks a dirty main.md description save with actionable recovery guidance',
    () async {
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      final service = DirtyLocalIssueSaveService(fixture);

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
    'TS-41 shows an actionable visible error after a user-triggered mutation hits a dirty main.md',
    (tester) async {
      final page = DirtyLocalIssueSavePage(tester);
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      final service = DirtyLocalIssueSaveService(fixture);

      await fixture.makeDirtyMainFileChange();

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await page.open(
        initialDescription: LocalTrackStateFixture.originalDescription,
        onSave: service.attemptDescriptionSave,
      );
      await page.enterDescription(LocalTrackStateFixture.updatedDescription);
      await page.save();

      expect(page.errorBannerContaining('Save failed:'), findsOneWidget);
      expect(page.errorBannerContaining('commit'), findsOneWidget);
      expect(page.errorBannerContaining('stash'), findsOneWidget);
      expect(page.errorBannerContaining('clean'), findsOneWidget);
      expect(
        page.errorBannerContaining(LocalTrackStateFixture.issuePath),
        findsOneWidget,
      );
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}
