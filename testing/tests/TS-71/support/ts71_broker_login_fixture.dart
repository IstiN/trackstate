import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

class Ts71BrokerLoginFixture {
  static const repositoryName = 'octo/broker-fork';
  static const branch = 'main';
  static const exchangedToken = 'broker-user-token';
  static const connectedLogin = 'broker-user';
  static const issueKey = 'TRACK-71';
  static const issueSummary = 'Brokered auth loads tracker data';

  final List<Ts71HttpRequest> requests = <Ts71HttpRequest>[];

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

  List<String> get requestDescriptions =>
      requests.map((request) => request.description).toList(growable: false);

  List<String> bearerTokensForPath(String path) {
    return requests
        .where((request) => request.path == path)
        .map((request) => request.bearerToken)
        .whereType<String>()
        .toList(growable: false);
  }

  Future<http.Response> _handleRequest(http.Request request) async {
    requests.add(
      Ts71HttpRequest(
        method: request.method,
        path: request.url.path,
        queryParameters: request.url.queryParameters,
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
          'name': 'broker-fork',
          'full_name': repositoryName,
          'permissions': {'pull': true, 'push': true, 'admin': false},
        }),
        200,
      );
    }
    if (path == '/user') {
      return http.Response(
        jsonEncode({'login': connectedLogin, 'name': 'Broker User'}),
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
      '/repos/$repositoryName/contents/TRACK/project.json' => 'project-sha',
      '/repos/$repositoryName/contents/TRACK/config/statuses.json' =>
        'statuses-sha',
      '/repos/$repositoryName/contents/TRACK/config/issue-types.json' =>
        'issue-types-sha',
      '/repos/$repositoryName/contents/TRACK/config/fields.json' => 'fields-sha',
      '/repos/$repositoryName/contents/TRACK/TRACK-71/main.md' => 'issue-sha',
      _ => 'sha',
    };
  }
}

class Ts71HttpRequest {
  const Ts71HttpRequest({
    required this.method,
    required this.path,
    required this.queryParameters,
    required this.bearerToken,
  });

  final String method;
  final String path;
  final Map<String, String> queryParameters;
  final String? bearerToken;

  String get description => '$method $path';
}

const _treeResponse = {
  'tree': [
    {'path': 'TRACK/project.json', 'type': 'blob'},
    {'path': 'TRACK/config/statuses.json', 'type': 'blob'},
    {'path': 'TRACK/config/issue-types.json', 'type': 'blob'},
    {'path': 'TRACK/config/fields.json', 'type': 'blob'},
    {'path': 'TRACK/TRACK-71/main.md', 'type': 'blob'},
  ],
};

const _contentResponses = {
  '/repos/octo/broker-fork/contents/TRACK/project.json':
      '{"key":"TRACK","name":"Broker Login Demo","defaultLocale":"en"}',
  '/repos/octo/broker-fork/contents/TRACK/config/statuses.json':
      '[{"name":"To Do"},{"name":"In Progress"},{"name":"Done"}]',
  '/repos/octo/broker-fork/contents/TRACK/config/issue-types.json':
      '[{"name":"Epic"},{"name":"Story"}]',
  '/repos/octo/broker-fork/contents/TRACK/config/fields.json':
      '[{"name":"Summary"},{"name":"Priority"}]',
  '/repos/octo/broker-fork/contents/TRACK/TRACK-71/main.md':
      '---\nkey: TRACK-71\nproject: TRACK\nissueType: Story\nstatus: In Progress\npriority: High\nsummary: Brokered auth loads tracker data\nassignee: broker-user\nreporter: broker-admin\nlabels:\n  - broker-login\ncomponents:\n  - web\nupdated: 2026-05-07T00:00:00Z\n---\n\n# Description\n\nVerify the user-scoped broker login continues to expose tracker data in the hosted UI.\n',
};
