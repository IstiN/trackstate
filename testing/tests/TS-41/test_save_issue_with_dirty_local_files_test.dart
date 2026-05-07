import 'dart:io';

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

  test(
    'TS-41 documents that the current issue detail implementation is read-only',
    () async {
      final source = await File(
        'lib/ui/features/tracker/views/trackstate_app.dart',
      ).readAsString();

      expect(
        source,
        contains('Text(issue.description)'),
        reason:
            'The current issue detail still renders the description as text.',
      );
      expect(
        source,
        contains('label: l10n.transition'),
        reason: 'The current issue detail exposes Transition as its action.',
      );
      expect(
        source,
        isNot(contains('label: l10n.save')),
        reason: 'The current issue detail does not expose a Save action yet.',
      );
    },
  );
}
