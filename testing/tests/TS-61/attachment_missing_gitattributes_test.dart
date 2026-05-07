import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/attachments/ts61_missing_gitattributes_fixture.dart';

void main() {
  test(
    'TS-61 uploads through the standard contents API when .gitattributes is missing',
    () async {
      final fixture = await Ts61MissingGitattributesFixture.create();
      final scenario = await fixture.uploadSampleAttachment();
      final gitattributesLookup = scenario.gitattributesLookup;
      final contentsUpload = scenario.contentsUpload;
      final uploadPayload = contentsUpload?.jsonBody as Map<String, Object?>?;

      expect(
        scenario.error,
        isNull,
        reason:
            'The upload should not surface an unsupported or provider error when tracking configuration is absent.',
      );
      expect(
        scenario.uploadResult,
        isNotNull,
        reason:
            'The user-facing outcome should be a successful attachment upload result.',
      );
      expect(
        scenario.uploadResult?.revision,
        'uploaded-notes-sha',
        reason:
            'A standard contents upload should return the revision reported by the GitHub Contents API.',
      );
      expect(
        scenario.gitattributesLookups,
        hasLength(1),
        reason:
            'writeAttachment() itself should perform exactly one .gitattributes lookup while deciding whether the upload is LFS-tracked.',
      );
      expect(
        scenario.contentsUploads,
        hasLength(1),
        reason:
            'After handling the missing .gitattributes response, writeAttachment() should perform exactly one standard Contents API upload.',
      );
      expect(
        scenario.requestSequence,
        [
          'GET /repos/${fixture.config.repository}/contents/.gitattributes',
          'PUT /repos/${fixture.config.repository}/contents/${fixture.config.path}',
        ],
        reason:
            'The upload-time guard should check .gitattributes and then continue directly into the standard Contents API write path.',
      );
      expect(
        gitattributesLookup?.query,
        {'ref': fixture.config.branch},
        reason:
            'The upload-time .gitattributes lookup should target the configured branch.',
      );
      expect(
        scenario.attemptedStandardUpload,
        isTrue,
        reason:
            'After the missing .gitattributes lookup, the provider should continue with the normal Contents API upload.',
      );
      expect(
        contentsUpload?.path,
        '/repos/${fixture.config.repository}/contents/${fixture.config.path}',
        reason:
            'The observable upload call should target the GitHub Contents API for the requested attachment path.',
      );
      expect(
        uploadPayload?['branch'],
        scenario.uploadResult?.branch,
        reason:
            'The standard upload request should preserve the branch selected by the user.',
      );
      expect(
        uploadPayload?['message'],
        fixture.config.message,
        reason:
            'The standard upload request should preserve the commit message sent with the attachment.',
      );
    },
  );
}
