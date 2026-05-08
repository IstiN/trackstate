import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class ReadOnlyTrackStateRepository extends ProviderBackedTrackStateRepository {
  ReadOnlyTrackStateRepository()
    : super(provider: const _IssueDetailTrackStateProvider(canWrite: false));
}

class WritableTrackStateRepository extends ProviderBackedTrackStateRepository {
  WritableTrackStateRepository()
    : super(provider: const _IssueDetailTrackStateProvider(canWrite: true));
}

class _IssueDetailTrackStateProvider implements TrackStateProviderAdapter {
  const _IssueDetailTrackStateProvider({required this.canWrite});

  final bool canWrite;

  static const String _revision = 'read-only-test-revision';

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

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      RepositoryUser(
        login: canWrite ? 'write-enabled-user' : 'read-only-user',
        displayName: canWrite ? 'Write Enabled User' : 'Read Only User',
      );

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryPermission> getPermission() async =>
      RepositoryPermission(canRead: true, canWrite: canWrite, isAdmin: false);

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
      'Attachment access is not required for the TS-42 widget test.',
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
      'TS-42 should not attempt to create commits in a read-only session.',
    );
  }

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-42 should not attempt to write issue files in a read-only session.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-42 should not attempt to write attachments in a read-only session.',
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
