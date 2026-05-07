import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../components/services/attachment_upload_probe.dart';
import '../../core/config/attachment_upload_test_config.dart';
import '../../frameworks/api/github/github_attachment_upload_framework.dart';

class Ts60AttachmentUploadFixture {
  Ts60AttachmentUploadFixture._({
    required this.config,
    required this.probe,
    required List<ObservedHttpRequest> observedRequests,
  }) : _observedRequests = observedRequests;

  final AttachmentUploadTestConfig config;
  final AttachmentUploadProbe probe;
  final List<ObservedHttpRequest> _observedRequests;

  static Future<Ts60AttachmentUploadFixture> create() async {
    final config = AttachmentUploadTestConfig.ts60;
    final observedRequests = <ObservedHttpRequest>[];
    final framework = await GitHubAttachmentUploadFramework.create(
      config: config,
      responder: (request) async {
        observedRequests.add(
          ObservedHttpRequest(method: request.method, path: request.url.path),
        );
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
          return githubContentResponse(
            '*.psd filter=lfs diff=lfs merge=lfs -text\n',
          );
        }

        if (path.endsWith('/contents/${config.path}') &&
            request.method == 'PUT') {
          return http.Response('{"content":{"sha":"uploaded-sha"}}', 201);
        }

        return http.Response('', 404);
      },
    );

    return Ts60AttachmentUploadFixture._(
      config: config,
      probe: AttachmentUploadProbe(framework),
      observedRequests: observedRequests,
    );
  }

  Future<Ts60AttachmentUploadRun> uploadSampleAttachment() async {
    final observation = await probe.upload(
      config.buildWriteRequest(Uint8List.fromList('binary-content'.codeUnits)),
    );
    return Ts60AttachmentUploadRun(
      observation: observation,
      observedRequests: List<ObservedHttpRequest>.unmodifiable(
        _observedRequests,
      ),
    );
  }
}

class Ts60AttachmentUploadRun {
  const Ts60AttachmentUploadRun({
    required this.observation,
    required this.observedRequests,
  });

  final AttachmentUploadObservation observation;
  final List<ObservedHttpRequest> observedRequests;

  bool get queriedGitAttributes => observedRequests.any(
    (request) =>
        request.method == 'GET' &&
        request.path.endsWith('/contents/.gitattributes'),
  );

  List<String> get requestDescriptions => observedRequests
      .map((request) => request.describe())
      .toList(growable: false);

  List<String> get uploadRequestDescriptions => observedRequests
      .where(
        (request) =>
            request.method == 'PUT' &&
            request.path.endsWith('/contents/${observation.path}'),
      )
      .map((request) => request.describe())
      .toList(growable: false);
}

class ObservedHttpRequest {
  const ObservedHttpRequest({required this.method, required this.path});

  final String method;
  final String path;

  String describe() => '$method $path';
}
