import 'dart:convert';
import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts787EmptyDomainPathRepository
    extends ProviderBackedTrackStateRepository {
  Ts787EmptyDomainPathRepository._(this._provider) : super(provider: _provider);

  factory Ts787EmptyDomainPathRepository() =>
      Ts787EmptyDomainPathRepository._(_Ts787MutableProvider());

  static const String issueCKey = 'TRACK-787C';
  static const String issueCSummary = 'Issue C empty sync path guard';
  static const String initialComment =
      'Issue C original comment remains visible before the empty sync path arrives.';
  static const String hiddenUpdatedComment =
      'Issue C hidden synced comment should stay invisible when the empty sync path is filtered out.';
  static const String emptyChangedPath = '';

  final _Ts787MutableProvider _provider;
  final List<Ts787HydrationCall> hydrateCalls = <Ts787HydrationCall>[];
  int loadSnapshotCalls = 0;

  Future<void> connectForTest() {
    return connect(
      const RepositoryConnection(
        repository: 'trackstate/trackstate',
        branch: 'main',
        token: 'ts787-token',
      ),
    );
  }

  Future<void> emitEmptyDomainRefresh() => _provider.emitEmptyDomainRefresh();

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
      Ts787HydrationCall(
        issueKey: issue.key,
        scopes: Set<IssueHydrationScope>.from(scopes),
        force: force,
      ),
    );
    return super.hydrateIssue(issue, scopes: scopes, force: force);
  }
}

class Ts787HydrationCall {
  const Ts787HydrationCall({
    required this.issueKey,
    required this.scopes,
    required this.force,
  });

  final String issueKey;
  final Set<IssueHydrationScope> scopes;
  final bool force;
}

class _Ts787MutableProvider implements TrackStateProviderAdapter {
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

  _Ts787MutableProvider() {
    _rebuildFiles();
  }

  final Map<String, _Ts787IssueRecord> _issues = <String, _Ts787IssueRecord>{
    Ts787EmptyDomainPathRepository.issueCKey: _Ts787IssueRecord(
      key: Ts787EmptyDomainPathRepository.issueCKey,
      summary: Ts787EmptyDomainPathRepository.issueCSummary,
      issueTypeId: 'story',
      statusId: 'todo',
      priorityId: 'high',
      updated: '2026-05-16T08:10:00Z',
      description:
          'Issue C stays selected while hosted workspace sync processes malformed empty changed paths.',
      comments: const <String>[Ts787EmptyDomainPathRepository.initialComment],
      labels: const <String>['comments', 'board'],
    ),
  };

  final Map<String, String> _textFiles = <String, String>{};
  RepositorySyncCheck? _queuedCheck;
  int _revision = 1;
  int syncCheckCount = 0;

  String get repositoryRevision => 'ts787-revision-$_revision';

  String issueDescription(String key) => _issue(key).description;

  String issueCommentBody(String key) => _issue(key).comments.join('\n');

  Future<void> emitEmptyDomainRefresh() async {
    final issue = _issue(Ts787EmptyDomainPathRepository.issueCKey);
    _issues[issue.key] = issue.copyWith(
      comments: const <String>[
        Ts787EmptyDomainPathRepository.hiddenUpdatedComment,
      ],
      updated: '2026-05-16T08:20:00Z',
    );
    _rebuildFiles();
    _queueHostedRefresh(const <String>{
      Ts787EmptyDomainPathRepository.emptyChangedPath,
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
      const RepositoryUser(login: 'ts787-user', displayName: 'TS-787 User');

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
      'TS-787 does not require attachment downloads.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-787 does not require attachment uploads.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _textFiles[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-787 fixture for $path.');
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
      'TS-787 should not create commits.',
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
    sessionRevision: 'ts787-session',
    connectionState: ProviderConnectionState.connected,
    permission: _permission,
  );

  String get _currentRevision => 'ts787-r$_revision';

  _Ts787IssueRecord _issue(String key) {
    final issue = _issues[key];
    if (issue == null) {
      throw StateError('Missing TS-787 issue state for $key.');
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

  String _issueMarkdown(_Ts787IssueRecord issue) {
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

  Future<Uint8List> readBinaryFile(String path, {required String ref}) async {
    throw const TrackStateProviderException(
      'TS-787 does not require binary file reads.',
    );
  }
}

class _Ts787IssueRecord {
  const _Ts787IssueRecord({
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

  _Ts787IssueRecord copyWith({
    String? updated,
    String? description,
    List<String>? comments,
  }) {
    return _Ts787IssueRecord(
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
  "repository": "trackstate/trackstate",
  "branch": "main",
  "defaultLocale": "en"
}
''';

const String _statusesJson = '''
[
  {"id":"todo","name":"To Do","category":"new"},
  {"id":"done","name":"Done","category":"done"}
]
''';

const String _issueTypesJson = '''
[
  {"id":"story","name":"Story","hierarchyLevel":0,"icon":"story"}
]
''';

const String _fieldsJson = '''
[
  {"id":"summary","name":"Summary","type":"string","required":true},
  {"id":"description","name":"Description","type":"markdown","required":false},
  {"id":"priority","name":"Priority","type":"option","required":false},
  {"id":"labels","name":"Labels","type":"array","required":false}
]
''';

const String _prioritiesJson = '''
[
  {"id":"high","name":"High"}
]
''';

const String _workflowsJson = '''
[
  {
    "id":"default",
    "name":"Default Workflow",
    "transitions":[]
  }
]
''';
