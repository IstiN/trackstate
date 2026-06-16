import 'package:trackstate/domain/models/trackstate_models.dart';

class IssueAttachmentMetadataObservation {
  const IssueAttachmentMetadataObservation({
    required this.id,
    required this.name,
    required this.mediaType,
    required this.sizeBytes,
    required this.author,
    required this.createdAt,
    required this.storagePath,
    required this.revisionOrOid,
  });

  factory IssueAttachmentMetadataObservation.fromAttachment(
    IssueAttachment attachment,
  ) {
    return IssueAttachmentMetadataObservation(
      id: attachment.id,
      name: attachment.name,
      mediaType: attachment.mediaType,
      sizeBytes: attachment.sizeBytes,
      author: attachment.author,
      createdAt: attachment.createdAt,
      storagePath: attachment.storagePath,
      revisionOrOid: attachment.revisionOrOid,
    );
  }

  final String id;
  final String name;
  final String mediaType;
  final int sizeBytes;
  final String author;
  final String createdAt;
  final String storagePath;
  final String revisionOrOid;

  Map<String, Object> toMap() {
    return <String, Object>{
      'id': id,
      'name': name,
      'mediaType': mediaType,
      'sizeBytes': sizeBytes,
      'author': author,
      'createdAt': createdAt,
      'storagePath': storagePath,
      'revisionOrOid': revisionOrOid,
    };
  }
}
