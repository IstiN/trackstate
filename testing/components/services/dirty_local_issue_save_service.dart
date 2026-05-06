import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../core/utils/local_trackstate_fixture.dart';

class DirtyLocalIssueSaveService {
  const DirtyLocalIssueSaveService(this.fixture);

  final LocalTrackStateFixture fixture;

  Future<void> attemptDescriptionSave() async {
    final provider = fixture.provider;
    final branch = await provider.resolveWriteBranch();
    final original = await provider.readTextFile(
      LocalTrackStateFixture.issuePath,
      ref: branch,
    );
    final updatedContent = await fixture.buildUpdatedDescriptionMarkdown();

    await provider.writeTextFile(
      RepositoryWriteRequest(
        path: LocalTrackStateFixture.issuePath,
        content: updatedContent,
        message: 'Update ${LocalTrackStateFixture.issueKey} description',
        branch: branch,
        expectedRevision: original.revision,
      ),
    );
  }
}
