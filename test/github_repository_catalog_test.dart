import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'GitHub provider lists accessible repositories after authentication',
    () async {
      final client = MockClient((request) async {
        switch (request.url.path) {
          case '/repos/owner/current':
            return http.Response(
              jsonEncode({'full_name': 'owner/current'}),
              200,
            );
          case '/user':
            return http.Response(
              jsonEncode({
                'login': 'workspace-tester',
                'name': 'Workspace Tester',
              }),
              200,
            );
          case '/user/repos':
            return http.Response(
              jsonEncode([
                {'full_name': 'owner/next-repo', 'default_branch': 'release'},
                {
                  'full_name': 'owner/platform-foundation',
                  'default_branch': 'main',
                },
              ]),
              200,
            );
        }
        throw StateError('Unexpected request: ${request.url}');
      });

      final provider = GitHubTrackStateProvider(
        client: client,
        repositoryName: 'owner/current',
        dataRef: 'main',
        sourceRef: 'main',
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'owner/current',
          branch: 'main',
          token: 'token',
        ),
      );
      final repositories = await provider.listAccessibleRepositories();

      expect(repositories.map((repository) => repository.fullName).toList(), [
        'owner/next-repo',
        'owner/platform-foundation',
      ]);
      expect(repositories.first.defaultBranch, 'release');
    },
  );

  test(
    'GitHub provider requires authentication before listing repositories',
    () async {
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          throw StateError('Unexpected request: ${request.url}');
        }),
        repositoryName: 'owner/current',
        dataRef: 'main',
        sourceRef: 'main',
      );

      await expectLater(
        provider.listAccessibleRepositories(),
        throwsA(isA<TrackStateProviderException>()),
      );
    },
  );
}
