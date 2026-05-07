import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

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
}
