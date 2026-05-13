import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class IssueAttachmentUploadPort {
  TrackerSnapshot? get cachedSnapshot;

  void replaceCachedState({
    required TrackerSnapshot snapshot,
    required List<RepositoryTreeEntry> tree,
  });

  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  });
}
