import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../components/services/attachment_upload_probe.dart';
import '../../core/config/attachment_upload_test_config.dart';
import '../../frameworks/api/github/github_attachment_upload_framework.dart';

class Ts61MissingGitattributesFixture {
  Ts61MissingGitattributesFixture._({
    required this.config,
    required this.probe,
    required List<RecordedGitHubRequest> recordedRequests,
  }) : _recordedRequests = recordedRequests;

  final AttachmentUploadTestConfig config;
  final AttachmentUploadProbe probe;
  final List<RecordedGitHubRequest> _recordedRequests;

  static Future<Ts61MissingGitattributesFixture> create() async {
    final config = AttachmentUploadTestConfig.ts61;
    final recordedRequests = <RecordedGitHubRequest>[];
    final framework = await GitHubAttachmentUploadFramework.create(
      config: config,
      responder: (request) async {
        final recordedRequest = await RecordedGitHubRequest.fromRequest(
          request,
        );
        recordedRequests.add(recordedRequest);

        final path = request.url.path;

        if (path.endsWith('/repos/${config.repository}') &&
            request.method == 'GET') {
          return http.Response(
            '{"permissions":{"pull":true,"push":true,"admin":false}}',
            200,
          );
        }

        if (path.endsWith('/user') && request.method == 'GET') {
          return http.Response('{"login":"octocat","name":"Mona"}', 200);
        }

        if (path.endsWith('/contents/.gitattributes') &&
            request.method == 'GET') {
          return http.Response('{"message":"Not Found"}', 404);
        }

        if (path.endsWith('/contents/${config.path}') &&
            request.method == 'PUT') {
          return http.Response('{"content":{"sha":"uploaded-notes-sha"}}', 201);
        }

        return http.Response('', 404);
      },
    );

    return Ts61MissingGitattributesFixture._(
      config: config,
      probe: AttachmentUploadProbe(framework),
      recordedRequests: recordedRequests,
    );
  }

  Future<Ts61UploadScenarioObservation> uploadSampleAttachment() async {
    final observation = await probe.upload(
      config.buildWriteRequest(
        Uint8List.fromList(utf8.encode('text attachment content')),
      ),
    );
    return Ts61UploadScenarioObservation(
      uploadObservation: observation,
      recordedRequests: List<RecordedGitHubRequest>.unmodifiable(
        _recordedRequests,
      ),
    );
  }
}

class Ts61UploadScenarioObservation {
  const Ts61UploadScenarioObservation({
    required this.uploadObservation,
    required this.recordedRequests,
  });

  final AttachmentUploadObservation uploadObservation;
  final List<RecordedGitHubRequest> recordedRequests;

  RecordedGitHubRequest? get gitattributesLookup => recordedRequests
      .where(
        (request) =>
            request.method == 'GET' &&
            request.path.endsWith('/contents/.gitattributes'),
      )
      .cast<RecordedGitHubRequest?>()
      .firstWhere((request) => request != null, orElse: () => null);

  RecordedGitHubRequest? get contentsUpload => recordedRequests
      .where(
        (request) =>
            request.method == 'PUT' &&
            request.path.endsWith('/contents/${uploadObservation.path}'),
      )
      .cast<RecordedGitHubRequest?>()
      .firstWhere((request) => request != null, orElse: () => null);

  bool get attemptedStandardUpload => contentsUpload != null;
}

class RecordedGitHubRequest {
  const RecordedGitHubRequest({
    required this.method,
    required this.path,
    required this.query,
    required this.body,
  });

  final String method;
  final String path;
  final Map<String, String> query;
  final String body;

  static Future<RecordedGitHubRequest> fromRequest(
    http.BaseRequest request,
  ) async {
    final body = switch (request) {
      http.Request() => request.body,
      _ => '',
    };
    return RecordedGitHubRequest(
      method: request.method,
      path: request.url.path,
      query: Map<String, String>.from(request.url.queryParameters),
      body: body,
    );
  }

  Object? get jsonBody => body.isEmpty ? null : jsonDecode(body);
}
