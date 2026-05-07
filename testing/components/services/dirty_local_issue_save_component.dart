import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../frameworks/providers/trackstate_provider_dirty_local_issue_write_client.dart';
import 'dirty_local_issue_save_service.dart';

class DirtyLocalIssueSaveComponent {
  DirtyLocalIssueSaveComponent._(this._service);

  factory DirtyLocalIssueSaveComponent.create({
    required TrackStateProviderAdapter provider,
    required String issueKey,
    required String issuePath,
    required String originalDescription,
  }) {
    return DirtyLocalIssueSaveComponent._(
      DirtyLocalIssueSaveService(
        provider: TrackStateProviderDirtyLocalIssueWriteClient(
          provider: provider,
        ),
        issueKey: issueKey,
        issuePath: issuePath,
        originalDescription: originalDescription,
      ),
    );
  }

  final DirtyLocalIssueSaveService _service;

  Future<void> attemptDescriptionSave(String updatedDescription) {
    return _service.attemptDescriptionSave(updatedDescription);
  }
}
