import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/attachments/ts60_attachment_upload_fixture.dart';

void main() {
  test(
    'TS-60 uploads a standard non-LFS attachment through the GitHub contents API',
    () async {
      final fixture = await Ts60AttachmentUploadFixture.create();
      final run = await fixture.uploadSampleAttachment();
      final expectedGitAttributesRequest =
          'GET /repos/${fixture.config.repository}/contents/.gitattributes';
      final expectedUploadRequest =
          'PUT /repos/${fixture.config.repository}/contents/${fixture.config.path}';

      expect(
        run.queriedGitAttributes,
        isTrue,
        reason:
            'The provider should inspect .gitattributes before deciding whether the upload must be blocked by the LFS guard.',
      );
      expect(
        run.observation.isLfsTracked,
        isFalse,
        reason:
            'The standard screenshot fixture must stay outside the repository LFS rules so the provider treats it as a normal attachment.',
      );
      expect(
        run.observation.signalsUnsupported,
        isFalse,
        reason:
            'A non-LFS file must not surface the unsupported/not-yet-implemented message reserved for LFS uploads.',
      );
      expect(
        run.observation.error,
        isNull,
        reason:
            'Uploading a standard attachment should complete successfully without surfacing a provider error.',
      );
      expect(
        run.observation.result,
        isNotNull,
        reason:
            'The provider should return a successful upload result for a standard attachment.',
      );
      expect(
        run.observation.result?.path,
        fixture.config.path,
        reason:
            'The successful result should point to the same attachment path the user uploaded.',
      );
      expect(
        run.observation.result?.branch,
        fixture.config.branch,
        reason:
            'The successful result should keep the upload on the requested branch.',
      );
      expect(
        run.observation.result?.revision,
        'uploaded-sha',
        reason:
            'The observable upload result should expose the content SHA returned by the GitHub Contents API.',
      );
      expect(
        run.observation.userVisibleMessage,
        'Upload succeeded for ${fixture.config.path} on ${fixture.config.branch} (revision: uploaded-sha).',
        reason:
            'The user-facing outcome should clearly report a successful upload for the standard attachment.',
      );
      expect(
        run.uploadRequestDescriptions,
        [expectedUploadRequest],
        reason:
            'The provider should upload the file through the standard GitHub Contents API endpoint exactly once.',
      );
      expect(
        run.gitAttributesRequestDescriptions,
        [expectedGitAttributesRequest, expectedGitAttributesRequest],
        reason:
            'The probe preflight and writeAttachment() should each read .gitattributes so the upload flow re-checks the LFS guard before uploading.',
      );
      expect(
        run.requestDescriptionsImmediatelyBeforeUpload,
        [expectedGitAttributesRequest, expectedUploadRequest],
        reason:
            'writeAttachment() should re-read .gitattributes immediately before the single PUT upload request.',
      );
    },
  );
}
