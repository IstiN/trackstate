import 'dart:async';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts732RemovedIssueSyncRepository
    extends ProviderBackedTrackStateRepository {
  Ts732RemovedIssueSyncRepository._(this._provider)
    : super(provider: _provider);

  factory Ts732RemovedIssueSyncRepository() =>
      Ts732RemovedIssueSyncRepository._(_Ts732MutableProvider());

  static const String hostedTokenKey =
      'trackstate.githubToken.trackstate.trackstate';
  static const String hostedTokenValue = 'ts732-write-enabled-token';

  static const String removedIssueKey = 'TRACK-12';
  static const String removedIssueSummary = 'Implement Git sync service';
  static const String remainingIssueKey = 'TRACK-11';
  static const String remainingIssueSummary = 'Stabilize dashboard polling';
  static const String removedIssueDescription =
      'Read and write tracker files through GitHub Contents API.';
  static const String remainingIssueDescription =
      'Keep the dashboard responsive when background refreshes are running.';

  final _Ts732MutableProvider _provider;

  Future<void> emitIssueRemovalSync() => _provider.emitIssueRemovalSync();
}

class _Ts732MutableProvider implements TrackStateProviderAdapter {
  static const RepositoryPermission _permission = RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: false,
    canCreateBranch: true,
    canManageAttachments: true,
    canCheckCollaborators: false,
  );

  final Completer<void> _firstSyncGate = Completer<void>();
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
    '.trackstate/index/issues.json': _issueIndexJson(includeRemovedIssue: true),
    '${Ts732RemovedIssueSyncRepository.remainingIssueKey}/main.md':
        _issueMarkdown(
          key: Ts732RemovedIssueSyncRepository.remainingIssueKey,
          summary: Ts732RemovedIssueSyncRepository.remainingIssueSummary,
          status: 'To Do',
          priority: 'Highest',
          updated: '2 minutes ago',
          label: 'dashboard',
          description:
              Ts732RemovedIssueSyncRepository.remainingIssueDescription,
        ),
    '${Ts732RemovedIssueSyncRepository.removedIssueKey}/main.md':
        _issueMarkdown(
          key: Ts732RemovedIssueSyncRepository.removedIssueKey,
          summary: Ts732RemovedIssueSyncRepository.removedIssueSummary,
          status: 'In Progress',
          priority: 'High',
          updated: '5 minutes ago',
          label: 'sync',
          description: Ts732RemovedIssueSyncRepository.removedIssueDescription,
        ),
  };

  bool _awaitedFirstSync = false;
  bool _hasPendingRemovalSync = false;
  int _revision = 1;

  Future<void> emitIssueRemovalSync() async {
    _files.remove('${Ts732RemovedIssueSyncRepository.removedIssueKey}/main.md');
    _files['.trackstate/index/issues.json'] = _issueIndexJson(
      includeRemovedIssue: false,
    );
    _revision += 1;
    _hasPendingRemovalSync = true;
    if (!_firstSyncGate.isCompleted) {
      _firstSyncGate.complete();
    }
  }

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    if (!_awaitedFirstSync) {
      _awaitedFirstSync = true;
      await _firstSyncGate.future;
    }

    final check = RepositorySyncCheck(
      state: _syncState(),
      signals: _hasPendingRemovalSync
          ? const <WorkspaceSyncSignal>{WorkspaceSyncSignal.hostedRepository}
          : const <WorkspaceSyncSignal>{},
      changedPaths: _hasPendingRemovalSync
          ? const <String>{'.trackstate/index/issues.json', 'TRACK-12/main.md'}
          : const <String>{},
    );
    _hasPendingRemovalSync = false;
    return check;
  }

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'ts732-writer', displayName: 'TS-732 Writer');

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
      'TS-732 does not require attachment access.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-732 fixture for $path.');
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
      'TS-732 should not create commits.',
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-732 should not write text files.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-732 should not write attachments.',
    );
  }

  RepositorySyncState _syncState() {
    return RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: _currentRevision,
      sessionRevision: 'ts732-write-enabled',
      connectionState: ProviderConnectionState.connected,
      permission: _permission,
    );
  }

  String get _currentRevision => 'ts732-revision-$_revision';
}

String _issueIndexJson({required bool includeRemovedIssue}) {
  final removedIssueEntry =
      '''
  {
    "key": "${Ts732RemovedIssueSyncRepository.removedIssueKey}",
    "path": "${Ts732RemovedIssueSyncRepository.removedIssueKey}/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "${Ts732RemovedIssueSyncRepository.removedIssueSummary}",
    "issueType": "story",
    "status": "in-progress",
    "priority": "high",
    "assignee": "Denis",
    "labels": ["sync"],
    "updated": "5 minutes ago",
    "children": [],
    "archived": false
  }''';

  return '''
[
  {
    "key": "${Ts732RemovedIssueSyncRepository.remainingIssueKey}",
    "path": "${Ts732RemovedIssueSyncRepository.remainingIssueKey}/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "${Ts732RemovedIssueSyncRepository.remainingIssueSummary}",
    "issueType": "story",
    "status": "todo",
    "priority": "highest",
    "assignee": "Denis",
    "labels": ["dashboard"],
    "updated": "2 minutes ago",
    "children": [],
    "archived": false
  }${includeRemovedIssue ? ',\n$removedIssueEntry' : ''}
]
''';
}

String _issueMarkdown({
  required String key,
  required String summary,
  required String status,
  required String priority,
  required String updated,
  required String label,
  required String description,
}) =>
    '''
---
key: $key
project: TRACK
issueType: Story
status: $status
priority: $priority
summary: $summary
assignee: Denis
reporter: Ana
labels:
  - $label
updated: $updated
---

# Description
$description
''';
