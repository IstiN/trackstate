import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts65IssueMetadataFixture {
  Ts65IssueMetadataFixture._(this.repository);

  final TrackStateRepository repository;

  static Ts65IssueMetadataFixture create() {
    return Ts65IssueMetadataFixture._(
      ProviderBackedTrackStateRepository(
        provider: const _Ts65TrackStateProvider(),
        supportsGitHubAuth: false,
      ),
    );
  }

  Future<TrackStateIssue> loadIssue() async {
    final snapshot = await repository.loadSnapshot();
    return snapshot.issues.singleWhere((issue) => issue.key == 'TRACK-65');
  }
}

class _Ts65TrackStateProvider implements TrackStateProviderAdapter {
  const _Ts65TrackStateProvider();

  static const String _revision = 'ts-65-revision';

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => const RepositorySyncCheck(
    state: RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: _revision,
      sessionRevision: 'ts65',
      connectionState: ProviderConnectionState.connected,
      permission: RepositoryPermission(
        canRead: true,
        canWrite: false,
        isAdmin: false,
      ),
    ),
  );

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => const RepositorySyncCheck(
    state: RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: _revision,
      sessionRevision: 'ts65',
      connectionState: ProviderConnectionState.connected,
      permission: RepositoryPermission(
        canRead: true,
        canWrite: false,
        isAdmin: false,
      ),
    ),
  );

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
  {"id": "wip", "name": "In Progress", "category": "indeterminate"},
  {"id": "done", "name": "Done", "category": "done"}
]
''',
    'config/issue-types.json': '''
[
  {"id": "story", "name": "Story", "hierarchyLevel": 0, "icon": "story"}
]
''',
    'config/fields.json': '''
[
  {"id": "summary", "name": "Summary", "type": "string", "required": true},
  {"id": "description", "name": "Description", "type": "markdown", "required": false},
  {"id": "acceptanceCriteria", "name": "Acceptance Criteria", "type": "markdown", "required": false},
  {"id": "priority", "name": "Priority", "type": "option", "required": false}
]
''',
    'TRACK-65/main.md': '''
---
key: TRACK-65
project: TRACK
issueType: story
status: wip
priority: high
summary: Resolve issue metadata from stable status IDs
assignee: Metadata Reader
reporter: QA Automation
labels:
  - metadata
components:
  - ui
updated: just now
---

# Description

The UI should resolve the stored status ID to the localized status label.
''',
    'TRACK-65/acceptance_criteria.md': '''
- Render "In Progress" while keeping the canonical custom status ID in the data model.
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
      const RepositoryUser(login: 'ts65-reader', displayName: 'TS-65 Reader');

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryPermission> getPermission() async =>
      const RepositoryPermission(
        canRead: true,
        canWrite: false,
        isAdmin: false,
      );

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
      'TS-65 does not exercise attachment access.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-65 fixture for $path.');
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
      'TS-65 should not attempt to create commits.',
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-65 should not attempt to write issue files.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-65 should not attempt to write attachments.',
    );
  }
}
