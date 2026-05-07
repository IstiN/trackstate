import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/setup/ts73_setup_repository_fixture.dart';

void main() {
  test(
    'TS-73 verifies attachment path and Git LFS guidance align with the setup repository structure',
    () async {
      final fixture = Ts73SetupRepositoryFixture.create();

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
        fixture.readmeFile.existsSync(),
        isTrue,
        reason:
            'The setup README should exist so the test can verify the documented attachment guidance.',
      );
      expect(
        fixture.gitattributesFile.existsSync(),
        isTrue,
        reason:
            'The setup repository should include .gitattributes so the test can verify the published Git LFS policy.',
      );

      final observation = await fixture.inspect();

      expect(
        observation.hasAttachmentDirectoryInDemoTree,
        isTrue,
        reason:
            'Expected at least one issue-level attachments/ directory inside trackstate-setup/DEMO so the documented storage location exists in the repository structure.',
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
    },
  );
}
