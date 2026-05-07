import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/setup/ts73_setup_repository_fixture.dart';

void main() {
  test(
    'TS-73 verifies attachment path and Git LFS guidance align with the setup repository structure',
    () async {
      final fixture = Ts73SetupRepositoryFixture.create();
      final observation = await fixture.inspect();

      expect(
        fixture.setupRoot.existsSync(),
        isTrue,
        reason:
            'The setup repository should be present so users can follow the documented attachment workflow.',
      );
      expect(
        fixture.demoRoot.existsSync(),
        isTrue,
        reason:
            'The demo tree should exist because the setup README points users to the DEMO/ repository structure.',
      );
      expect(
        observation.hasAttachmentDirectoryInDemoTree,
        isTrue,
        reason:
            'Expected at least one issue-level attachments/ directory inside trackstate-setup/DEMO so the documented storage location exists in the repository structure.',
      );
      expect(
        observation.hasDocumentedDemoIssueAttachmentDirectory,
        isTrue,
        reason:
            'Expected DEMO/DEMO-1/DEMO-5/attachments to exist because the demo story that documents attachment handoff should include the folder users are told to use.',
      );
      expect(
        observation.attachmentDirectories,
        containsAll([
          'DEMO/DEMO-1/DEMO-2/attachments',
          'DEMO/DEMO-1/DEMO-5/attachments',
        ]),
        reason:
            'The demo tree should expose the concrete attachments/ directories a setup user can inspect while learning the repository layout.',
      );
      expect(
        observation.lfsTrackedPatterns,
        contains('*.png'),
        reason:
            'Expected .gitattributes to track PNG files through Git LFS because screenshots are a common binary attachment format.',
      );
      expect(
        observation.lfsTrackedPatterns,
        contains('*.zip'),
        reason:
            'Expected .gitattributes to track ZIP files through Git LFS because archives are a common large attachment format.',
      );
      expect(
        observation.readmeDocumentsAttachmentDirectory,
        isTrue,
        reason:
            'The setup README should explicitly tell users to keep attachments under each issue\'s attachments/ directory and show that directory in the documented demo tree.',
      );
      expect(
        observation.readmeDocumentsGitLfsForLargeFiles,
        isTrue,
        reason:
            'The setup README should explicitly explain that large attachments belong in Git LFS and that .gitattributes already tracks common binary formats.',
      );
      expect(
        observation.demoIssueAttachmentReadmeDocumentsUsage,
        isTrue,
        reason:
            'The issue-level attachments/ README should read like end-user guidance by telling people to keep small files there and move large or binary files into Git LFS.',
      );
    },
  );
}
