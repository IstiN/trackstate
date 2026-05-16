import 'dart:convert';
import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts766AttachmentRefreshRepository
    extends ProviderBackedTrackStateRepository {
  Ts766AttachmentRefreshRepository._(this._provider)
    : super(provider: _provider);

  factory Ts766AttachmentRefreshRepository() =>
      Ts766AttachmentRefreshRepository._(_Ts766MutableProvider());

  static const String issueCKey = 'TRACK-766C';
  static const String issueCSummary = 'Issue C attachment sync scope target';
  static const String initialAttachmentName = 'ts766-initial-wireframe.png';
  static const String updatedAttachmentName = 'ts766-synced-spec.pdf';
  static const String attachmentPath =
      '$issueCKey/attachments/ts766-sync-artifact.bin';
  static const String attachmentMetadataPath = '$issueCKey/attachments.json';

  final _Ts766MutableProvider _provider;
  final List<Ts766HydrationCall> hydrateCalls = <Ts766HydrationCall>[];
  int loadSnapshotCalls = 0;

  Future<void> connectForTest() {
    return connect(
      const RepositoryConnection(
        repository: 'trackstate/trackstate',
        branch: 'main',
        token: 'ts766-token',
      ),
    );
  }

  Future<void> emitAttachmentsOnlyRefresh() =>
      _provider.emitAttachmentsOnlyRefresh();

  String get currentAttachmentDisplayName =>
      _provider.currentAttachmentDisplayName;

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
              hasAttachmentsLoaded: false,
              attachments: const <IssueAttachment>[],
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
      Ts766HydrationCall(
        issueKey: issue.key,
        scopes: Set<IssueHydrationScope>.from(scopes),
        force: force,
      ),
    );
    return super.hydrateIssue(issue, scopes: scopes, force: force);
  }
}

class Ts766HydrationCall {
  const Ts766HydrationCall({
    required this.issueKey,
    required this.scopes,
    required this.force,
  });

  final String issueKey;
  final Set<IssueHydrationScope> scopes;
  final bool force;
}

class _Ts766MutableProvider implements TrackStateProviderAdapter {
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

  _Ts766MutableProvider() {
    _rebuildFiles();
  }

  final Map<String, _Ts766IssueRecord> _issues = <String, _Ts766IssueRecord>{
    Ts766AttachmentRefreshRepository.issueCKey: const _Ts766IssueRecord(
      key: Ts766AttachmentRefreshRepository.issueCKey,
      summary: Ts766AttachmentRefreshRepository.issueCSummary,
      issueTypeId: 'story',
      statusId: 'todo',
      priorityId: 'high',
      updated: '2026-05-15T14:10:00Z',
      description:
          'Issue C stays selected while hosted workspace sync publishes an attachments-only refresh.',
      comments: <String>[],
      labels: <String>['attachments', 'board'],
    ),
  };

  final Map<String, String> _textFiles = <String, String>{};
  final Map<String, Uint8List> _attachmentFiles = <String, Uint8List>{};
  RepositorySyncCheck? _queuedCheck;
  int _revision = 1;
  String _currentAttachmentDisplayName =
      Ts766AttachmentRefreshRepository.initialAttachmentName;
  String _currentAttachmentCreatedAt = '2026-05-15T14:10:00Z';
  Uint8List _currentAttachmentBytes = Uint8List.fromList(
    List<int>.generate(32, (index) => index + 1),
  );

  String get currentAttachmentDisplayName => _currentAttachmentDisplayName;

  String issueDescription(String key) => _issue(key).description;

  Future<void> emitAttachmentsOnlyRefresh() async {
    _currentAttachmentDisplayName =
        Ts766AttachmentRefreshRepository.updatedAttachmentName;
    _currentAttachmentCreatedAt = '2026-05-15T14:20:00Z';
    _currentAttachmentBytes = Uint8List.fromList(
      List<int>.generate(64, (index) => 255 - index),
    );
    _rebuildFiles();
    _queueHostedRefresh(const <String>{
      Ts766AttachmentRefreshRepository.attachmentPath,
    });
  }

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
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
      const RepositoryUser(login: 'ts766-user', displayName: 'TS-766 User');

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryPermission> getPermission() async => _permission;

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async => [
    for (final path in <String>{..._textFiles.keys, ..._attachmentFiles.keys})
      RepositoryTreeEntry(path: path, type: 'blob'),
  ];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    final bytes = _attachmentFiles[path];
    if (bytes == null) {
      throw TrackStateProviderException(
        'Missing TS-766 attachment fixture for $path.',
      );
    }
    return RepositoryAttachment(
      path: path,
      bytes: bytes,
      revision: _currentRevision,
      declaredSizeBytes: bytes.length,
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-766 does not require attachment uploads.',
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _textFiles[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-766 fixture for $path.');
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
      'TS-766 should not create commits.',
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
    repositoryRevision: 'ts766-revision-$_revision',
    sessionRevision: 'ts766-session',
    connectionState: ProviderConnectionState.connected,
    permission: _permission,
  );

  String get _currentRevision => 'ts766-r$_revision';

  _Ts766IssueRecord _issue(String key) {
    final issue = _issues[key];
    if (issue == null) {
      throw StateError('Missing TS-766 issue state for $key.');
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
        for (final issue in _issues.values)
          '${issue.key}/main.md': _issueMarkdown(issue),
        Ts766AttachmentRefreshRepository.attachmentMetadataPath:
            _attachmentsMetadataJson(),
      });
    _attachmentFiles
      ..clear()
      ..[Ts766AttachmentRefreshRepository.attachmentPath] =
          _currentAttachmentBytes;
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

  String _issueMarkdown(_Ts766IssueRecord issue) {
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

  String _attachmentsMetadataJson() {
    final metadata = <Map<String, Object?>>[
      <String, Object?>{
        'id': Ts766AttachmentRefreshRepository.attachmentPath,
        'name': _currentAttachmentDisplayName,
        'mediaType': _currentAttachmentDisplayName.endsWith('.pdf')
            ? 'application/pdf'
            : 'image/png',
        'sizeBytes': _currentAttachmentBytes.length,
        'author': 'Taylor QA',
        'createdAt': _currentAttachmentCreatedAt,
        'storagePath': Ts766AttachmentRefreshRepository.attachmentPath,
        'revisionOrOid': _currentRevision,
        'storageBackend': AttachmentStorageMode.repositoryPath.persistedValue,
        'repositoryPath': Ts766AttachmentRefreshRepository.attachmentPath,
      },
    ];
    return '${const JsonEncoder.withIndent('  ').convert(metadata)}\n';
  }
}

class _Ts766IssueRecord {
  const _Ts766IssueRecord({
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
}

const String _projectJson = '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config",
  "attachmentStorage": {
    "mode": "repository-path"
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
  {"id": "summary", "name": "Summary", "type": "string", "required": true},
  {"id": "description", "name": "Description", "type": "markdown", "required": false},
  {"id": "acceptanceCriteria", "name": "Acceptance Criteria", "type": "markdown", "required": false},
  {"id": "priority", "name": "Priority", "type": "option", "required": false},
  {"id": "assignee", "name": "Assignee", "type": "user", "required": false},
  {"id": "labels", "name": "Labels", "type": "array", "required": false}
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
