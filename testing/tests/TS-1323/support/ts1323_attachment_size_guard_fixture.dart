import 'dart:convert';
import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts1323AttachmentSizeGuardFixture {
  Ts1323AttachmentSizeGuardFixture._({
    required this.repository,
    required this.provider,
    required this.issue,
    required this.sourceBytes,
  });

  static const String projectKey = 'DEMO';
  static const String issueKey = 'DEMO-1';
  static const String issuePath = 'DEMO/DEMO-1/main.md';
  static const String metadataPath = 'DEMO/DEMO-1/attachments.json';
  static const String attachmentName = 'size-guard-check.txt';

  final ProviderBackedTrackStateRepository repository;
  final _TruncatingAttachmentProvider provider;
  final TrackStateIssue issue;
  final Uint8List sourceBytes;

  static Future<Ts1323AttachmentSizeGuardFixture> create() async {
    final provider = _TruncatingAttachmentProvider();
    final repository = ProviderBackedTrackStateRepository(
      provider: provider,
      usesLocalPersistence: true,
    );
    final snapshot = await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(
        repository: 'mock/demo',
        branch: 'main',
        token: 'demo-token',
      ),
    );
    return Ts1323AttachmentSizeGuardFixture._(
      repository: repository,
      provider: provider,
      issue: snapshot.issues.single,
      sourceBytes: Uint8List.fromList(
        utf8.encode('source payload for the size guard check'),
      ),
    );
  }

  Future<Ts1323AttachmentUploadRun> runUpload() async {
    try {
      final updatedIssue = await repository.uploadIssueAttachment(
        issue: issue,
        name: attachmentName,
        bytes: sourceBytes,
      );
      return Ts1323AttachmentUploadRun(
        updatedIssue: updatedIssue,
        sourceBytes: sourceBytes,
        provider: provider,
      );
    } catch (error, stackTrace) {
      return Ts1323AttachmentUploadRun(
        error: error,
        stackTrace: stackTrace,
        sourceBytes: sourceBytes,
        provider: provider,
      );
    }
  }
}

class Ts1323AttachmentUploadRun {
  Ts1323AttachmentUploadRun({
    this.updatedIssue,
    this.error,
    this.stackTrace,
    required this.sourceBytes,
    required this.provider,
  });

  final TrackStateIssue? updatedIssue;
  final Object? error;
  final StackTrace? stackTrace;
  final Uint8List sourceBytes;
  final _TruncatingAttachmentProvider provider;

  IssueAttachment? get uploadedAttachment =>
      (() {
        for (final attachment in updatedIssue?.attachments ?? const []) {
          if (attachment.name == Ts1323AttachmentSizeGuardFixture.attachmentName) {
            return attachment;
          }
        }
        return null;
      })();

  Map<String, Object?>? get metadataJson {
    final content = provider.files[Ts1323AttachmentSizeGuardFixture.metadataPath];
    if (content == null) {
      return null;
    }
    final decoded = jsonDecode(content);
    if (decoded is! List || decoded.isEmpty) {
      return null;
    }
    final first = decoded.first;
    return first is Map<String, Object?> ? first : null;
  }

  int? get storedSizeBytes => provider.storedAttachmentBytes.length;

  int get metadataWriteCount => provider.metadataWriteCount;

  int get attachmentWriteCount => provider.attachmentWriteCount;

  String get storedSizeLabel => '${storedSizeBytes ?? 0} bytes';
}

class _TruncatingAttachmentProvider implements TrackStateProviderAdapter {
  _TruncatingAttachmentProvider() {
    _files.addAll(<String, String>{
      'project.json': '''
{
  "key": "DEMO",
  "name": "Demo Project",
  "defaultLocale": "en",
  "issueKeyPattern": "DEMO-{number}",
  "dataModel": "nested-tree",
  "configPath": "config"
}
''',
      'config/statuses.json': '''
[
  {"id": "todo", "name": "To Do", "category": "new"}
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
  {"id": "priority", "name": "Priority", "type": "option", "required": false},
  {"id": "assignee", "name": "Assignee", "type": "user", "required": false},
  {"id": "labels", "name": "Labels", "type": "array", "required": false}
]
''',
      'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: Story
status: To Do
priority: Medium
summary: Size guard upload fixture
assignee: tester
reporter: tester
updated: 2026-06-02T00:00:00Z
---

# Description

Seed issue for the upload size guard regression test.
''',
    });
  }

  final Map<String, String> _files = <String, String>{};
  final Map<String, Uint8List> _attachmentFiles = <String, Uint8List>{};
  RepositoryConnection? _connection;

  int attachmentWriteCount = 0;
  int metadataWriteCount = 0;

  Uint8List get storedAttachmentBytes =>
      _attachmentFiles.values.isEmpty
          ? Uint8List(0)
          : _attachmentFiles.values.first;

  Map<String, String> get files => _files;

  @override
  ProviderType get providerType => ProviderType.local;

  @override
  String get repositoryLabel => 'mock/demo';

  @override
  String get dataRef => 'main';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    _connection = connection;
    return const RepositoryUser(login: 'demo-user', displayName: 'Demo User');
  }

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryPermission> getPermission() async => const RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: false,
    canCreateBranch: true,
    canManageAttachments: true,
    attachmentUploadMode: AttachmentUploadMode.full,
    supportsReleaseAttachmentWrites: false,
    canCheckCollaborators: false,
  );

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async =>
      RepositorySyncCheck(
        state: RepositorySyncState(
          providerType: providerType,
          repositoryRevision: 'demo-revision',
          sessionRevision: '${_connection?.repository ?? 'mock/demo'}:${_connection?.branch ?? 'main'}',
          connectionState: ProviderConnectionState.connected,
          permission: await getPermission(),
        ),
      );

  @override
  Future<String> resolveWriteBranch() async => _connection?.branch ?? dataRef;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async => [
    for (final path in _files.keys) RepositoryTreeEntry(path: path, type: 'blob'),
    for (final path in _attachmentFiles.keys)
      RepositoryTreeEntry(path: path, type: 'blob'),
  ];

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
    if (content == null) {
      throw TrackStateProviderException('Missing fixture for $path.');
    }
    return RepositoryTextFile(path: path, content: content, revision: 'seed-revision');
  }

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    metadataWriteCount += 1;
    _files[request.path] = request.content;
    return RepositoryWriteResult(
      path: request.path,
      branch: request.branch,
      revision: 'metadata-sha',
    );
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async =>
      RepositoryCommitResult(
        branch: request.branch,
        message: request.message,
        revision: 'commit-sha',
      );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    final bytes = _attachmentFiles[path];
    if (bytes == null) {
      throw TrackStateProviderException('Missing attachment fixture for $path.');
    }
    return RepositoryAttachment(
      path: path,
      bytes: Uint8List.fromList(bytes),
      revision: 'attachment-sha',
      declaredSizeBytes: bytes.length,
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    attachmentWriteCount += 1;
    final truncatedLength = request.bytes.isEmpty ? 0 : request.bytes.length - 1;
    _attachmentFiles[request.path] = Uint8List.fromList(
      request.bytes.sublist(0, truncatedLength),
    );
    return RepositoryAttachmentWriteResult(
      path: request.path,
      branch: request.branch,
      revision: 'attachment-sha',
    );
  }

  @override
  Future<bool> isLfsTracked(String path) async => false;
}
