import 'dart:async';
import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts450DashboardBootstrapFixture {
  Ts450DashboardBootstrapFixture._({
    required _Ts450BootstrapProvider provider,
    required this.repository,
  }) : _provider = provider;

  static const String bootstrapIndexPath =
      'TRACK/.trackstate/index/issues.json';

  final _Ts450BootstrapProvider _provider;
  final _Ts450DelayedSearchRepository repository;

  static Future<Ts450DashboardBootstrapFixture> create() async {
    final provider = _Ts450BootstrapProvider();
    final delegate = ProviderBackedTrackStateRepository(provider: provider);
    return Ts450DashboardBootstrapFixture._(
      provider: provider,
      repository: _Ts450DelayedSearchRepository(delegate),
    );
  }

  List<String> get textFileReads =>
      List<String>.unmodifiable(_provider.textFileReads);

  bool sawRead(String path) => _provider.textFileReads.contains(path);

  bool get sawIssueMarkdownRead =>
      _provider.textFileReads.any((path) => path.endsWith('/main.md'));

  int get searchRequestCount => repository.searchRequestCount;

  void releaseSearchResults() {
    repository.releaseSearchResults();
  }
}

class _Ts450DelayedSearchRepository implements TrackStateRepository {
  _Ts450DelayedSearchRepository(this._delegate);

  final ProviderBackedTrackStateRepository _delegate;
  final Completer<void> _searchRelease = Completer<void>();
  int searchRequestCount = 0;

  void releaseSearchResults() {
    if (_searchRelease.isCompleted) {
      return;
    }
    _searchRelease.complete();
  }

  @override
  bool get supportsGitHubAuth => _delegate.supportsGitHubAuth;

  @override
  bool get usesLocalPersistence => _delegate.usesLocalPersistence;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      _delegate.connect(connection);

  @override
  Future<TrackerSnapshot> loadSnapshot() => _delegate.loadSnapshot();

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    searchRequestCount += 1;
    await _searchRelease.future;
    return _delegate.searchIssuePage(
      jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) =>
      _delegate.searchIssues(jql);

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) => _delegate.createIssue(
    summary: summary,
    description: description,
    customFields: customFields,
  );

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) => _delegate.updateIssueDescription(issue, description);

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) =>
      _delegate.deleteIssue(issue);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) =>
      _delegate.archiveIssue(issue);

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) => _delegate.updateIssueStatus(issue, status);

  @override
  Future<TrackStateIssue> addIssueComment(TrackStateIssue issue, String body) =>
      _delegate.addIssueComment(issue, body);

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) =>
      _delegate.downloadAttachment(attachment);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) =>
      _delegate.loadIssueHistory(issue);

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) => _delegate.uploadIssueAttachment(issue: issue, name: name, bytes: bytes);
}

class _Ts450BootstrapProvider implements TrackStateProviderAdapter {
  static const Map<String, String> _files = <String, String>{
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
  {"id": "epic", "name": "Epic", "hierarchyLevel": 1, "icon": "epic", "workflowId": "default"},
  {"id": "story", "name": "Story", "hierarchyLevel": 0, "icon": "story", "workflowId": "default"},
  {"id": "bug", "name": "Bug", "hierarchyLevel": 0, "icon": "bug", "workflowId": "default"}
]
''',
    'TRACK/config/fields.json': '''
[
  {"id": "summary", "name": "Summary", "type": "string", "required": true, "reserved": true},
  {"id": "description", "name": "Description", "type": "markdown", "required": false, "reserved": true},
  {"id": "story-points", "name": "Story Points", "type": "number", "required": false}
]
''',
    'TRACK/config/priorities.json': '''
[
  {"id": "high", "name": "High"},
  {"id": "medium", "name": "Medium"},
  {"id": "low", "name": "Low"}
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
    "key": "TRACK-450E",
    "path": "TRACK/TRACK-450E/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "Dashboard bootstrap epic summary",
    "issueType": "epic",
    "status": "in-progress",
    "priority": "high",
    "assignee": "qa-user",
    "labels": ["dashboard", "bootstrap"],
    "updated": "2026-05-12T06:00:00Z",
    "progress": 0.65,
    "children": ["TRACK-450-1"],
    "archived": false
  },
  {
    "key": "TRACK-450-1",
    "path": "TRACK/TRACK-450-1/main.md",
    "parent": null,
    "epic": "TRACK-450E",
    "parentPath": null,
    "epicPath": "TRACK/TRACK-450E/main.md",
    "summary": "Summary count sourced from issues index",
    "issueType": "story",
    "status": "todo",
    "priority": "medium",
    "assignee": "qa-user",
    "labels": ["bootstrap-count"],
    "updated": "2026-05-12T06:01:00Z",
    "children": [],
    "archived": false
  },
  {
    "key": "TRACK-450-2",
    "path": "TRACK/TRACK-450-2/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "Loading placeholders keep unresolved fields readable",
    "issueType": "bug",
    "status": "in-progress",
    "priority": "high",
    "assignee": "qa-user",
    "labels": ["skeleton"],
    "updated": "2026-05-12T06:02:00Z",
    "children": [],
    "archived": false
  },
  {
    "key": "TRACK-450-3",
    "path": "TRACK/TRACK-450-3/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "Completed issue remains counted during bootstrap",
    "issueType": "story",
    "status": "done",
    "priority": "low",
    "assignee": "qa-user",
    "labels": ["done"],
    "updated": "2026-05-12T06:03:00Z",
    "children": [],
    "archived": false
  }
]
''',
    'TRACK/TRACK-450E/main.md': '''
---
key: TRACK-450E
project: TRACK
issueType: epic
status: in-progress
priority: high
summary: Dashboard bootstrap epic summary
assignee: qa-user
reporter: qa-user
labels:
  - dashboard
  - bootstrap
customFields:
  story-points: 13
updated: 2026-05-12T06:00:00Z
---

# Description

Bootstrap epic detail stays deferred while the Dashboard still renders summary tiles.
''',
    'TRACK/TRACK-450-1/main.md': '''
---
key: TRACK-450-1
project: TRACK
issueType: story
status: todo
priority: medium
summary: Summary count sourced from issues index
assignee: qa-user
reporter: qa-user
labels:
  - bootstrap-count
customFields:
  story-points: 5
updated: 2026-05-12T06:01:00Z
---

# Description

This issue proves metric counts can come from .trackstate/index/issues.json before detail hydration.
''',
    'TRACK/TRACK-450-2/main.md': '''
---
key: TRACK-450-2
project: TRACK
issueType: bug
status: in-progress
priority: high
summary: Loading placeholders keep unresolved fields readable
assignee: qa-user
reporter: qa-user
labels:
  - skeleton
customFields:
  story-points: 3
updated: 2026-05-12T06:02:00Z
---

# Description

This issue proves the dashboard can keep summary content visible while other fields remain deferred.
''',
    'TRACK/TRACK-450-3/main.md': '''
---
key: TRACK-450-3
project: TRACK
issueType: story
status: done
priority: low
summary: Completed issue remains counted during bootstrap
assignee: qa-user
reporter: qa-user
labels:
  - done
customFields:
  story-points: 1
updated: 2026-05-12T06:03:00Z
resolution: done
---

# Description

This issue keeps the completed counter non-zero while detail hydration is still pending.
''',
  };

  static const String _branch = 'main';
  static const String _revision = 'ts-450-revision';

  final List<String> textFileReads = <String>[];

  @override
  String get dataRef => _branch;

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'ts-450-user', displayName: 'TS-450 User');

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-450 does not exercise repository commits.',
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
    for (final path in _files.keys.toList()..sort())
      RepositoryTreeEntry(path: path, type: 'blob'),
  ];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    throw const TrackStateProviderException(
      'TS-450 does not exercise attachment reads.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-450 fixture for $path.');
    }
    textFileReads.add(path);
    return RepositoryTextFile(
      path: path,
      content: content,
      revision: _revision,
    );
  }

  @override
  Future<String> resolveWriteBranch() async => _branch;

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-450 does not exercise repository writes.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-450 does not exercise attachment uploads.',
    );
  }
}
