import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

class Ts106OauthIdentityFixture {
  static const repositoryName = 'octo/oauth-profile-priority';
  static const branch = 'main';
  static const remoteToken = 'oauth-priority-token';
  static const remoteLogin = 'remote-user';
  static const remoteDisplayName = 'Remote User';
  static const issueKey = 'DEMO-106';
  static const issueSummary = 'Hosted auth prefers remote identity';

  final List<Ts106HttpRequest> requests = <Ts106HttpRequest>[];

  TrackStateRepository createRepository() {
    return SetupTrackStateRepository(
      client: MockClient(_handleRequest),
      repositoryName: repositoryName,
      sourceRef: branch,
      dataRef: branch,
    );
  }

  String get tokenPreferenceKey =>
      'trackstate.githubToken.${repositoryName.replaceAll('/', '.')}';

  List<String> bearerTokensForPath(String path) {
    return requests
        .where((request) => request.path == path)
        .map((request) => request.bearerToken)
        .whereType<String>()
        .toList(growable: false);
  }

  Future<http.Response> _handleRequest(http.Request request) async {
    requests.add(
      Ts106HttpRequest(
        method: request.method,
        path: request.url.path,
        bearerToken: _bearerTokenFromHeaders(request.headers),
      ),
    );

    final path = request.url.path;
    if (path == '/repos/$repositoryName/git/trees/$branch') {
      return http.Response(jsonEncode(_treeResponse), 200);
    }
    if (path == '/repos/$repositoryName') {
      return http.Response(
        jsonEncode({
          'name': 'oauth-profile-priority',
          'full_name': repositoryName,
          'permissions': {'pull': true, 'push': true, 'admin': false},
        }),
        200,
      );
    }
    if (path == '/user') {
      return http.Response(
        jsonEncode({'login': remoteLogin, 'name': remoteDisplayName}),
        200,
      );
    }
    final content = _contentResponses[path];
    if (content != null) {
      return http.Response(
        jsonEncode({
          'content': base64Encode(utf8.encode(content)),
          'sha': _shaFor(path),
        }),
        200,
      );
    }
    return http.Response('not found: $path', 404);
  }

  String? _bearerTokenFromHeaders(Map<String, String> headers) {
    final authorization = headers['authorization'];
    if (authorization == null || !authorization.startsWith('Bearer ')) {
      return null;
    }
    return authorization.substring('Bearer '.length);
  }

  String _shaFor(String path) {
    return switch (path) {
      '/repos/$repositoryName/contents/DEMO/project.json' => 'project-sha',
      '/repos/$repositoryName/contents/DEMO/config/statuses.json' =>
        'statuses-sha',
      '/repos/$repositoryName/contents/DEMO/config/issue-types.json' =>
        'issue-types-sha',
      '/repos/$repositoryName/contents/DEMO/config/fields.json' => 'fields-sha',
      '/repos/$repositoryName/contents/DEMO/$issueKey/main.md' => 'issue-sha',
      _ => 'sha',
    };
  }
}

class Ts106HttpRequest {
  const Ts106HttpRequest({
    required this.method,
    required this.path,
    required this.bearerToken,
  });

  final String method;
  final String path;
  final String? bearerToken;
}

const _treeResponse = {
  'tree': [
    {'path': 'DEMO/project.json', 'type': 'blob'},
    {'path': 'DEMO/config/statuses.json', 'type': 'blob'},
    {'path': 'DEMO/config/issue-types.json', 'type': 'blob'},
    {'path': 'DEMO/config/fields.json', 'type': 'blob'},
    {'path': 'DEMO/DEMO-106/main.md', 'type': 'blob'},
  ],
};

const _contentResponses = {
  '/repos/octo/oauth-profile-priority/contents/DEMO/project.json':
      '{"key":"DEMO","name":"OAuth Profile Priority Demo","defaultLocale":"en"}',
  '/repos/octo/oauth-profile-priority/contents/DEMO/config/statuses.json':
      '[{"name":"To Do"},{"name":"In Progress"},{"name":"Done"}]',
  '/repos/octo/oauth-profile-priority/contents/DEMO/config/issue-types.json':
      '[{"name":"Epic"},{"name":"Story"}]',
  '/repos/octo/oauth-profile-priority/contents/DEMO/config/fields.json':
      '[{"name":"Summary"},{"name":"Priority"}]',
  '/repos/octo/oauth-profile-priority/contents/DEMO/DEMO-106/main.md':
      '---\nkey: DEMO-106\nproject: DEMO\nissueType: Story\nstatus: In Progress\npriority: High\nsummary: Hosted auth prefers remote identity\nassignee: remote-user\nreporter: remote-user\nupdated: 2026-05-09T00:00:00Z\n---\n\n# Description\n\nHosted OAuth metadata should win over local Git identity.\n',
};
