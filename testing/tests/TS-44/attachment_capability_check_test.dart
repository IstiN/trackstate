import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import '../../components/services/attachment_upload_probe.dart';
import '../../core/config/attachment_upload_test_config.dart';

void main() {
  test(
    'TS-44 reports an explicit unsupported outcome for LFS attachment uploads',
    () async {
      final config = AttachmentUploadTestConfig.ts44;
      var uploadAttempts = 0;
      final probe = await AttachmentUploadProbe.createGitHub(
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
            return _contentResponse(
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
      final observation = await probe.upload(
        config.buildWriteRequest(
          Uint8List.fromList('binary-content'.codeUnits),
        ),
      );

      expect(
        observation.isLfsTracked,
        isTrue,
        reason:
            'The provider port must identify the attachment path as LFS-tracked before upload capability is evaluated.',
      );
      expect(
        observation.signalsUnsupported,
        isTrue,
        reason:
            'Expected an explicit unsupported or not-yet-implemented outcome for the LFS upload flow, but observed ${observation.describeOutcome()}',
      );
      expect(
        uploadAttempts,
        0,
        reason:
            'An unsupported LFS upload should stop before the GitHub contents upload endpoint is called.',
      );
    },
  );
}

http.Response _contentResponse(String content) {
  final encoded = base64Encode(utf8.encode(content));
  return http.Response('{"content":"$encoded","sha":"abc123"}', 200);
}
