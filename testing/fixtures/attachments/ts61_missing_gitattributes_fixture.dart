import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../core/config/attachment_upload_test_config.dart';
import '../../frameworks/api/github/github_attachment_upload_framework.dart';

class Ts61MissingGitattributesFixture {
  Ts61MissingGitattributesFixture._({
    required this.config,
    required this.framework,
    required List<RecordedGitHubRequest> recordedRequests,
  }) : _recordedRequests = recordedRequests;

  final AttachmentUploadTestConfig config;
  final GitHubAttachmentUploadFramework framework;
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

    recordedRequests.clear();

    return Ts61MissingGitattributesFixture._(
      config: config,
      framework: framework,
      recordedRequests: recordedRequests,
    );
  }

  Future<Ts61UploadScenarioObservation> uploadSampleAttachment() async {
    try {
      final result = await framework.writeAttachment(
        config.buildWriteRequest(
          Uint8List.fromList(utf8.encode('text attachment content')),
        ),
      );
      return Ts61UploadScenarioObservation(
        config: config,
        uploadResult: result,
        recordedRequests: List<RecordedGitHubRequest>.unmodifiable(
          _recordedRequests,
        ),
      );
    } catch (error, stackTrace) {
      return Ts61UploadScenarioObservation(
        config: config,
        error: error,
        stackTrace: stackTrace,
        recordedRequests: List<RecordedGitHubRequest>.unmodifiable(
          _recordedRequests,
        ),
      );
    }
  }
}

class Ts61UploadScenarioObservation {
  const Ts61UploadScenarioObservation({
    required this.config,
    this.uploadResult,
    this.error,
    this.stackTrace,
    required this.recordedRequests,
  });

  final AttachmentUploadTestConfig config;
  final RepositoryAttachmentWriteResult? uploadResult;
  final Object? error;
  final StackTrace? stackTrace;
  final List<RecordedGitHubRequest> recordedRequests;

  List<RecordedGitHubRequest> get gitattributesLookups => recordedRequests
      .where(
        (request) =>
            request.method == 'GET' &&
            request.path.endsWith('/contents/.gitattributes'),
      )
      .toList(growable: false);

  RecordedGitHubRequest? get gitattributesLookup =>
      gitattributesLookups.isEmpty ? null : gitattributesLookups.first;

  List<RecordedGitHubRequest> get contentsUploads => recordedRequests
      .where(
        (request) =>
            request.method == 'PUT' &&
            request.path.endsWith('/contents/${config.path}'),
      )
      .toList(growable: false);

  RecordedGitHubRequest? get contentsUpload =>
      contentsUploads.isEmpty ? null : contentsUploads.first;

  List<String> get requestSequence => recordedRequests
      .map((request) => '${request.method} ${request.path}')
      .toList(growable: false);

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
