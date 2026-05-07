import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/setup/ts73_setup_repository_fixture.dart';

void main() {
  test(
    'TS-73 requires guidance-level Git LFS README instructions for large attachments',
    () {
      const unrelatedObservation = Ts73SetupRepositoryObservation(
        attachmentDirectories: <String>[],
        readmeContent:
            'Git LFS keeps binary history lightweight. Large attachments can be shared with the team.',
        gitattributesContent: '',
      );
      const guidanceObservation = Ts73SetupRepositoryObservation(
        attachmentDirectories: <String>[],
        readmeContent: 'Store large attachments through Git LFS.',
        gitattributesContent: '',
      );

      expect(
        unrelatedObservation.readmeGuidesGitLfsForLargeFiles,
        isFalse,
        reason:
            'Separate mentions of Git LFS and large attachments should not satisfy TS-73 without actual guidance to use Git LFS.',
      );
      expect(
        guidanceObservation.readmeGuidesGitLfsForLargeFiles,
        isTrue,
        reason:
            'Direct README guidance to store large attachments through Git LFS should satisfy TS-73.',
      );
    },
  );

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
        observation.readmeGuidesAttachmentStorage,
        isTrue,
        reason:
            'The setup README should guide users to store issue attachments under an attachments/ path.',
      );
      expect(
        observation.readmeGuidesGitLfsForLargeFiles,
        isTrue,
        reason:
            'The setup README should guide users to use Git LFS for large files.',
      );
    },
  );
}
