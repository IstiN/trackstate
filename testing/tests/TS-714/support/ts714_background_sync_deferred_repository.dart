import 'dart:async';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts714BackgroundSyncDeferredRepository
    extends ProviderBackedTrackStateRepository {
  Ts714BackgroundSyncDeferredRepository._(this._provider)
    : super(provider: _provider);

  factory Ts714BackgroundSyncDeferredRepository() =>
      Ts714BackgroundSyncDeferredRepository._(_Ts714MutableProvider());

  static const String hostedTokenKey =
      'trackstate.githubToken.trackstate.trackstate';
  static const String hostedTokenValue = 'ts714-write-enabled-token';

  static const String issueKey = 'TRACK-12';
  static const String issueSummary = 'Implement Git sync service';
  static const String initialDescription =
      'Read and write tracker files through GitHub Contents API.';
  static const String localDraftDescription =
      'Local draft: keep the editor open while background sync queues the refresh for later.';
  static const String remoteDescription =
      'Remote change: the issue description was updated by an external Git sync.';

  final _Ts714MutableProvider _provider;

  Future<void> emitExternalIssueDescriptionChange() =>
      _provider.emitExternalIssueDescriptionChange();
}

class _Ts714MutableProvider
    implements TrackStateProviderAdapter, RepositoryFileMutator {
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
    '.trackstate/index/issues.json': _issueIndexJson(),
    'TRACK-12/main.md': _issueMarkdown(
      Ts714BackgroundSyncDeferredRepository.initialDescription,
    ),
  };

  bool _awaitedFirstSync = false;
  bool _hasPendingExternalSync = false;
  int _revision = 1;

  Future<void> emitExternalIssueDescriptionChange() async {
    _files['TRACK-12/main.md'] = _issueMarkdown(
      Ts714BackgroundSyncDeferredRepository.remoteDescription,
    );
    _files['.trackstate/index/issues.json'] = _issueIndexJson(
      updated: 'just now',
    );
    _revision += 1;
    _hasPendingExternalSync = true;
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

    return RepositorySyncCheck(
      state: _syncState(),
      signals: _hasPendingExternalSync
          ? const <WorkspaceSyncSignal>{WorkspaceSyncSignal.hostedRepository}
          : const <WorkspaceSyncSignal>{},
      changedPaths: _hasPendingExternalSync
          ? const <String>{'.trackstate/index/issues.json', 'TRACK-12/main.md'}
          : const <String>{},
    )..let((_) {
      _hasPendingExternalSync = false;
    });
  }

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'ts714-writer', displayName: 'TS-714 Writer');

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
      'TS-714 does not exercise attachment reads.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-714 fixture for $path.');
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
      'TS-714 does not create standalone commits.',
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    _files[request.path] = request.content;
    _revision += 1;
    return RepositoryWriteResult(
      path: request.path,
      branch: request.branch,
      revision: _currentRevision,
    );
  }

  @override
  Future<RepositoryCommitResult> applyFileChanges(
    RepositoryFileChangeRequest request,
  ) async {
    for (final change in request.changes) {
      switch (change) {
        case RepositoryTextFileChange():
          _files[change.path] = change.content;
        case RepositoryDeleteFileChange():
          _files.remove(change.path);
        case RepositoryBinaryFileChange():
          throw const TrackStateProviderException(
            'TS-714 does not exercise binary issue mutations.',
          );
      }
    }
    _revision += 1;
    return RepositoryCommitResult(
      branch: request.branch,
      message: request.message,
      revision: _currentRevision,
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-714 does not exercise attachment writes.',
    );
  }

  RepositorySyncState _syncState() {
    return RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: _currentRevision,
      sessionRevision: 'ts714-write-enabled',
      connectionState: ProviderConnectionState.connected,
      permission: _permission,
    );
  }

  String get _currentRevision => 'ts714-revision-$_revision';
}

String _issueIndexJson({String updated = '5 minutes ago'}) =>
    '''
[
  {
    "key": "${Ts714BackgroundSyncDeferredRepository.issueKey}",
    "path": "${Ts714BackgroundSyncDeferredRepository.issueKey}/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "${Ts714BackgroundSyncDeferredRepository.issueSummary}",
    "issueType": "story",
    "status": "in-progress",
    "priority": "high",
    "assignee": "Denis",
    "labels": ["sync"],
    "updated": "$updated",
    "children": [],
    "archived": false
  }
]
''';

String _issueMarkdown(String description) =>
    '''
---
key: ${Ts714BackgroundSyncDeferredRepository.issueKey}
project: TRACK
issueType: Story
status: In Progress
priority: High
summary: ${Ts714BackgroundSyncDeferredRepository.issueSummary}
assignee: Denis
reporter: Ana
labels:
  - sync
updated: 5 minutes ago
---

# Description
$description
''';

extension<T> on T {
  T let(void Function(T value) update) {
    update(this);
    return this;
  }
}
