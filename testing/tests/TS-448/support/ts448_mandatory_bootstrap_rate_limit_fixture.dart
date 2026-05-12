import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

enum Ts448MandatoryBootstrapArtifact { projectJson, issuesIndex }

class Ts448MandatoryBootstrapRateLimitFixture {
  Ts448MandatoryBootstrapRateLimitFixture._({
    required this.artifact,
    required this.repository,
    required Map<String, int> requestCounts,
  }) : _requestCounts = requestCounts;

  static const String repositoryName = 'octo/ts448-mandatory-bootstrap';
  static const String branch = 'main';
  static const String projectPath = 'TRACK/project.json';
  static const String issuesIndexPath = 'TRACK/.trackstate/index/issues.json';

  final Ts448MandatoryBootstrapArtifact artifact;
  final TrackStateRepository repository;
  final Map<String, int> _requestCounts;

  String get artifactLabel => switch (artifact) {
    Ts448MandatoryBootstrapArtifact.projectJson => 'project.json',
    Ts448MandatoryBootstrapArtifact.issuesIndex => 'issues.json',
  };

  String get failingContentPath => switch (artifact) {
    Ts448MandatoryBootstrapArtifact.projectJson => projectPath,
    Ts448MandatoryBootstrapArtifact.issuesIndex => issuesIndexPath,
  };

  String get failingRequestPath =>
      '/repos/$repositoryName/contents/$failingContentPath';

  int requestCount(String path) => _requestCounts[path] ?? 0;

  List<String> get requestedPaths => [
    for (final path in _requestCounts.keys.toList()..sort()) path,
  ];

  static Future<Ts448MandatoryBootstrapRateLimitFixture> create({
    required Ts448MandatoryBootstrapArtifact artifact,
  }) async {
    final requestCounts = <String, int>{};
    final repository = SetupTrackStateRepository(
      client: MockClient(
        (request) => _handleHostedRequest(
          request,
          artifact: artifact,
          requestCounts: requestCounts,
        ),
      ),
      repositoryName: repositoryName,
      sourceRef: branch,
      dataRef: branch,
    );
    return Ts448MandatoryBootstrapRateLimitFixture._(
      artifact: artifact,
      repository: repository,
      requestCounts: requestCounts,
    );
  }
}

Future<http.Response> _handleHostedRequest(
  http.Request request, {
  required Ts448MandatoryBootstrapArtifact artifact,
  required Map<String, int> requestCounts,
}) async {
  final path = request.url.path;
  requestCounts[path] = (requestCounts[path] ?? 0) + 1;

  if (path ==
      '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/git/trees/${Ts448MandatoryBootstrapRateLimitFixture.branch}') {
    return http.Response(jsonEncode(_treeResponse), 200);
  }

  final failingRequestPath = switch (artifact) {
    Ts448MandatoryBootstrapArtifact.projectJson =>
      '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/contents/${Ts448MandatoryBootstrapRateLimitFixture.projectPath}',
    Ts448MandatoryBootstrapArtifact.issuesIndex =>
      '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/contents/${Ts448MandatoryBootstrapRateLimitFixture.issuesIndexPath}',
  };

  if (path == failingRequestPath && requestCounts[path] == 1) {
    return http.Response(
      jsonEncode({
        'message':
            'API rate limit exceeded for 203.0.113.10. Authenticated requests get a higher rate limit.',
        'documentation_url':
            'https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting',
      }),
      403,
      headers: const {'x-ratelimit-remaining': '0', 'retry-after': '60'},
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

String _shaFor(String path) {
  return switch (path) {
    '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/contents/TRACK/project.json' =>
      'project-sha',
    '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/contents/TRACK/config/statuses.json' =>
      'statuses-sha',
    '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/contents/TRACK/config/issue-types.json' =>
      'issue-types-sha',
    '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/contents/TRACK/config/fields.json' =>
      'fields-sha',
    '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/contents/TRACK/config/workflows.json' =>
      'workflows-sha',
    '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/contents/TRACK/config/priorities.json' =>
      'priorities-sha',
    '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/contents/TRACK/.trackstate/index/issues.json' =>
      'index-sha',
    '/repos/${Ts448MandatoryBootstrapRateLimitFixture.repositoryName}/contents/TRACK/TRACK-448/main.md' =>
      'issue-sha',
    _ => 'sha',
  };
}

const _treeResponse = {
  'tree': [
    {'path': 'TRACK/project.json', 'type': 'blob'},
    {'path': 'TRACK/config/statuses.json', 'type': 'blob'},
    {'path': 'TRACK/config/issue-types.json', 'type': 'blob'},
    {'path': 'TRACK/config/fields.json', 'type': 'blob'},
    {'path': 'TRACK/config/workflows.json', 'type': 'blob'},
    {'path': 'TRACK/config/priorities.json', 'type': 'blob'},
    {'path': 'TRACK/.trackstate/index/issues.json', 'type': 'blob'},
    {'path': 'TRACK/TRACK-448/main.md', 'type': 'blob'},
  ],
};

const _contentResponses = {
  '/repos/octo/ts448-mandatory-bootstrap/contents/TRACK/project.json':
      '{"key":"TRACK","name":"TrackState.AI","defaultLocale":"en"}',
  '/repos/octo/ts448-mandatory-bootstrap/contents/TRACK/config/statuses.json':
      '[{"id":"todo","name":"To Do","category":"new"},{"id":"in-progress","name":"In Progress","category":"indeterminate"},{"id":"done","name":"Done","category":"done"}]',
  '/repos/octo/ts448-mandatory-bootstrap/contents/TRACK/config/issue-types.json':
      '[{"id":"story","name":"Story","workflowId":"default","hierarchyLevel":0}]',
  '/repos/octo/ts448-mandatory-bootstrap/contents/TRACK/config/fields.json':
      '[{"id":"summary","name":"Summary","type":"string","required":true,"reserved":true},{"id":"description","name":"Description","type":"markdown","reserved":true}]',
  '/repos/octo/ts448-mandatory-bootstrap/contents/TRACK/config/workflows.json':
      '{"default":{"name":"Default Workflow","statuses":["todo","in-progress","done"],"transitions":[{"id":"start","name":"Start progress","from":"todo","to":"in-progress"},{"id":"finish","name":"Complete","from":"in-progress","to":"done"}]}}',
  '/repos/octo/ts448-mandatory-bootstrap/contents/TRACK/config/priorities.json':
      '[{"id":"high","name":"High"}]',
  '/repos/octo/ts448-mandatory-bootstrap/contents/TRACK/.trackstate/index/issues.json':
      '[{"key":"TRACK-448","path":"TRACK/TRACK-448/main.md","parent":null,"epic":null,"parentPath":null,"epicPath":null,"summary":"Mandatory bootstrap shell recovery issue","issueType":"story","status":"in-progress","priority":"high","assignee":"qa-user","labels":["startup-recovery"],"updated":"2026-05-12T06:00:00Z","children":[],"archived":false}]',
  '/repos/octo/ts448-mandatory-bootstrap/contents/TRACK/TRACK-448/main.md':
      '---\nkey: TRACK-448\nproject: TRACK\nissueType: story\nstatus: in-progress\npriority: high\nsummary: Mandatory bootstrap shell recovery issue\nassignee: qa-user\nreporter: qa-user\nlabels:\n  - startup-recovery\nupdated: 2026-05-12T06:00:00Z\n---\n\n# Description\n\nRetry should restore the hosted shell after the initial mandatory bootstrap rate-limit response.\n',
};
