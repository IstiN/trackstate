import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../components/services/attachment_upload_probe.dart';
import '../../core/config/attachment_upload_test_config.dart';
import '../../frameworks/api/github/github_attachment_upload_framework.dart';

class Ts44AttachmentUploadFixture {
  Ts44AttachmentUploadFixture._({
    required this.config,
    required this.probe,
    required int Function() uploadAttempts,
  }) : _uploadAttempts = uploadAttempts;

  final AttachmentUploadTestConfig config;
  final AttachmentUploadProbe probe;
  final int Function() _uploadAttempts;

  int get uploadAttempts => _uploadAttempts();

  static Future<Ts44AttachmentUploadFixture> create() async {
    final config = AttachmentUploadTestConfig.ts44;
    var uploadAttempts = 0;
    final framework = await GitHubAttachmentUploadFramework.create(
      config: config,
      responder: (request) async {
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
            '*.png filter=lfs diff=lfs merge=lfs -text\n',
          );
        }

        if (path.endsWith('/contents/${config.path}') &&
            request.method == 'PUT') {
          uploadAttempts++;
          return http.Response('{"content":{"sha":"uploaded-sha"}}', 201);
        }

        return http.Response('', 404);
      },
    );

    return Ts44AttachmentUploadFixture._(
      config: config,
      probe: AttachmentUploadProbe(framework),
      uploadAttempts: () => uploadAttempts,
    );
  }

  Future<AttachmentUploadObservation> uploadSampleAttachment() {
    return probe.upload(
      config.buildWriteRequest(
        Uint8List.fromList('binary-content'.codeUnits),
      ),
    );
  }
}
