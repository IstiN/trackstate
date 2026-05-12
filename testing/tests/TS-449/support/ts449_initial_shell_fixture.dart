import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts449InitialShellFixture {
  Ts449InitialShellFixture._({required this.repository});

  static const Duration initialSearchDelay = Duration(seconds: 4);
  static const String hydratedIssueSummary = 'Hosted shell issue stays visible';

  final Ts449DelayedInitialSearchRepository repository;

  static Future<Ts449InitialShellFixture> create() async {
    final repository = Ts449DelayedInitialSearchRepository(
      _createHostedRepository(),
      initialSearchDelay: initialSearchDelay,
    );
    return Ts449InitialShellFixture._(repository: repository);
  }

  Future<void> dispose() async {}
}

TrackStateRepository _createHostedRepository() {
  return SetupTrackStateRepository(
    client: MockClient(_handleHostedRequest),
    repositoryName: _repositoryName,
    sourceRef: _branch,
    dataRef: _branch,
  );
}

Future<http.Response> _handleHostedRequest(http.Request request) async {
  final path = request.url.path;
  if (path == '/repos/$_repositoryName/git/trees/$_branch') {
    return http.Response(jsonEncode(_treeResponse), 200);
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
    '/repos/$_repositoryName/contents/TRACK/project.json' => 'project-sha',
    '/repos/$_repositoryName/contents/TRACK/config/statuses.json' =>
      'statuses-sha',
    '/repos/$_repositoryName/contents/TRACK/config/issue-types.json' =>
      'issue-types-sha',
    '/repos/$_repositoryName/contents/TRACK/config/fields.json' => 'fields-sha',
    '/repos/$_repositoryName/contents/TRACK/config/priorities.json' =>
      'priorities-sha',
    '/repos/$_repositoryName/contents/TRACK/config/workflows.json' =>
      'workflows-sha',
    '/repos/$_repositoryName/contents/TRACK/.trackstate/index/issues.json' =>
      'index-sha',
    '/repos/$_repositoryName/contents/TRACK/TRACK-449/main.md' => 'issue-sha',
    _ => 'sha',
  };
}

const String _repositoryName = 'octo/ts449-hosted-shell';
const String _branch = 'main';

const _treeResponse = {
  'tree': [
    {'path': 'TRACK/project.json', 'type': 'blob'},
    {'path': 'TRACK/config/statuses.json', 'type': 'blob'},
    {'path': 'TRACK/config/issue-types.json', 'type': 'blob'},
    {'path': 'TRACK/config/fields.json', 'type': 'blob'},
    {'path': 'TRACK/config/priorities.json', 'type': 'blob'},
    {'path': 'TRACK/config/workflows.json', 'type': 'blob'},
    {'path': 'TRACK/.trackstate/index/issues.json', 'type': 'blob'},
    {'path': 'TRACK/TRACK-449/main.md', 'type': 'blob'},
  ],
};

const _contentResponses = {
  '/repos/octo/ts449-hosted-shell/contents/TRACK/project.json':
      '{"key":"TRACK","name":"Hosted Shell Demo","defaultLocale":"en"}',
  '/repos/octo/ts449-hosted-shell/contents/TRACK/config/statuses.json':
      '[{"id":"todo","name":"To Do"},{"id":"in-progress","name":"In Progress"},{"id":"done","name":"Done"}]',
  '/repos/octo/ts449-hosted-shell/contents/TRACK/config/issue-types.json':
      '[{"id":"story","name":"Story"}]',
  '/repos/octo/ts449-hosted-shell/contents/TRACK/config/fields.json':
      '[{"id":"summary","name":"Summary"},{"id":"priority","name":"Priority"},{"id":"description","name":"Description","type":"markdown","reserved":true}]',
  '/repos/octo/ts449-hosted-shell/contents/TRACK/config/priorities.json':
      '[{"id":"high","name":"High"}]',
  '/repos/octo/ts449-hosted-shell/contents/TRACK/config/workflows.json':
      '{"default":{"name":"Default Workflow","statuses":["todo","in-progress","done"],"transitions":[{"id":"start","name":"Start progress","from":"todo","to":"in-progress"},{"id":"finish","name":"Complete","from":"in-progress","to":"done"}]}}',
  '/repos/octo/ts449-hosted-shell/contents/TRACK/.trackstate/index/issues.json':
      '[{"key":"TRACK-449","path":"TRACK/TRACK-449/main.md","parent":null,"epic":null,"parentPath":null,"epicPath":null,"summary":"Hosted shell issue stays visible","issueType":"story","status":"in-progress","priority":"high","assignee":"qa-user","labels":["hosted-shell"],"updated":"2026-05-12T06:00:00Z","children":[],"archived":false}]',
  '/repos/octo/ts449-hosted-shell/contents/TRACK/TRACK-449/main.md':
      '---\nkey: TRACK-449\nproject: TRACK\nissueType: story\nstatus: in-progress\npriority: high\nsummary: Hosted shell issue stays visible\nassignee: qa-user\nreporter: qa-user\nlabels:\n  - hosted-shell\nupdated: 2026-05-12T06:00:00Z\n---\n\n# Description\n\nHosted shell hydration should keep this issue visible after the delayed search completes.\n',
};

class Ts449DelayedInitialSearchRepository
    implements TrackStateRepository, ProjectSettingsRepository {
  Ts449DelayedInitialSearchRepository(
    this._delegate, {
    required this.initialSearchDelay,
  });

  final TrackStateRepository _delegate;
  final Duration initialSearchDelay;

  int searchPageCalls = 0;
  bool initialSearchStarted = false;
  bool initialSearchCompleted = false;
  Object? lastSearchError;

  @override
  bool get supportsGitHubAuth => _delegate.supportsGitHubAuth;

  @override
  bool get usesLocalPersistence => _delegate.usesLocalPersistence;

  @override
  Future<TrackerSnapshot> loadSnapshot() => _delegate.loadSnapshot();

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    searchPageCalls += 1;
    if (!initialSearchStarted) {
      initialSearchStarted = true;
      await Future<void>.delayed(initialSearchDelay);
    }
    try {
      final page = await _delegate.searchIssuePage(
        jql,
        startAt: startAt,
        maxResults: maxResults,
        continuationToken: continuationToken,
      );
      initialSearchCompleted = true;
      return page;
    } on Object catch (error) {
      lastSearchError = error;
      rethrow;
    }
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) =>
      _delegate.searchIssues(jql);

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      _delegate.connect(connection);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) =>
      _delegate.archiveIssue(issue);

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) =>
      _delegate.deleteIssue(issue);

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) => _delegate.createIssue(
    summary: summary,
    description: description,
    customFields: customFields,
  );

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) => _delegate.updateIssueDescription(issue, description);

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) => _delegate.updateIssueStatus(issue, status);

  @override
  Future<TrackStateIssue> addIssueComment(TrackStateIssue issue, String body) =>
      _delegate.addIssueComment(issue, body);

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) => _delegate.uploadIssueAttachment(issue: issue, name: name, bytes: bytes);

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) =>
      _delegate.downloadAttachment(attachment);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) =>
      _delegate.loadIssueHistory(issue);

  @override
  Future<TrackerSnapshot> saveProjectSettings(ProjectSettingsCatalog settings) {
    if (_delegate case final ProjectSettingsRepository settingsRepository) {
      return settingsRepository.saveProjectSettings(settings);
    }
    throw StateError(
      'TS-449 delayed search repository does not support project settings.',
    );
  }
}
