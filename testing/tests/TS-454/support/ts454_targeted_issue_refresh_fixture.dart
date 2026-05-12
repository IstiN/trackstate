import 'dart:convert';
import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts454TargetedIssueRefreshFixture {
  Ts454TargetedIssueRefreshFixture._({
    required this.repository,
    required _Ts454Provider provider,
  }) : _provider = provider;

  static const String projectKey = 'TRACK';
  static const String issueAKey = 'TRACK-454A';
  static const String issueASummary = 'Issue A targeted refresh coverage';
  static const String issueADescription =
      'Issue A description stays scoped to the mutated issue.';
  static const String issueAComment =
      'Issue A comment stays visible after the scoped refresh.';
  static const String issueBKey = 'TRACK-454B';
  static const String issueBSummary = 'Issue B preserved hydration coverage';
  static const String issueBDescription =
      'Issue B detail must remain loaded and interactive.';
  static const String issueBComment =
      'Issue B comment proves unrelated detail stays hydrated.';
  static const String initialStatusLabel = 'To Do';
  static const String updatedStatusLabel = 'In Progress';

  final _Ts454Provider _provider;
  final Ts454RecordingRepository repository;

  static Future<Ts454TargetedIssueRefreshFixture> create() async {
    final provider = _Ts454Provider();
    final repository = Ts454RecordingRepository(provider: provider);
    await repository.connect(
      const RepositoryConnection(
        repository: 'trackstate/trackstate',
        branch: 'main',
        token: 'ts-454-token',
      ),
    );
    return Ts454TargetedIssueRefreshFixture._(
      repository: repository,
      provider: provider,
    );
  }

  int get snapshotLoadCount => repository.snapshotLoadCount;

  List<Ts454HydrationCall> get hydrateCalls =>
      List<Ts454HydrationCall>.unmodifiable(repository.hydrateCalls);

  TrackStateIssue requireCachedIssue(String key) {
    final snapshot = repository.cachedSnapshot;
    if (snapshot == null) {
      throw StateError('TS-454 expected the repository snapshot to be cached.');
    }
    return snapshot.issues.firstWhere((issue) => issue.key == key);
  }

  String indexStatusFor(String key) => _provider.indexStatusFor(key);
}

class Ts454HydrationCall {
  const Ts454HydrationCall({
    required this.issueKey,
    required this.scopes,
    required this.force,
  });

  final String issueKey;
  final Set<IssueHydrationScope> scopes;
  final bool force;
}

class Ts454RecordingRepository extends ProviderBackedTrackStateRepository {
  Ts454RecordingRepository({required _Ts454Provider provider})
    : super(provider: provider);

  int snapshotLoadCount = 0;
  final List<Ts454HydrationCall> hydrateCalls = <Ts454HydrationCall>[];

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    snapshotLoadCount += 1;
    return super.loadSnapshot();
  }

  @override
  Future<TrackStateIssue> hydrateIssue(
    TrackStateIssue issue, {
    Set<IssueHydrationScope> scopes = const {IssueHydrationScope.detail},
    bool force = false,
  }) {
    hydrateCalls.add(
      Ts454HydrationCall(
        issueKey: issue.key,
        scopes: Set<IssueHydrationScope>.from(scopes),
        force: force,
      ),
    );
    return super.hydrateIssue(issue, scopes: scopes, force: force);
  }
}

class _Ts454Provider
    implements TrackStateProviderAdapter, RepositoryFileMutator {
  _Ts454Provider()
    : _textFiles = Map<String, String>.from(_seedFiles),
      _revisionsByPath = <String, String>{
        for (final path in _seedFiles.keys) path: _revisionFor(path, 1),
      };

  static const String _branch = 'main';

  static const Map<String, String> _seedFiles = <String, String>{
    'TRACK/project.json': '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config"
}
''',
    'TRACK/config/statuses.json': '''
[
  {"id": "todo", "name": "To Do", "category": "new"},
  {"id": "in-progress", "name": "In Progress", "category": "indeterminate"},
  {"id": "done", "name": "Done", "category": "done"}
]
''',
    'TRACK/config/issue-types.json': '''
[
  {"id": "story", "name": "Story", "hierarchyLevel": 0, "icon": "story", "workflowId": "default"}
]
''',
    'TRACK/config/fields.json': '''
[
  {"id": "summary", "name": "Summary", "type": "string", "required": true, "reserved": true},
  {"id": "description", "name": "Description", "type": "markdown", "required": false, "reserved": true}
]
''',
    'TRACK/config/priorities.json': '''
[
  {"id": "medium", "name": "Medium"}
]
''',
    'TRACK/config/workflows.json': '''
{
  "default": {
    "name": "Default Workflow",
    "statuses": ["todo", "in-progress", "done"],
    "transitions": [
      {"id": "start", "name": "Start progress", "from": "todo", "to": "in-progress"},
      {"id": "finish", "name": "Complete", "from": "in-progress", "to": "done"}
    ]
  }
}
''',
    'TRACK/.trackstate/index/issues.json': '''
[
  {
    "key": "TRACK-454A",
    "path": "TRACK/TRACK-454A/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "Issue A targeted refresh coverage",
    "issueType": "story",
    "status": "todo",
    "priority": "medium",
    "assignee": "qa-user",
    "labels": ["targeted-refresh"],
    "updated": "2026-05-12T05:00:00Z",
    "children": [],
    "archived": false
  },
  {
    "key": "TRACK-454B",
    "path": "TRACK/TRACK-454B/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "Issue B preserved hydration coverage",
    "issueType": "story",
    "status": "in-progress",
    "priority": "medium",
    "assignee": "qa-user",
    "labels": ["preserved-detail"],
    "updated": "2026-05-12T05:01:00Z",
    "children": [],
    "archived": false
  }
]
''',
    'TRACK/TRACK-454A/main.md': '''
---
key: TRACK-454A
project: TRACK
issueType: story
status: todo
priority: medium
summary: Issue A targeted refresh coverage
assignee: qa-user
reporter: qa-user
labels:
  - targeted-refresh
updated: 2026-05-12T05:00:00Z
---

# Description

Issue A description stays scoped to the mutated issue.
''',
    'TRACK/TRACK-454A/comments/0001.md': '''
---
author: qa-user
created: 2026-05-12T05:02:00Z
updated: 2026-05-12T05:02:00Z
---

Issue A comment stays visible after the scoped refresh.
''',
    'TRACK/TRACK-454B/main.md': '''
---
key: TRACK-454B
project: TRACK
issueType: story
status: in-progress
priority: medium
summary: Issue B preserved hydration coverage
assignee: qa-user
reporter: qa-user
labels:
  - preserved-detail
updated: 2026-05-12T05:01:00Z
---

# Description

Issue B detail must remain loaded and interactive.
''',
    'TRACK/TRACK-454B/comments/0001.md': '''
---
author: qa-user
created: 2026-05-12T05:03:00Z
updated: 2026-05-12T05:03:00Z
---

Issue B comment proves unrelated detail stays hydrated.
''',
  };

  final Map<String, String> _textFiles;
  final Map<String, String> _revisionsByPath;
  int _revisionCounter = 1;
  int _commitCounter = 0;

  @override
  String get dataRef => _branch;

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  String indexStatusFor(String key) {
    final rawIndex = _textFiles['TRACK/.trackstate/index/issues.json'];
    if (rawIndex == null) {
      throw StateError(
        'Missing TRACK/.trackstate/index/issues.json in TS-454.',
      );
    }
    final entries = jsonDecode(rawIndex) as List<dynamic>;
    final entry = entries.cast<Map<String, dynamic>>().firstWhere(
      (candidate) => candidate['key'] == key,
      orElse: () =>
          throw StateError('Missing $key in the TS-454 repository index.'),
    );
    return '${entry['status'] ?? ''}';
  }

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'ts-454-user', displayName: 'TS-454 User');

  @override
  Future<RepositoryCommitResult> applyFileChanges(
    RepositoryFileChangeRequest request,
  ) async {
    for (final change in request.changes) {
      switch (change) {
        case RepositoryTextFileChange():
          _assertExpectedRevision(change.path, change.expectedRevision);
          _textFiles[change.path] = change.content;
          _revisionsByPath[change.path] = _nextRevision(change.path);
        case RepositoryDeleteFileChange():
          _assertExpectedRevision(change.path, change.expectedRevision);
          _textFiles.remove(change.path);
          _revisionsByPath.remove(change.path);
        case RepositoryBinaryFileChange():
          throw const TrackStateProviderException(
            'TS-454 does not exercise binary file mutations.',
          );
      }
    }
    _commitCounter += 1;
    return RepositoryCommitResult(
      branch: request.branch,
      message: request.message,
      revision: 'ts454-commit-$_commitCounter',
    );
  }

  void _assertExpectedRevision(String path, String? expectedRevision) {
    if (expectedRevision == null) {
      return;
    }
    final actual = _revisionsByPath[path];
    if (actual != expectedRevision) {
      throw TrackStateProviderException(
        'TS-454 revision mismatch for $path. Expected $expectedRevision but observed $actual.',
      );
    }
  }

  String _nextRevision(String path) {
    _revisionCounter += 1;
    return _revisionFor(path, _revisionCounter);
  }

  static String _revisionFor(String path, int counter) =>
      'ts454-${counter}-${path.replaceAll('/', '_')}';

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-454 should persist workflow transitions through applyFileChanges.',
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == _branch);

  @override
  Future<RepositoryPermission> getPermission() async =>
      const RepositoryPermission(canRead: true, canWrite: true, isAdmin: false);

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async => [
    for (final path in _textFiles.keys.toList()..sort())
      RepositoryTreeEntry(path: path, type: 'blob'),
  ];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    throw const TrackStateProviderException(
      'TS-454 does not exercise attachment reads.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _textFiles[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-454 fixture for $path.');
    }
    return RepositoryTextFile(
      path: path,
      content: content,
      revision: _revisionsByPath[path],
    );
  }

  @override
  Future<String> resolveWriteBranch() async => _branch;

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-454 should not use single-file writes for targeted refresh coverage.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-454 does not exercise attachment writes.',
    );
  }
}
