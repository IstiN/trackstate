import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/services/attachment_upload_probe.dart';

void main() {
  test(
    'TS-44 reports an explicit unsupported outcome for LFS attachment uploads',
    () async {
      var uploadAttempts = 0;
      final provider = GitHubTrackStateProvider(
        repositoryName: 'IstiN/trackstate',
        dataRef: 'main',
        client: MockClient((request) async {
          final path = request.url.path;

          if (path.endsWith('/repos/IstiN/trackstate') &&
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

          if (path.endsWith('/contents/attachments/screenshot.png') &&
              request.method == 'PUT') {
            uploadAttempts++;
            return http.Response('{"content":{"sha":"uploaded-sha"}}', 201);
          }

          return http.Response('', 404);
        }),
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'main',
          token: 'test-token',
        ),
      );

      final observation = await AttachmentUploadProbe(provider).upload(
        RepositoryAttachmentWriteRequest(
          path: 'attachments/screenshot.png',
          bytes: Uint8List.fromList('binary-content'.codeUnits),
          message: 'Upload screenshot attachment',
          branch: 'main',
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
