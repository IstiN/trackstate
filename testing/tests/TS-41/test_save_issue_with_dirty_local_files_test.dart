import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

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
      final service = DirtyLocalIssueSaveService(
        provider: fixture.provider,
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
}
