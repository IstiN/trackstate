import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../domain/models/trackstate_models.dart';

abstract interface class TrackStateRepository {
  Future<TrackerSnapshot> loadSnapshot();
  Future<List<TrackStateIssue>> searchIssues(String jql);
  Future<GitHubUser> connect(GitHubConnection connection);
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  );
}

class SetupTrackStateRepository implements TrackStateRepository {
  SetupTrackStateRepository({http.Client? client}) : _client = client;

  final http.Client? _client;
  TrackerSnapshot? _snapshot;
  GitHubConnection? _connection;

  static const repositoryName = String.fromEnvironment(
    'TRACKSTATE_REPOSITORY',
    defaultValue: 'trackstate/trackstate',
  );
  static const sourceRef = String.fromEnvironment(
    'TRACKSTATE_SOURCE_REF',
    defaultValue: 'main',
  );

  http.Client get _http => _client ?? http.Client();

  @override
  Future<GitHubUser> connect(GitHubConnection connection) async {
    final repoResponse = await _http.get(
      _githubUri('/repos/${connection.repository}'),
      headers: _githubHeaders(connection.token),
    );
    if (repoResponse.statusCode != 200) {
      throw TrackStateRepositoryException(
        'GitHub connection failed (${repoResponse.statusCode}): ${repoResponse.body}',
      );
    }
    final userJson =
        await _getGitHubJson('/user', token: connection.token)
            as Map<String, Object?>;
    _connection = connection;
    return GitHubUser(
      login: userJson['login']?.toString() ?? 'github',
      displayName: userJson['name']?.toString() ?? '',
    );
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final snapshot = await _loadSetupSnapshot();
    _snapshot = snapshot;
    return snapshot;
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async {
    final snapshot = _snapshot ?? await loadSnapshot();
    return _filterIssues(snapshot.issues, jql);
  }

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot be saved.',
      );
    }
    final connection = _connection;
    if (connection == null) {
      throw const TrackStateRepositoryException(
        'Connect a GitHub token with repository Contents write access first.',
      );
    }

    final path = issue.storagePath;
    final getUri = Uri.https(
      'api.github.com',
      '/repos/${connection.repository}/contents/$path',
      {'ref': connection.branch},
    );
    final getResponse = await _http.get(
      getUri,
      headers: _githubHeaders(connection.token),
    );
    if (getResponse.statusCode != 200) {
      throw TrackStateRepositoryException(
        'Could not read $path (${getResponse.statusCode}): ${getResponse.body}',
      );
    }

    final fileJson = jsonDecode(getResponse.body) as Map<String, Object?>;
    final sha = fileJson['sha'] as String?;
    final encoded = (fileJson['content'] as String?)?.replaceAll('\n', '');
    if (sha == null || encoded == null) {
      throw TrackStateRepositoryException(
        'GitHub response for $path is missing sha/content.',
      );
    }

    final markdown = utf8.decode(base64Decode(encoded));
    final updatedMarkdown = _replaceFrontmatterValue(
      markdown,
      'status',
      status.label,
    );
    final putResponse = await _http.put(
      Uri.https(
        'api.github.com',
        '/repos/${connection.repository}/contents/$path',
      ),
      headers: {
        ..._githubHeaders(connection.token),
        'content-type': 'application/json; charset=utf-8',
      },
      body: jsonEncode({
        'message': 'Move ${issue.key} to ${status.label}',
        'content': base64Encode(utf8.encode(updatedMarkdown)),
        'sha': sha,
        'branch': connection.branch,
      }),
    );
    if (putResponse.statusCode != 200 && putResponse.statusCode != 201) {
      throw TrackStateRepositoryException(
        'Could not save $path (${putResponse.statusCode}): ${putResponse.body}',
      );
    }

    final updatedIssue = issue.copyWith(
      status: status,
      rawMarkdown: updatedMarkdown,
      updatedLabel: 'just now',
    );
    _replaceCachedIssue(updatedIssue);
    return updatedIssue;
  }

  Future<TrackerSnapshot> _loadSetupSnapshot() async {
    final tree = await _loadRepositoryTree();
    final paths = tree.map((entry) => entry.path).toSet();
    final projectPath = paths.firstWhere(
      (path) => path.endsWith('/project.json') || path == 'project.json',
      orElse: () => throw const TrackStateRepositoryException(
        'project.json was not found in the repository.',
      ),
    );
    final dataRoot = projectPath.contains('/')
        ? projectPath.substring(0, projectPath.lastIndexOf('/'))
        : '';
    final configRoot = dataRoot.isEmpty ? 'config' : '$dataRoot/config';
    final projectJson =
        await _getRepositoryJson(projectPath) as Map<String, Object?>;
    final issuePaths =
        tree
            .where(
              (entry) =>
                  entry.type == 'blob' &&
                  entry.path.startsWith(dataRoot.isEmpty ? '' : '$dataRoot/') &&
                  entry.path.endsWith('/main.md'),
            )
            .map((entry) => entry.path)
            .toList()
          ..sort();
    if (issuePaths.isEmpty) {
      throw TrackStateRepositoryException(
        'No issue markdown files were found under ${dataRoot.isEmpty ? 'repository root' : dataRoot}.',
      );
    }

    final statuses = await _getNamedConfig('$configRoot/statuses.json');
    final issueTypes = await _getNamedConfig('$configRoot/issue-types.json');
    final fields = await _getNamedConfig('$configRoot/fields.json');

    final issues = <TrackStateIssue>[];
    for (final path in issuePaths) {
      final markdown = await _getRepositoryText(path);
      final acceptancePath = path.replaceAll(
        '/main.md',
        '/acceptance_criteria.md',
      );
      final acceptance = paths.contains(acceptancePath)
          ? await _getRepositoryText(acceptancePath)
          : null;
      issues.add(_parseIssue(path, markdown, acceptance));
    }
    issues.sort((a, b) => a.key.compareTo(b.key));

    final project = ProjectConfig(
      key: (projectJson['key'] as String?) ?? 'DEMO',
      name: (projectJson['name'] as String?) ?? 'TrackState Project',
      repository: repositoryName,
      branch: sourceRef,
      issueTypes: issueTypes,
      statuses: statuses,
      fields: fields,
    );
    return TrackerSnapshot(project: project, issues: issues);
  }

  Future<List<_GitTreeEntry>> _loadRepositoryTree() async {
    final json =
        await _getGitHubJson(
              '/repos/$repositoryName/git/trees/$sourceRef',
              queryParameters: {'recursive': '1'},
            )
            as Map<String, Object?>;
    final tree = json['tree'];
    if (tree is! List) {
      throw const TrackStateRepositoryException(
        'GitHub tree response did not contain a file list.',
      );
    }
    return tree
        .whereType<Map<String, Object?>>()
        .map(_GitTreeEntry.fromJson)
        .toList();
  }

  Future<Object?> _getRepositoryJson(String path) async =>
      jsonDecode(await _getRepositoryText(path));

  Future<List<String>> _getNamedConfig(String path) async {
    final json = await _getRepositoryJson(path);
    if (json is List) {
      return json
          .map(
            (entry) =>
                entry is Map ? entry['name']?.toString() : entry.toString(),
          )
          .whereType<String>()
          .toList();
    }
    return const [];
  }

  Future<String> _getRepositoryText(String path) async {
    final json =
        await _getGitHubJson(
              '/repos/$repositoryName/contents/$path',
              queryParameters: {'ref': sourceRef},
            )
            as Map<String, Object?>;
    final encoded = json['content']?.toString().replaceAll('\n', '');
    if (encoded == null || encoded.isEmpty) {
      throw TrackStateRepositoryException(
        'GitHub content response for $path did not contain file content.',
      );
    }
    return utf8.decode(base64Decode(encoded));
  }

  Future<Object?> _getGitHubJson(
    String path, {
    Map<String, String>? queryParameters,
    String? token,
  }) async {
    final response = await _http.get(
      _githubUri(path, queryParameters),
      headers: _githubHeaders(token ?? _connection?.token),
    );
    if (response.statusCode != 200) {
      throw TrackStateRepositoryException(
        'GitHub API request failed for $path (${response.statusCode}): ${response.body}',
      );
    }
    return jsonDecode(response.body);
  }

  void _replaceCachedIssue(TrackStateIssue updatedIssue) {
    final snapshot = _snapshot;
    if (snapshot == null) return;
    _snapshot = TrackerSnapshot(
      project: snapshot.project,
      issues: [
        for (final issue in snapshot.issues)
          if (issue.key == updatedIssue.key) updatedIssue else issue,
      ],
    );
  }
}

class DemoTrackStateRepository implements TrackStateRepository {
  const DemoTrackStateRepository();

  @override
  Future<GitHubUser> connect(GitHubConnection connection) async =>
      const GitHubUser(login: 'demo-user', displayName: 'Demo User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _snapshot;

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      _filterIssues(_snapshot.issues, jql);

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, updatedLabel: 'just now');
}

class TrackStateRepositoryException implements Exception {
  const TrackStateRepositoryException(this.message);
  final String message;

  @override
  String toString() => message;
}

TrackStateIssue _parseIssue(
  String storagePath,
  String markdown,
  String? acceptanceMarkdown,
) {
  final frontmatter = _frontmatter(markdown);
  final body = markdown.split('---').skip(2).join('---').trim();
  final description = _section(
    body,
    'Description',
  ).ifEmpty(_section(body, 'Summary'));
  final acceptance = acceptanceMarkdown == null
      ? const <String>[]
      : LineSplitter.split(acceptanceMarkdown)
            .where((line) => line.trimLeft().startsWith('- '))
            .map((line) => line.trimLeft().substring(2).trim())
            .toList();

  return TrackStateIssue(
    key: frontmatter['key'] ?? 'UNKNOWN-0',
    project: frontmatter['project'] ?? 'DEMO',
    issueType: _issueType(frontmatter['issueType']),
    status: _issueStatus(frontmatter['status']),
    priority: _issuePriority(frontmatter['priority']),
    summary: frontmatter['summary'] ?? 'Untitled issue',
    description: description.ifEmpty(body),
    assignee: frontmatter['assignee'] ?? 'unassigned',
    reporter: frontmatter['reporter'] ?? 'unknown',
    labels: _listValue(frontmatter, 'labels'),
    components: _listValue(frontmatter, 'components'),
    parentKey: _nullable(frontmatter['parent']),
    epicKey: _nullable(frontmatter['epic']),
    progress: _issueStatus(frontmatter['status']) == IssueStatus.done ? 1 : .35,
    updatedLabel: frontmatter['updated'] ?? 'from repo',
    acceptanceCriteria: acceptance,
    comments: const [],
    storagePath: storagePath,
    rawMarkdown: markdown,
  );
}

Map<String, String> _frontmatter(String markdown) {
  final lines = const LineSplitter().convert(markdown);
  if (lines.isEmpty || lines.first.trim() != '---') return const {};
  final result = <String, String>{};
  String? listKey;
  for (final line in lines.skip(1)) {
    if (line.trim() == '---') break;
    final listItem = RegExp(r'^\s*-\s+(.+)$').firstMatch(line);
    if (listKey != null && listItem != null) {
      result[listKey] = [
        if (result[listKey]?.isNotEmpty ?? false) result[listKey]!,
        listItem.group(1)!.trim(),
      ].join('|');
      continue;
    }
    final match = RegExp(r'^([A-Za-z0-9_-]+):\s*(.*)$').firstMatch(line);
    if (match == null) continue;
    final key = match.group(1)!;
    final value = match.group(2)!.trim();
    result[key] = value;
    listKey = value.isEmpty ? key : null;
  }
  return result;
}

List<String> _listValue(Map<String, String> frontmatter, String key) =>
    (frontmatter[key] ?? '')
        .split('|')
        .map((value) => value.trim())
        .where((value) => value.isNotEmpty)
        .toList();

String? _nullable(String? value) =>
    value == null || value == 'null' || value.isEmpty ? null : value;

String _section(String markdown, String title) {
  final match = RegExp(
    '^# $title\\s*\\n([\\s\\S]*?)(?=\\n# |\\z)',
    multiLine: true,
  ).firstMatch(markdown);
  return match?.group(1)?.trim() ?? '';
}

String _replaceFrontmatterValue(String markdown, String key, String value) {
  final pattern = RegExp('^$key:\\s*.*\$', multiLine: true);
  if (pattern.hasMatch(markdown)) {
    return markdown.replaceFirst(pattern, '$key: $value');
  }
  return markdown.replaceFirst('---\n', '---\n$key: $value\n');
}

IssueType _issueType(String? value) => switch ((value ?? '').toLowerCase()) {
  'epic' => IssueType.epic,
  'sub-task' || 'subtask' => IssueType.subtask,
  'bug' => IssueType.bug,
  'task' => IssueType.task,
  _ => IssueType.story,
};

IssueStatus _issueStatus(String? value) =>
    switch ((value ?? '').toLowerCase()) {
      'in progress' || 'in-progress' => IssueStatus.inProgress,
      'in review' || 'in-review' => IssueStatus.inReview,
      'done' => IssueStatus.done,
      _ => IssueStatus.todo,
    };

IssuePriority _issuePriority(String? value) =>
    switch ((value ?? '').toLowerCase()) {
      'highest' => IssuePriority.highest,
      'high' => IssuePriority.high,
      'low' => IssuePriority.low,
      _ => IssuePriority.medium,
    };

List<TrackStateIssue> _filterIssues(List<TrackStateIssue> issues, String jql) {
  final query = jql.trim().toLowerCase();
  if (query.isEmpty) return issues;

  Iterable<TrackStateIssue> results = issues;
  if (query.contains('status != done')) {
    results = results.where((issue) => issue.status != IssueStatus.done);
  }
  if (query.contains('status = done')) {
    results = results.where((issue) => issue.status == IssueStatus.done);
  }
  if (query.contains('issuetype = story') ||
      query.contains('issuetype = "story"')) {
    results = results.where((issue) => issue.issueType == IssueType.story);
  }
  final keyMatch = RegExp(
    r'(?:epic|parent)\s*=\s*([a-z]+-\d+)',
  ).firstMatch(query);
  if (keyMatch != null) {
    final key = keyMatch.group(1)!.toUpperCase();
    results = results.where(
      (issue) => issue.epicKey == key || issue.parentKey == key,
    );
  }
  final freeText = query
      .replaceAll(RegExp(r'project\s*=\s*[a-z]+'), '')
      .replaceAll(RegExp(r'status\s*(!=|=)\s*[a-z ]+'), '')
      .replaceAll(RegExp(r'issuetype\s*=\s*"?[a-z -]+"?'), '')
      .replaceAll(RegExp(r'(?:epic|parent)\s*=\s*[a-z]+-\d+'), '')
      .replaceAll(RegExp(r'order\s+by.+$'), '')
      .replaceAll(RegExp(r'\b(and|or)\b'), '')
      .trim();
  if (freeText.isNotEmpty && !freeText.contains('=')) {
    results = results.where(
      (issue) =>
          issue.summary.toLowerCase().contains(freeText) ||
          issue.key.toLowerCase().contains(freeText),
    );
  }
  final sorted = results.toList()
    ..sort(
      (a, b) => _priorityRank(b.priority).compareTo(_priorityRank(a.priority)),
    );
  return sorted;
}

Map<String, String> _githubHeaders(String? token) => {
  'accept': 'application/vnd.github+json',
  'X-GitHub-Api-Version': '2022-11-28',
  if (token != null && token.isNotEmpty) 'authorization': 'Bearer $token',
};

Uri _githubUri(String path, [Map<String, String>? queryParameters]) =>
    Uri.https('api.github.com', path, queryParameters);

class _GitTreeEntry {
  const _GitTreeEntry({required this.path, required this.type});

  factory _GitTreeEntry.fromJson(Map<String, Object?> json) => _GitTreeEntry(
    path: json['path']?.toString() ?? '',
    type: json['type']?.toString() ?? '',
  );

  final String path;
  final String type;
}

int _priorityRank(IssuePriority priority) => switch (priority) {
  IssuePriority.highest => 4,
  IssuePriority.high => 3,
  IssuePriority.medium => 2,
  IssuePriority.low => 1,
};

extension on String {
  String ifEmpty(String fallback) => isEmpty ? fallback : this;
}

const _project = ProjectConfig(
  key: 'TRACK',
  name: 'TrackState.AI',
  repository: SetupTrackStateRepository.repositoryName,
  branch: SetupTrackStateRepository.sourceRef,
  issueTypes: ['Epic', 'Story', 'Task', 'Sub-task', 'Bug'],
  statuses: ['To Do', 'In Progress', 'In Review', 'Done'],
  fields: [
    'Summary',
    'Description',
    'Acceptance Criteria',
    'Priority',
    'Assignee',
  ],
);

const _snapshot = TrackerSnapshot(
  project: _project,
  issues: [
    TrackStateIssue(
      key: 'TRACK-1',
      project: 'TRACK',
      issueType: IssueType.epic,
      status: IssueStatus.inProgress,
      priority: IssuePriority.highest,
      summary: 'Platform Foundation',
      description: 'Bootstrap the Git-native tracker.',
      assignee: 'Ana',
      reporter: 'Uladzimir',
      labels: ['mvp', 'git-native'],
      components: ['tracker-core'],
      parentKey: null,
      epicKey: null,
      progress: .62,
      updatedLabel: '2 minutes ago',
      acceptanceCriteria: ['Issue metadata follows canonical frontmatter.'],
      comments: [],
    ),
    TrackStateIssue(
      key: 'TRACK-12',
      project: 'TRACK',
      issueType: IssueType.story,
      status: IssueStatus.inProgress,
      priority: IssuePriority.high,
      summary: 'Implement Git sync service',
      description: 'Read and write tracker files through GitHub Contents API.',
      assignee: 'Denis',
      reporter: 'Ana',
      labels: ['sync'],
      components: ['storage'],
      parentKey: null,
      epicKey: 'TRACK-1',
      progress: .44,
      updatedLabel: '5 minutes ago',
      acceptanceCriteria: ['Push issue updates as commits.'],
      comments: [],
    ),
    TrackStateIssue(
      key: 'TRACK-34',
      project: 'TRACK',
      issueType: IssueType.epic,
      status: IssueStatus.inProgress,
      priority: IssuePriority.medium,
      summary: 'Mobile Experience',
      description: 'Deliver responsive layouts and touch optimized screens.',
      assignee: 'Noah',
      reporter: 'Ana',
      labels: ['mobile'],
      components: ['ui'],
      parentKey: null,
      epicKey: null,
      progress: .52,
      updatedLabel: 'Jun 18',
      acceptanceCriteria: ['Layouts adapt without overflow.'],
      comments: [],
    ),
    TrackStateIssue(
      key: 'TRACK-41',
      project: 'TRACK',
      issueType: IssueType.story,
      status: IssueStatus.todo,
      priority: IssuePriority.medium,
      summary: 'Polish mobile board interactions',
      description: 'Make drag and drop work on touch devices.',
      assignee: 'Noah',
      reporter: 'Ana',
      labels: ['mobile', 'board'],
      components: ['ui'],
      parentKey: null,
      epicKey: 'TRACK-34',
      progress: .12,
      updatedLabel: 'Jun 19',
      acceptanceCriteria: ['Cards can be moved between columns.'],
      comments: [],
    ),
    TrackStateIssue(
      key: 'TRACK-50',
      project: 'TRACK',
      issueType: IssueType.task,
      status: IssueStatus.done,
      priority: IssuePriority.low,
      summary: 'Create CI pipeline',
      description: 'Analyze, test, build, and deploy Pages artifacts.',
      assignee: 'Priya',
      reporter: 'Ana',
      labels: ['ci'],
      components: ['quality'],
      parentKey: null,
      epicKey: 'TRACK-1',
      progress: 1,
      updatedLabel: 'Jun 20',
      acceptanceCriteria: ['Workflow uploads web artifact.'],
      comments: [],
    ),
  ],
);
