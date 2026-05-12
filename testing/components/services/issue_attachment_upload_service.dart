import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_attachment_upload_driver.dart';
import '../../core/interfaces/issue_attachment_upload_port.dart';

class IssueAttachmentUploadService implements IssueAttachmentUploadPort {
  const IssueAttachmentUploadService({
    required IssueAttachmentUploadDriver attachmentDriver,
  }) : _attachmentDriver = attachmentDriver;

  final IssueAttachmentUploadDriver _attachmentDriver;

  @override
  TrackerSnapshot? get cachedSnapshot => _attachmentDriver.cachedSnapshot;

  @override
  void replaceCachedState({
    required TrackerSnapshot snapshot,
    required List<RepositoryTreeEntry> tree,
  }) {
    _attachmentDriver.replaceCachedState(snapshot: snapshot, tree: tree);
  }

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) => _attachmentDriver.uploadIssueAttachment(
    issue: issue,
    name: name,
    bytes: bytes,
  );
}
