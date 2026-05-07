import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../../core/config/attachment_upload_test_config.dart';
import '../../../core/interfaces/attachment_upload_port.dart';

typedef GitHubHttpResponder = Future<http.Response> Function(
  http.BaseRequest request,
);

class GitHubAttachmentUploadFramework implements AttachmentUploadPort {
  GitHubAttachmentUploadFramework._(this._provider);

  final GitHubTrackStateProvider _provider;

  static Future<GitHubAttachmentUploadFramework> create({
    required AttachmentUploadTestConfig config,
    required GitHubHttpResponder responder,
  }) async {
    final framework = GitHubAttachmentUploadFramework._(
      GitHubTrackStateProvider(
        repositoryName: config.repository,
        dataRef: config.branch,
        client: MockClient(responder),
      ),
    );
    await framework._provider.authenticate(config.connection);
    return framework;
  }

  @override
  Future<bool> isLfsTracked(String path) => _provider.isLfsTracked(path);

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) => _provider.writeAttachment(request);
}

http.Response githubContentResponse(String content) {
  final encoded = base64Encode(utf8.encode(content));
  return http.Response('{"content":"$encoded","sha":"abc123"}', 200);
}
