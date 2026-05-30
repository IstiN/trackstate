import '../models/issue_attachment_metadata_observation.dart';

abstract interface class IssueAttachmentMetadataLoader {
  Future<List<IssueAttachmentMetadataObservation>> loadAttachmentMetadata(
    String issueKey,
  );
}
