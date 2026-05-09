import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class ReactiveIssueDetailTrackStateRepository
    extends ProviderBackedTrackStateRepository {
  ReactiveIssueDetailTrackStateRepository._(this._provider)
    : super(provider: _provider);

  factory ReactiveIssueDetailTrackStateRepository() =>
      ReactiveIssueDetailTrackStateRepository._(
        MutableIssueDetailTrackStateProvider(),
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
    updateProviderSession(
      connectionState: ProviderConnectionState.connected,
      resolvedUserIdentity: currentSession.resolvedUserIdentity,
      permission: readOnlyPermission,
    );
  }
}

class MutableIssueDetailTrackStateProvider
    implements TrackStateProviderAdapter {
  MutableIssueDetailTrackStateProvider()
    : _permission = const RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: true,
        canCheckCollaborators: false,
      );

  RepositoryPermission _permission;

  static const String _revision = 'reactive-read-only-test-revision';

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
      'Attachment access is not required for the TS-104 widget test.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
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
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-104 should not attempt to write issue files while verifying capability sync.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-104 should not attempt to write attachments while verifying capability sync.',
    );
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
