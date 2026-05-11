import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class ReactiveIssueDetailTrackStateRepository
    extends ProviderBackedTrackStateRepository {
  ReactiveIssueDetailTrackStateRepository._(this._provider)
    : super(provider: _provider);

  factory ReactiveIssueDetailTrackStateRepository({
    RepositoryPermission permission = const RepositoryPermission(
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: true,
      canCheckCollaborators: false,
    ),
    Set<String> lfsTrackedPaths = const <String>{},
    Set<String> failingTextPaths = const <String>{},
  }) => ReactiveIssueDetailTrackStateRepository._(
    MutableIssueDetailTrackStateProvider(
      permission: permission,
      lfsTrackedPaths: lfsTrackedPaths,
      failingTextPaths: failingTextPaths,
    ),
  );

  final MutableIssueDetailTrackStateProvider _provider;

  void synchronizeSessionToReadOnly() {
    final currentSession = session;
    if (currentSession == null) {
      throw StateError(
        'Cannot downgrade write access before the provider session is connected.',
      );
    }

    const readOnlyPermission = RepositoryPermission(
      canRead: true,
      canWrite: false,
      isAdmin: false,
      canCreateBranch: false,
      canManageAttachments: false,
      canCheckCollaborators: false,
    );

    _provider.updatePermission(readOnlyPermission);
    currentSession.update(
      providerType: currentSession.providerType,
      connectionState: ProviderConnectionState.connected,
      resolvedUserIdentity: currentSession.resolvedUserIdentity,
      canRead: readOnlyPermission.canRead,
      canWrite: readOnlyPermission.canWrite,
      canCreateBranch: readOnlyPermission.canCreateBranch,
      canManageAttachments: readOnlyPermission.canManageAttachments,
      attachmentUploadMode: readOnlyPermission.attachmentUploadMode,
      canCheckCollaborators: readOnlyPermission.canCheckCollaborators,
    );
  }

  void synchronizeSessionToAttachmentRestricted() {
    final currentSession = session;
    if (currentSession == null) {
      throw StateError(
        'Cannot restrict attachments before the provider session is connected.',
      );
    }

    const attachmentRestrictedPermission = RepositoryPermission(
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: false,
      attachmentUploadMode: AttachmentUploadMode.noLfs,
      canCheckCollaborators: false,
    );

    _provider.updatePermission(attachmentRestrictedPermission);
    currentSession.update(
      providerType: currentSession.providerType,
      connectionState: ProviderConnectionState.connected,
      resolvedUserIdentity: currentSession.resolvedUserIdentity,
      canRead: attachmentRestrictedPermission.canRead,
      canWrite: attachmentRestrictedPermission.canWrite,
      canCreateBranch: attachmentRestrictedPermission.canCreateBranch,
      canManageAttachments: attachmentRestrictedPermission.canManageAttachments,
      attachmentUploadMode: attachmentRestrictedPermission.attachmentUploadMode,
      canCheckCollaborators:
          attachmentRestrictedPermission.canCheckCollaborators,
    );
  }
}

class MutableIssueDetailTrackStateProvider
    implements TrackStateProviderAdapter, RepositoryFileMutator {
  MutableIssueDetailTrackStateProvider({
    RepositoryPermission permission = const RepositoryPermission(
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: true,
      canCheckCollaborators: false,
    ),
    Set<String> lfsTrackedPaths = const <String>{},
    Set<String> failingTextPaths = const <String>{},
  }) : _permission = permission,
       _lfsTrackedPaths = lfsTrackedPaths,
       _failingTextPaths = failingTextPaths;

  RepositoryPermission _permission;
  final Set<String> _lfsTrackedPaths;
  final Set<String> _failingTextPaths;

  static const String _revision = 'reactive-read-only-test-revision';

  static const Map<String, String> _textFixtures = {
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
    'TRACK/config/priorities.json': '''
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
    'TRACK/config/workflows.json': '''
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
components:
  - ui
updated: 2 minutes ago
---

# Description
Keep the dashboard responsive when background refreshes are running.
''',
    'TRACK-11/acceptance_criteria.md': '''
- Dashboard cards stay interactive during refresh.
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
components:
  - storage
updated: 5 minutes ago
---

# Description
Read and write tracker files through GitHub Contents API.
''',
    'TRACK-12/acceptance_criteria.md': '''
- Push issue updates as commits.
''',
  };

  final Map<String, String> _textFiles = Map<String, String>.from(
    _textFixtures,
  );
  final Map<String, Uint8List> _binaryFiles = <String, Uint8List>{
    'TRACK-12/attachments/sync-sequence.svg': Uint8List.fromList(
      '<svg />'.codeUnits,
    ),
  };

  void updatePermission(RepositoryPermission permission) {
    _permission = permission;
  }

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(
        login: 'write-enabled-user',
        displayName: 'Write Enabled User',
      );

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryPermission> getPermission() async => _permission;

  @override
  Future<bool> isLfsTracked(String path) async =>
      _lfsTrackedPaths.contains(path);

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async => [
    for (final path in [..._textFiles.keys, ..._binaryFiles.keys])
      RepositoryTreeEntry(path: path, type: 'blob'),
  ];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    final binary = _binaryFiles[path];
    if (binary != null) {
      return RepositoryAttachment(
        path: path,
        bytes: binary,
        revision: _revision,
        declaredSizeBytes: binary.length,
        lfsOid: _lfsTrackedPaths.contains(path) ? 'reactive-lfs-oid' : null,
      );
    }
    final text = _textFiles[path];
    if (text != null) {
      final bytes = Uint8List.fromList(text.codeUnits);
      return RepositoryAttachment(
        path: path,
        bytes: bytes,
        revision: _revision,
        declaredSizeBytes: bytes.length,
      );
    }
    throw TrackStateProviderException('Missing attachment fixture for $path.');
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    if (_failingTextPaths.contains(path)) {
      throw TrackStateProviderException('Deferred read failed for $path.');
    }
    final content = _textFiles[path];
    if (content == null) {
      throw TrackStateProviderException('Missing fixture for $path.');
    }
    return const RepositoryTextFile(
      path: '',
      content: '',
      revision: _revision,
    ).copyWith(path: path, content: content);
  }

  @override
  Future<String> resolveWriteBranch() async => dataRef;

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-104 should not attempt to create commits while verifying capability sync.',
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    _textFiles[request.path] = request.content;
    return const RepositoryWriteResult(
      path: '',
      branch: '',
      revision: _revision,
    ).copyWith(path: request.path, branch: request.branch);
  }

  @override
  Future<RepositoryCommitResult> applyFileChanges(
    RepositoryFileChangeRequest request,
  ) async {
    for (final change in request.changes) {
      switch (change) {
        case RepositoryTextFileChange():
          _textFiles[change.path] = change.content;
        case RepositoryBinaryFileChange():
          _binaryFiles[change.path] = Uint8List.fromList(change.bytes);
        case RepositoryDeleteFileChange():
          _textFiles.remove(change.path);
          _binaryFiles.remove(change.path);
      }
    }
    return const RepositoryCommitResult(
      branch: '',
      message: '',
      revision: _revision,
    ).copyWith(branch: request.branch, message: request.message);
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    _binaryFiles[request.path] = Uint8List.fromList(request.bytes);
    return const RepositoryAttachmentWriteResult(
      path: '',
      branch: '',
      revision: _revision,
    ).copyWith(path: request.path, branch: request.branch);
  }
}

extension on RepositoryTextFile {
  RepositoryTextFile copyWith({
    String? path,
    String? content,
    String? revision,
  }) {
    return RepositoryTextFile(
      path: path ?? this.path,
      content: content ?? this.content,
      revision: revision ?? this.revision,
    );
  }
}

extension on RepositoryAttachmentWriteResult {
  RepositoryAttachmentWriteResult copyWith({
    String? path,
    String? branch,
    String? revision,
  }) {
    return RepositoryAttachmentWriteResult(
      path: path ?? this.path,
      branch: branch ?? this.branch,
      revision: revision ?? this.revision,
    );
  }
}

extension on RepositoryWriteResult {
  RepositoryWriteResult copyWith({
    String? path,
    String? branch,
    String? revision,
  }) {
    return RepositoryWriteResult(
      path: path ?? this.path,
      branch: branch ?? this.branch,
      revision: revision ?? this.revision,
    );
  }
}

extension on RepositoryCommitResult {
  RepositoryCommitResult copyWith({
    String? branch,
    String? message,
    String? revision,
  }) {
    return RepositoryCommitResult(
      branch: branch ?? this.branch,
      message: message ?? this.message,
      revision: revision ?? this.revision,
    );
  }
}
