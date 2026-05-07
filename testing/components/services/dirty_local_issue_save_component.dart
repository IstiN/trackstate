import '../../core/interfaces/dirty_local_issue_write_client.dart';
import 'dirty_local_issue_save_service.dart';

class DirtyLocalIssueSaveComponent {
  DirtyLocalIssueSaveComponent({
    required DirtyLocalIssueWriteClient provider,
    required String issueKey,
    required String issuePath,
    required String originalDescription,
  }) : _service = DirtyLocalIssueSaveService(
         provider: provider,
         issueKey: issueKey,
         issuePath: issuePath,
         originalDescription: originalDescription,
       );

  final DirtyLocalIssueSaveService _service;

  Future<void> attemptDescriptionSave(String updatedDescription) {
    return _service.attemptDescriptionSave(updatedDescription);
  }
}
