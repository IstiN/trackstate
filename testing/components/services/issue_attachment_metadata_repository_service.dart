import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_attachment_metadata_loader.dart';
import '../../core/models/issue_attachment_metadata_observation.dart';

class IssueAttachmentMetadataRepositoryService
    implements IssueAttachmentMetadataLoader {
  const IssueAttachmentMetadataRepositoryService({required this.repository});

  final TrackStateRepository repository;

  @override
  Future<List<IssueAttachmentMetadataObservation>> loadAttachmentMetadata(
    String issueKey,
  ) async {
    final snapshot = await repository.loadSnapshot();
    final issue = _findIssue(snapshot.issues, issueKey);
    return issue.attachments
        .map(IssueAttachmentMetadataObservation.fromAttachment)
        .toList(growable: false);
  }

  TrackStateIssue _findIssue(List<TrackStateIssue> issues, String issueKey) {
    for (final issue in issues) {
      if (issue.key == issueKey) {
        return issue;
      }
    }
    throw StateError(
      'Issue $issueKey was not loaded from the repository snapshot.',
    );
  }
}
