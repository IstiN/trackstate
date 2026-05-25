@TestOn('browser')
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'browser GitHub sessions keep release-backed attachment uploads disabled for writable repositories',
    () async {
      final provider = GitHubTrackStateProvider(
        repositoryName: 'IstiN/trackstate',
        dataRef: 'main',
        client: MockClient((request) async {
          switch (request.url.path) {
            case '/repos/IstiN/trackstate':
              return http.Response(
                '{"permissions":{"pull":true,"push":true,"admin":false}}',
                200,
              );
            case '/user':
              return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          return http.Response('', 404);
        }),
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'main',
          token: 'token',
        ),
      );
      final permission = await provider.getPermission();

      expect(permission.canWrite, isTrue);
      expect(permission.canManageAttachments, isTrue);
      expect(permission.supportsReleaseAttachmentWrites, isFalse);
    },
  );
}
