import 'package:trackstate/data/providers/trackstate_provider.dart';

class DirtyLocalIssueSaveService {
  const DirtyLocalIssueSaveService({
    required this.provider,
    required this.issueKey,
    required this.issuePath,
    required this.originalDescription,
  });

  final TrackStateProviderAdapter provider;
  final String issueKey;
  final String issuePath;
  final String originalDescription;

  Future<void> attemptDescriptionSave(String updatedDescription) async {
    final branch = await provider.resolveWriteBranch();
    final original = await provider.readTextFile(issuePath, ref: branch);
    final updatedContent = original.content.replaceFirst(
      originalDescription,
      updatedDescription,
    );

    await provider.writeTextFile(
      RepositoryWriteRequest(
        path: issuePath,
        content: updatedContent,
        message: 'Update $issueKey description',
        branch: branch,
        expectedRevision: original.revision,
      ),
    );
  }
}
