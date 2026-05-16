import 'dart:convert';
import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts734RefreshMatrixRepository extends ProviderBackedTrackStateRepository {
  Ts734RefreshMatrixRepository._(this._provider) : super(provider: _provider);

  factory Ts734RefreshMatrixRepository() =>
      Ts734RefreshMatrixRepository._(_Ts734MutableProvider());

  static const String issueAKey = 'TRACK-734A';
  static const String issueASummary = 'Issue A dashboard counter source';
  static const String issueCKey = 'TRACK-734C';
  static const String issueCSummary = 'Issue C refresh matrix target';
  static const String initialComment =
      'Issue C original comment remains visible until the comments-only sync arrives.';
  static const String updatedComment =
      'Issue C synced comment appears after the comments-only refresh without rebuilding unrelated surfaces.';
  static const String initialTagPrefix = 'ts734-release-';
  static const String updatedTagPrefix = 'ts734-sync-';

  final _Ts734MutableProvider _provider;
  final List<Ts734HydrationCall> hydrateCalls = <Ts734HydrationCall>[];
  int loadSnapshotCalls = 0;

  Future<void> connectForTest() {
    return connect(
      const RepositoryConnection(
        repository: 'trackstate/trackstate',
        branch: 'main',
        token: 'ts734-token',
      ),
    );
  }

  Future<void> emitCommentsOnlyRefresh() => _provider.emitCommentsOnlyRefresh();

  Future<void> emitProjectMetaOnlyRefresh() =>
      _provider.emitProjectMetaOnlyRefresh();

  Future<void> emitProjectMetaRefresh() => _provider.emitProjectMetaRefresh();

  String get releaseTagPrefix => _provider.releaseTagPrefix;

  String get currentIssueCComment => _provider.issueCommentBody(issueCKey);

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    loadSnapshotCalls += 1;
    final snapshot = await super.loadSnapshot();
    return TrackerSnapshot(
      project: snapshot.project,
      issues: [
        for (final issue in snapshot.issues)
          if (issue.key == issueCKey)
            issue.copyWith(
              description: _provider.issueDescription(issueCKey),
              hasDetailLoaded: true,
              hasCommentsLoaded: false,
              comments: const <IssueComment>[],
            )
          else
            issue,
      ],
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: snapshot.loadWarnings,
      readiness: snapshot.readiness,
      startupRecovery: snapshot.startupRecovery,
    );
  }

  @override
  Future<TrackStateIssue> hydrateIssue(
    TrackStateIssue issue, {
    Set<IssueHydrationScope> scopes = const {IssueHydrationScope.detail},
    bool force = false,
  }) {
    hydrateCalls.add(
      Ts734HydrationCall(
        issueKey: issue.key,
        scopes: Set<IssueHydrationScope>.from(scopes),
        force: force,
      ),
    );
    return super.hydrateIssue(issue, scopes: scopes, force: force);
  }
}

class Ts734HydrationCall {
  const Ts734HydrationCall({
    required this.issueKey,
    required this.scopes,
    required this.force,
  });

  final String issueKey;
  final Set<IssueHydrationScope> scopes;
  final bool force;
}

class _Ts734MutableProvider
    implements TrackStateProviderAdapter, RepositoryFileMutator {
  static const RepositoryPermission _permission = RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: false,
    canCreateBranch: true,
    canManageAttachments: true,
    attachmentUploadMode: AttachmentUploadMode.full,
    supportsReleaseAttachmentWrites: true,
    canCheckCollaborators: false,
  );

  _Ts734MutableProvider() {
    _rebuildFiles();
  }

  final Map<String, _Ts734IssueRecord> _issues = <String, _Ts734IssueRecord>{
    Ts734RefreshMatrixRepository.issueAKey: _Ts734IssueRecord(
      key: Ts734RefreshMatrixRepository.issueAKey,
      summary: Ts734RefreshMatrixRepository.issueASummary,
      issueTypeId: 'story',
      statusId: 'todo',
      priorityId: 'medium',
      updated: '2026-05-14T18:00:00Z',
      description:
          'Issue A starts open so the dashboard counters can change when project metadata refreshes.',
      comments: const <String>[],
      labels: const <String>['dashboard'],
    ),
    'TRACK-734B': _Ts734IssueRecord(
      key: 'TRACK-734B',
      summary: 'Issue B progress baseline',
      issueTypeId: 'story',
      statusId: 'in-progress',
      priorityId: 'high',
      updated: '2026-05-14T18:05:00Z',
      description:
          'Issue B keeps the in-progress dashboard metric visible throughout the scenario.',
      comments: const <String>[],
      labels: const <String>['dashboard'],
    ),
    Ts734RefreshMatrixRepository.issueCKey: _Ts734IssueRecord(
      key: Ts734RefreshMatrixRepository.issueCKey,
      summary: Ts734RefreshMatrixRepository.issueCSummary,
      issueTypeId: 'story',
      statusId: 'todo',
      priorityId: 'high',
      updated: '2026-05-14T18:10:00Z',
      description:
          'Issue C stays selected while the sync coordinator publishes targeted refreshes.',
      comments: const <String>[Ts734RefreshMatrixRepository.initialComment],
      labels: const <String>['comments', 'board'],
    ),
  };

  final Map<String, String> _textFiles = <String, String>{};
  RepositorySyncCheck? _queuedCheck;
  int _revision = 1;
  String _releaseTagPrefix = Ts734RefreshMatrixRepository.initialTagPrefix;

  String get releaseTagPrefix => _releaseTagPrefix;

  String issueDescription(String key) => _issue(key).description;

  String issueCommentBody(String key) => _issue(key).comments.join('\n');

  Future<void> emitCommentsOnlyRefresh() async {
    final issue = _issue(Ts734RefreshMatrixRepository.issueCKey);
    _issues[issue.key] = issue.copyWith(
      comments: const <String>[Ts734RefreshMatrixRepository.updatedComment],
      updated: '2026-05-14T18:20:00Z',
    );
    _rebuildFiles();
    _queueHostedRefresh(<String>{'TRACK-734C/comments/0001.md'});
  }

  Future<void> emitProjectMetaOnlyRefresh() async {
    _releaseTagPrefix = Ts734RefreshMatrixRepository.updatedTagPrefix;
    _rebuildFiles();
    _queueHostedRefresh(<String>{'project.json'});
  }

  Future<void> emitProjectMetaRefresh() async {
    _releaseTagPrefix = Ts734RefreshMatrixRepository.updatedTagPrefix;
    final issue = _issue(Ts734RefreshMatrixRepository.issueAKey);
    _issues[issue.key] = issue.copyWith(
      statusId: 'done',
      updated: '2026-05-14T18:30:00Z',
      description:
          'Issue A is completed in the refreshed snapshot so the dashboard counters visibly change.',
    );
    _rebuildFiles();
    _queueHostedRefresh(<String>{
      'project.json',
      '.trackstate/index/issues.json',
      'TRACK-734A/main.md',
    });
  }

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    if (previousState == null) {
      return RepositorySyncCheck(state: _syncState());
    }
    final queued = _queuedCheck;
    _queuedCheck = null;
    return queued ?? RepositorySyncCheck(state: _syncState());
  }

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'ts734-user', displayName: 'TS-734 User');

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryPermission> getPermission() async => _permission;

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async => [
    for (final path in _textFiles.keys)
      RepositoryTreeEntry(path: path, type: 'blob'),
  ];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    throw const TrackStateProviderException(
      'TS-734 does not require attachment downloads.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-734 does not require attachment uploads.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _textFiles[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-734 fixture for $path.');
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
    _textFiles[request.path] = request.content;
    _revision += 1;
    return RepositoryCommitResult(
      branch: request.branch,
      message: request.message,
      revision: _currentRevision,
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    _textFiles[request.path] = request.content;
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
          _textFiles[change.path] = change.content;
        case RepositoryDeleteFileChange():
          _textFiles.remove(change.path);
        case RepositoryBinaryFileChange():
          throw const TrackStateProviderException(
            'TS-734 does not support binary repository changes.',
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

  void _queueHostedRefresh(Set<String> changedPaths) {
    _revision += 1;
    _queuedCheck = RepositorySyncCheck(
      state: _syncState(),
      signals: const <WorkspaceSyncSignal>{
        WorkspaceSyncSignal.hostedRepository,
      },
      changedPaths: changedPaths,
    );
  }

  RepositorySyncState _syncState() => RepositorySyncState(
    providerType: providerType,
    repositoryRevision: 'ts734-revision-$_revision',
    sessionRevision: 'ts734-session',
    connectionState: ProviderConnectionState.connected,
    permission: _permission,
  );

  String get _currentRevision => 'ts734-r$_revision';

  _Ts734IssueRecord _issue(String key) {
    final issue = _issues[key];
    if (issue == null) {
      throw StateError('Missing TS-734 issue state for $key.');
    }
    return issue;
  }

  void _rebuildFiles() {
    _textFiles
      ..clear()
      ..addAll(<String, String>{
        'project.json': _projectJson(_releaseTagPrefix),
        'config/statuses.json': _statusesJson,
        'config/issue-types.json': _issueTypesJson,
        'config/fields.json': _fieldsJson,
        'config/priorities.json': _prioritiesJson,
        'config/workflows.json': _workflowsJson,
        '.trackstate/index/issues.json': _issueIndexJson(),
        for (final issue in _issues.values) ...<String, String>{
          '${issue.key}/main.md': _issueMarkdown(issue),
          for (var index = 0; index < issue.comments.length; index += 1)
            '${issue.key}/comments/${(index + 1).toString().padLeft(4, '0')}.md':
                _commentMarkdown(
                  body: issue.comments[index],
                  created: issue.updated,
                ),
        },
      });
  }

  String _issueIndexJson() {
    final entries = [
      for (final issue in _issues.values)
        <String, Object?>{
          'key': issue.key,
          'path': '${issue.key}/main.md',
          'parent': null,
          'epic': null,
          'parentPath': null,
          'epicPath': null,
          'summary': issue.summary,
          'issueType': issue.issueTypeId,
          'status': issue.statusId,
          'priority': issue.priorityId,
          'assignee': 'Taylor QA',
          'labels': issue.labels,
          'updated': issue.updated,
          'children': const <Object?>[],
          'archived': false,
        },
    ];
    return const JsonEncoder.withIndent('  ').convert(entries);
  }

  String _issueMarkdown(_Ts734IssueRecord issue) {
    final labels = issue.labels.map((label) => '  - $label').join('\n');
    return '''
---
key: ${issue.key}
project: TRACK
issueType: ${issue.issueTypeId}
status: ${issue.statusId}
priority: ${issue.priorityId}
summary: ${issue.summary}
assignee: Taylor QA
reporter: Taylor QA
labels:
$labels
updated: ${issue.updated}
---

# Description

${issue.description}
''';
  }

  static String _commentMarkdown({
    required String body,
    required String created,
  }) {
    return '''
---
author: Taylor QA
created: $created
updated: $created
---

$body
''';
  }
}

class _Ts734IssueRecord {
  const _Ts734IssueRecord({
    required this.key,
    required this.summary,
    required this.issueTypeId,
    required this.statusId,
    required this.priorityId,
    required this.updated,
    required this.description,
    required this.comments,
    required this.labels,
  });

  final String key;
  final String summary;
  final String issueTypeId;
  final String statusId;
  final String priorityId;
  final String updated;
  final String description;
  final List<String> comments;
  final List<String> labels;

  _Ts734IssueRecord copyWith({
    String? statusId,
    String? updated,
    String? description,
    List<String>? comments,
  }) {
    return _Ts734IssueRecord(
      key: key,
      summary: summary,
      issueTypeId: issueTypeId,
      statusId: statusId ?? this.statusId,
      priorityId: priorityId,
      updated: updated ?? this.updated,
      description: description ?? this.description,
      comments: comments ?? this.comments,
      labels: labels,
    );
  }
}

String _projectJson(String tagPrefix) =>
    '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config",
  "attachmentStorage": {
    "mode": "github-releases",
    "githubReleases": {
      "tagPrefix": "$tagPrefix"
    }
  }
}
''';

const String _statusesJson = '''
[
  {"id": "todo", "name": "To Do", "category": "new"},
  {"id": "in-progress", "name": "In Progress", "category": "indeterminate"},
  {"id": "done", "name": "Done", "category": "done"}
]
''';

const String _issueTypesJson = '''
[
  {"id": "story", "name": "Story", "hierarchyLevel": 0, "icon": "story"}
]
''';

const String _fieldsJson = '''
[
  {"id": "summary", "name": "Summary", "type": "string", "required": true, "reserved": true},
  {"id": "description", "name": "Description", "type": "markdown", "required": false, "reserved": true}
]
''';

const String _prioritiesJson = '''
[
  {"id": "high", "name": "High"},
  {"id": "medium", "name": "Medium"}
]
''';

const String _workflowsJson = '''
{
  "default": {
    "name": "Default Workflow",
    "statuses": ["todo", "in-progress", "done"],
    "transitions": [
      {"id": "start", "name": "Start", "from": "todo", "to": "in-progress"},
      {"id": "finish", "name": "Finish", "from": "in-progress", "to": "done"}
    ]
  }
}
''';
