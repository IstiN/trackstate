import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts306CreateIssueFailureFixture {
  Ts306CreateIssueFailureFixture._({
    required this.repository,
    required _Ts306CreateIssueFailureProvider provider,
  }) : _provider = provider;

  final _Ts306CreateIssueFailureProvider _provider;

  int get mutationAttemptCount => _provider.applyFileChangesCalls;

  static const providerFailureMessage =
      'provider-failure: Simulated create issue mutation outage.';

  final ProviderBackedTrackStateRepository repository;

  static Future<Ts306CreateIssueFailureFixture> create() async {
    final provider = _Ts306CreateIssueFailureProvider();
    final repository = ProviderBackedTrackStateRepository(provider: provider);
    await repository.connect(
      const RepositoryConnection(
        repository: 'trackstate/trackstate',
        branch: 'main',
        token: 'ts-306-test-token',
      ),
    );
    return Ts306CreateIssueFailureFixture._(
      repository: repository,
      provider: provider,
    );
  }
}

class _Ts306CreateIssueFailureProvider
    implements TrackStateProviderAdapter, RepositoryFileMutator {
  static const _revision = 'ts-306-revision';

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
  {"id": "done", "name": "Done", "category": "done"}
]
''',
    'config/issue-types.json': '''
[
  {"id": "story", "name": "Story", "hierarchyLevel": 0, "icon": "story"},
  {"id": "bug", "name": "Bug", "hierarchyLevel": 0, "icon": "bug"}
]
''',
    'config/fields.json': '''
[
  {"id": "summary", "name": "Summary", "type": "string", "required": true},
  {"id": "description", "name": "Description", "type": "markdown", "required": false},
  {"id": "labels", "name": "Labels", "type": "array", "required": false}
]
''',
    'config/priorities.json': '''
[
  {"id": "medium", "name": "Medium"},
  {"id": "high", "name": "High"}
]
''',
    'TRACK-11/main.md': '''
---
key: TRACK-11
project: TRACK
issueType: story
status: todo
priority: medium
summary: Existing search result
assignee: qa-user
reporter: qa-user
labels:
  - existing
updated: 2026-05-10T08:00:00Z
---

# Description

Existing issue used to keep the repository snapshot realistic for TS-306.
''',
  };

  int applyFileChangesCalls = 0;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'ts-306-user', displayName: 'TS-306 User');

  @override
  Future<RepositoryCommitResult> applyFileChanges(
    RepositoryFileChangeRequest request,
  ) async {
    applyFileChangesCalls += 1;
    throw const TrackStateProviderException(
      Ts306CreateIssueFailureFixture.providerFailureMessage,
    );
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-306 should route create issue through applyFileChanges.',
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryPermission> getPermission() async =>
      const RepositoryPermission(canRead: true, canWrite: true, isAdmin: false);

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
      'TS-306 does not exercise attachment reads.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-306 fixture for $path.');
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
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-306 should not use single-file writes for create issue.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-306 does not exercise attachment writes.',
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
