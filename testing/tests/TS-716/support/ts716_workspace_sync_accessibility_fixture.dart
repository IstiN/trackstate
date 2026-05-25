import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts716WorkspaceSyncAccessibilityRepository
    extends ProviderBackedTrackStateRepository {
  Ts716WorkspaceSyncAccessibilityRepository._(this._provider)
    : super(provider: _provider);

  factory Ts716WorkspaceSyncAccessibilityRepository() =>
      Ts716WorkspaceSyncAccessibilityRepository._(_Ts716ReadOnlyProvider());

  static const String hostedTokenKey =
      'trackstate.githubToken.trackstate.trackstate';
  static const String hostedTokenValue = 'ts716-read-only-token';
  static const String topBarStatusLabel = 'Attention needed';
  static const String syncError =
      'Hosted workspace sync could not refresh the latest repository snapshot.';
  static const String syncErrorMessage =
      'The latest sync check failed: $syncError';
  static const String retryLabel = 'Retry';
  static const String reconnectLabel = 'Reconnect for write access';
  static const String readOnlyLabel = 'Read-only';
  static const String workspaceSyncSectionLabel = 'Workspace sync';
  static const String repositoryAccessSectionLabel = 'Repository access';

  final _Ts716ReadOnlyProvider _provider;
  int _loadSnapshotCalls = 0;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    _loadSnapshotCalls += 1;
    if (_loadSnapshotCalls >= 2) {
      throw const TrackStateProviderException(syncError);
    }
    return await super.loadSnapshot();
  }
}

class _Ts716ReadOnlyProvider implements TrackStateProviderAdapter {
  static const RepositoryPermission _permission = RepositoryPermission(
    canRead: true,
    canWrite: false,
    isAdmin: false,
    canCreateBranch: false,
    canManageAttachments: false,
    canCheckCollaborators: false,
  );

  static const String _revision = 'ts716-workspace-sync-accessibility';

  static const Map<String, String> _files = {
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
    '.trackstate/index/issues.json': '''
[
  {
    "key": "TRACK-11",
    "path": "TRACK-11/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "Stabilize dashboard polling",
    "issueType": "story",
    "status": "todo",
    "priority": "highest",
    "assignee": "Denis",
    "labels": ["dashboard"],
    "updated": "2 minutes ago",
    "children": [],
    "archived": false
  },
  {
    "key": "TRACK-12",
    "path": "TRACK-12/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "Implement Git sync service",
    "issueType": "story",
    "status": "in-progress",
    "priority": "high",
    "assignee": "Denis",
    "labels": ["sync"],
    "updated": "5 minutes ago",
    "children": [],
    "archived": false
  }
]
''',
    'TRACK-11/main.md': '''
---
key: TRACK-11
project: TRACK
issueType: Story
status: To Do
priority: Highest
summary: Stabilize dashboard polling
assignee: Denis
reporter: Ana
labels:
  - dashboard
updated: 2 minutes ago
---

# Description
Keep the dashboard responsive when background refreshes are running.
''',
    'TRACK-12/main.md': '''
---
key: TRACK-12
project: TRACK
issueType: Story
status: In Progress
priority: High
summary: Implement Git sync service
assignee: Denis
reporter: Ana
labels:
  - sync
updated: 5 minutes ago
---

# Description
Read and write tracker files through GitHub Contents API.
''',
  };

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => const RepositorySyncCheck(
    state: RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: _revision,
      sessionRevision: 'ts716-read-only',
      connectionState: ProviderConnectionState.connected,
      permission: _permission,
    ),
    signals: <WorkspaceSyncSignal>{WorkspaceSyncSignal.hostedRepository},
    changedPaths: <String>{'.trackstate/index/issues.json'},
  );

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(
        login: 'read-only-user',
        displayName: 'Read Only User',
      );

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
      'TS-716 does not require attachment access.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-716 fixture for $path.');
    }
    return RepositoryTextFile(
      path: path,
      content: content,
      revision: _revision,
    );
  }

  @override
  Future<String> resolveWriteBranch() async => dataRef;

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-716 should not attempt to create commits in a read-only session.',
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-716 should not attempt to write text files in a read-only session.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-716 should not attempt to write attachments in a read-only session.',
    );
  }
}
