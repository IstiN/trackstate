import 'dart:convert';
import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts741InvalidDomainScopeRepository
    extends ProviderBackedTrackStateRepository {
  Ts741InvalidDomainScopeRepository._(this._provider)
    : super(provider: _provider);

  factory Ts741InvalidDomainScopeRepository() =>
      Ts741InvalidDomainScopeRepository._(_Ts741MutableProvider());

  static const String issueCKey = 'TRACK-741C';
  static const String issueCSummary = 'Issue C invalid sync scope guard';
  static const String initialComment =
      'Issue C original comment remains visible before the unknown sync scope arrives.';
  static const String hiddenUpdatedComment =
      'Issue C hidden synced comment should stay invisible when the unknown sync scope is filtered out.';
  static const String unknownChangedPath =
      'TRACK-741C/sync-domains/unknown-domain.md';

  final _Ts741MutableProvider _provider;
  final List<Ts741HydrationCall> hydrateCalls = <Ts741HydrationCall>[];
  int loadSnapshotCalls = 0;

  Future<void> connectForTest() {
    return connect(
      const RepositoryConnection(
        repository: 'trackstate/trackstate',
        branch: 'main',
        token: 'ts741-token',
      ),
    );
  }

  Future<void> emitUnknownDomainRefresh() =>
      _provider.emitUnknownDomainRefresh();

  String get currentIssueCComment => _provider.issueCommentBody(issueCKey);

  int get syncCheckCount => _provider.syncCheckCount;

  String get repositoryRevision => _provider.repositoryRevision;

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
      Ts741HydrationCall(
        issueKey: issue.key,
        scopes: Set<IssueHydrationScope>.from(scopes),
        force: force,
      ),
    );
    return super.hydrateIssue(issue, scopes: scopes, force: force);
  }
}

class Ts741HydrationCall {
  const Ts741HydrationCall({
    required this.issueKey,
    required this.scopes,
    required this.force,
  });

  final String issueKey;
  final Set<IssueHydrationScope> scopes;
  final bool force;
}

class _Ts741MutableProvider implements TrackStateProviderAdapter {
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

  _Ts741MutableProvider() {
    _rebuildFiles();
  }

  final Map<String, _Ts741IssueRecord> _issues = <String, _Ts741IssueRecord>{
    Ts741InvalidDomainScopeRepository.issueCKey: _Ts741IssueRecord(
      key: Ts741InvalidDomainScopeRepository.issueCKey,
      summary: Ts741InvalidDomainScopeRepository.issueCSummary,
      issueTypeId: 'story',
      statusId: 'todo',
      priorityId: 'high',
      updated: '2026-05-14T18:10:00Z',
      description:
          'Issue C stays selected while hosted workspace sync processes malformed domain scopes.',
      comments: const <String>[
        Ts741InvalidDomainScopeRepository.initialComment,
      ],
      labels: const <String>['comments', 'board'],
    ),
  };

  final Map<String, String> _textFiles = <String, String>{};
  RepositorySyncCheck? _queuedCheck;
  int _revision = 1;
  int syncCheckCount = 0;

  String get repositoryRevision => 'ts741-revision-$_revision';

  String issueDescription(String key) => _issue(key).description;

  String issueCommentBody(String key) => _issue(key).comments.join('\n');

  Future<void> emitUnknownDomainRefresh() async {
    final issue = _issue(Ts741InvalidDomainScopeRepository.issueCKey);
    _issues[issue.key] = issue.copyWith(
      comments: const <String>[
        Ts741InvalidDomainScopeRepository.hiddenUpdatedComment,
      ],
      updated: '2026-05-14T18:20:00Z',
    );
    _rebuildFiles();
    _queueHostedRefresh(const <String>{
      Ts741InvalidDomainScopeRepository.unknownChangedPath,
    });
  }

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    syncCheckCount += 1;
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
      const RepositoryUser(login: 'ts741-user', displayName: 'TS-741 User');

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
      'TS-741 does not require attachment downloads.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-741 does not require attachment uploads.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _textFiles[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-741 fixture for $path.');
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
      'TS-741 should not create commits.',
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
    repositoryRevision: repositoryRevision,
    sessionRevision: 'ts741-session',
    connectionState: ProviderConnectionState.connected,
    permission: _permission,
  );

  String get _currentRevision => 'ts741-r$_revision';

  _Ts741IssueRecord _issue(String key) {
    final issue = _issues[key];
    if (issue == null) {
      throw StateError('Missing TS-741 issue state for $key.');
    }
    return issue;
  }

  void _rebuildFiles() {
    _textFiles
      ..clear()
      ..addAll(<String, String>{
        'project.json': _projectJson,
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

  String _issueMarkdown(_Ts741IssueRecord issue) {
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

class _Ts741IssueRecord {
  const _Ts741IssueRecord({
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

  _Ts741IssueRecord copyWith({
    String? updated,
    String? description,
    List<String>? comments,
  }) {
    return _Ts741IssueRecord(
      key: key,
      summary: summary,
      issueTypeId: issueTypeId,
      statusId: statusId,
      priorityId: priorityId,
      updated: updated ?? this.updated,
      description: description ?? this.description,
      comments: comments ?? this.comments,
      labels: labels,
    );
  }
}

const String _projectJson = '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config"
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
  {"id": "high", "name": "High"}
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
