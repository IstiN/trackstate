import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/attachments/ts61_missing_gitattributes_fixture.dart';

void main() {
  test(
    'TS-61 uploads through the standard contents API when .gitattributes is missing',
    () async {
      final fixture = await Ts61MissingGitattributesFixture.create();
      final scenario = await fixture.uploadSampleAttachment();
      final observation = scenario.uploadObservation;
      final gitattributesLookup = scenario.gitattributesLookup;
      final contentsUpload = scenario.contentsUpload;
      final uploadPayload = contentsUpload?.jsonBody as Map<String, Object?>?;

      expect(
        observation.isLfsTracked,
        isFalse,
        reason:
            'A missing .gitattributes file should be treated as not LFS-tracked so the upload can continue.',
      );
      expect(
        observation.error,
        isNull,
        reason:
            'The upload should not surface an unsupported or provider error when tracking configuration is absent.',
      );
      expect(
        observation.result,
        isNotNull,
        reason:
            'The user-facing outcome should be a successful attachment upload result.',
      );
      expect(
        observation.result?.revision,
        'uploaded-notes-sha',
        reason:
            'A standard contents upload should return the revision reported by the GitHub Contents API.',
      );
      expect(
        gitattributesLookup,
        isNotNull,
        reason:
            'The provider should still check for .gitattributes before deciding whether the file is LFS-tracked.',
      );
      expect(
        gitattributesLookup?.query['ref'],
        fixture.config.branch,
        reason:
            'The .gitattributes lookup should target the configured branch.',
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
        fixture.config.branch,
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
