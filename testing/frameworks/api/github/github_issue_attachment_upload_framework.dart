import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../../core/interfaces/issue_attachment_upload_driver.dart';

typedef GitHubIssueAttachmentResponder =
    Future<http.Response> Function(http.BaseRequest request);

class GitHubIssueAttachmentUploadFramework
    implements IssueAttachmentUploadDriver {
  GitHubIssueAttachmentUploadFramework._(this._repository);

  final ProviderBackedTrackStateRepository _repository;

  static Future<GitHubIssueAttachmentUploadFramework> create({
    required String repositoryName,
    required String branch,
    required String token,
    required GitHubIssueAttachmentResponder responder,
  }) async {
    final repository = ProviderBackedTrackStateRepository(
      provider: GitHubTrackStateProvider(
        repositoryName: repositoryName,
        dataRef: branch,
        client: MockClient(responder),
      ),
    );
    await repository.connect(
      RepositoryConnection(
        repository: repositoryName,
        branch: branch,
        token: token,
      ),
    );
    return GitHubIssueAttachmentUploadFramework._(repository);
  }

  @override
  TrackerSnapshot? get cachedSnapshot => _repository.cachedSnapshot;

  @override
  void replaceCachedState({
    required TrackerSnapshot snapshot,
    required List<RepositoryTreeEntry> tree,
  }) {
    _repository.replaceCachedState(snapshot: snapshot, tree: tree);
  }

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) =>
      _repository.uploadIssueAttachment(issue: issue, name: name, bytes: bytes);
}
