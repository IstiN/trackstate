import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts736SearchQueryFallbackRepository
    extends ProviderBackedTrackStateRepository {
  Ts736SearchQueryFallbackRepository._(this._provider)
    : super(provider: _provider);

  factory Ts736SearchQueryFallbackRepository() =>
      Ts736SearchQueryFallbackRepository._(_Ts736MutableProvider());

  static const String issueKey = 'TRACK-736';
  static const String issueSummary = 'Urgent customer escalation';
  static const String issueDescription =
      'Coordinate the production fix for the urgent customer escalation.';
  static const String unaffectedIssueKey = 'TRACK-737';
  static const String unaffectedIssueSummary = 'Routine backlog cleanup';
  static const String query = 'labels = urgent';
  static const String noResultsText = 'No issues match this query';

  final _Ts736MutableProvider _provider;

  Future<void> emitUrgentLabelRemovalSync() =>
      _provider.emitUrgentLabelRemovalSync();

  int get syncCheckCount => _provider.syncCheckCount;

  String get currentRevision => _provider.currentRevision;
}

class _Ts736MutableProvider implements TrackStateProviderAdapter {
  static const RepositoryPermission _permission = RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: false,
    canCreateBranch: true,
    canManageAttachments: true,
    canCheckCollaborators: false,
  );

  final Map<String, String> _files = <String, String>{
    'project.json': '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config"
}
''',
    'config/statuses.json': '''
[
  {"id": "todo", "name": "To Do", "category": "new"},
  {"id": "in-progress", "name": "In Progress", "category": "indeterminate"},
  {"id": "in-review", "name": "In Review", "category": "indeterminate"},
  {"id": "done", "name": "Done", "category": "done"}
]
''',
    'config/issue-types.json': '''
[
  {"id": "epic", "name": "Epic", "hierarchyLevel": 1, "icon": "epic"},
  {"id": "story", "name": "Story", "hierarchyLevel": 0, "icon": "story"},
  {"id": "task", "name": "Task", "hierarchyLevel": 0, "icon": "task"},
  {"id": "subtask", "name": "Sub-task", "hierarchyLevel": -1, "icon": "subtask"},
  {"id": "bug", "name": "Bug", "hierarchyLevel": 0, "icon": "bug"}
]
''',
    'config/fields.json': '''
[
  {"id": "summary", "name": "Summary", "type": "string", "required": true},
  {"id": "description", "name": "Description", "type": "markdown", "required": false},
  {"id": "acceptanceCriteria", "name": "Acceptance Criteria", "type": "markdown", "required": false},
  {"id": "priority", "name": "Priority", "type": "option", "required": false},
  {"id": "assignee", "name": "Assignee", "type": "user", "required": false},
  {"id": "labels", "name": "Labels", "type": "array", "required": false}
]
''',
    'config/priorities.json': '''
[
  {"id": "highest", "name": "Highest"},
  {"id": "high", "name": "High"},
  {"id": "medium", "name": "Medium"}
]
''',
    'config/workflows.json': '''
{
  "default": {
    "name": "Default Workflow",
    "statuses": ["todo", "in-progress", "in-review", "done"],
    "transitions": [
      {"id": "start", "name": "Start", "from": "todo", "to": "in-progress"},
      {"id": "review", "name": "Review", "from": "in-progress", "to": "in-review"},
      {"id": "finish", "name": "Finish", "from": "in-review", "to": "done"}
    ]
  }
}
''',
    '.trackstate/index/issues.json': _issueIndexJson(
      urgentLabels: const <String>['urgent', 'support'],
    ),
    'TRACK-736/main.md': _issueMarkdown(
      key: Ts736SearchQueryFallbackRepository.issueKey,
      summary: Ts736SearchQueryFallbackRepository.issueSummary,
      description: Ts736SearchQueryFallbackRepository.issueDescription,
      labels: const <String>['urgent', 'support'],
      updated: '2 minutes ago',
      priority: 'High',
      status: 'To Do',
    ),
    'TRACK-737/main.md': _issueMarkdown(
      key: Ts736SearchQueryFallbackRepository.unaffectedIssueKey,
      summary: Ts736SearchQueryFallbackRepository.unaffectedIssueSummary,
      description: 'Close routine cleanup items without urgent impact.',
      labels: const <String>['backlog'],
      updated: '5 minutes ago',
      priority: 'Medium',
      status: 'In Progress',
    ),
  };

  bool _hasPendingExternalSync = false;
  int _revision = 1;
  int _syncCheckCount = 0;

  Future<void> emitUrgentLabelRemovalSync() async {
    _files['.trackstate/index/issues.json'] = _issueIndexJson(
      urgentLabels: const <String>['support'],
      urgentUpdated: 'just now',
    );
    _files['TRACK-736/main.md'] = _issueMarkdown(
      key: Ts736SearchQueryFallbackRepository.issueKey,
      summary: Ts736SearchQueryFallbackRepository.issueSummary,
      description: Ts736SearchQueryFallbackRepository.issueDescription,
      labels: const <String>['support'],
      updated: 'just now',
      priority: 'High',
      status: 'To Do',
    );
    _revision += 1;
    _hasPendingExternalSync = true;
  }

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    _syncCheckCount += 1;

    final hasPendingExternalSync = _hasPendingExternalSync;
    _hasPendingExternalSync = false;

    return RepositorySyncCheck(
      state: _syncState(),
      signals: hasPendingExternalSync
          ? const <WorkspaceSyncSignal>{WorkspaceSyncSignal.hostedRepository}
          : const <WorkspaceSyncSignal>{},
      changedPaths: hasPendingExternalSync
          ? const <String>{'.trackstate/index/issues.json', 'TRACK-736/main.md'}
          : const <String>{},
    );
  }

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'ts736-tester', displayName: 'TS-736 Tester');

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryPermission> getPermission() async => _permission;

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async => [
    for (final path in _files.keys)
      RepositoryTreeEntry(path: path, type: 'blob'),
  ];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    throw const TrackStateProviderException(
      'TS-736 does not require attachment reads.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-736 should not write attachments while validating search query fallback.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-736 fixture for $path.');
    }
    return RepositoryTextFile(
      path: path,
      content: content,
      revision: _currentRevision,
    );
  }

  @override
  Future<String> resolveWriteBranch() async => dataRef;

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-736 should not create commits while validating search query fallback.',
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-736 should not write repository files while validating search query fallback.',
    );
  }

  RepositorySyncState _syncState() {
    return RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: _currentRevision,
      sessionRevision: 'ts736-write-enabled',
      connectionState: ProviderConnectionState.connected,
      permission: _permission,
    );
  }

  String get _currentRevision => 'ts736-revision-$_revision';

  int get syncCheckCount => _syncCheckCount;

  String get currentRevision => _currentRevision;
}

String _issueIndexJson({
  required List<String> urgentLabels,
  String urgentUpdated = '2 minutes ago',
}) =>
    '''
[
  {
    "key": "${Ts736SearchQueryFallbackRepository.issueKey}",
    "path": "${Ts736SearchQueryFallbackRepository.issueKey}/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "${Ts736SearchQueryFallbackRepository.issueSummary}",
    "issueType": "story",
    "status": "todo",
    "priority": "high",
    "assignee": "Ana",
    "labels": ${_jsonList(urgentLabels)},
    "updated": "$urgentUpdated",
    "children": [],
    "archived": false
  },
  {
    "key": "${Ts736SearchQueryFallbackRepository.unaffectedIssueKey}",
    "path": "${Ts736SearchQueryFallbackRepository.unaffectedIssueKey}/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "${Ts736SearchQueryFallbackRepository.unaffectedIssueSummary}",
    "issueType": "task",
    "status": "in-progress",
    "priority": "medium",
    "assignee": "Sam",
    "labels": ["backlog"],
    "updated": "5 minutes ago",
    "children": [],
    "archived": false
  }
]
''';

String _issueMarkdown({
  required String key,
  required String summary,
  required String description,
  required List<String> labels,
  required String updated,
  required String priority,
  required String status,
}) =>
    '''
---
key: $key
project: TRACK
issueType: Story
status: $status
priority: $priority
summary: $summary
assignee: Ana
reporter: Casey
labels:
${_yamlList(labels)}
updated: $updated
---

# Description
$description
''';

String _yamlList(List<String> values) {
  return values.map((value) => '  - $value').join('\n');
}

String _jsonList(List<String> values) {
  return '[${values.map((value) => '"$value"').join(', ')}]';
}
