import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/attachments/ts44_attachment_upload_fixture.dart';

void main() {
  test(
    'TS-44 reports an explicit unsupported outcome for LFS attachment uploads',
    () async {
      final fixture = await Ts44AttachmentUploadFixture.create();
      final observation = await fixture.uploadSampleAttachment();

      expect(
        observation.isLfsTracked,
        isTrue,
        reason:
            'The provider port must identify the attachment path as LFS-tracked before upload capability is evaluated.',
      );
      expect(
        observation.signalsUnsupported,
        isTrue,
        reason:
            'Expected an explicit unsupported or not-yet-implemented outcome for the LFS upload flow, but observed ${observation.describeOutcome()}',
      );
      expect(
        fixture.uploadAttempts,
        0,
        reason:
            'An unsupported LFS upload should stop before the GitHub contents upload endpoint is called.',
      );
    },
  );
}
