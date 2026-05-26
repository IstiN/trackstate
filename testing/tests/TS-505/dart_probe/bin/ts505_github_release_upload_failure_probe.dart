import 'dart:convert';
import 'dart:typed_data';

import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

const String _repositoryName = 'mock/demo';
const String _branch = 'main';
const String _issueKey = 'DEMO-2';
const String _issuePath = 'DEMO/DEMO-1/DEMO-2';
const String _issueStoragePath = '$_issuePath/main.md';
const String _manifestPath = '$_issuePath/attachments.json';
const String _failedAttachmentName = 'release-failure.pdf';
const String _existingAttachmentName = 'architecture-notes.txt';
const String _existingAttachmentPath = '$_issuePath/attachments/$_existingAttachmentName';
const String _tagPrefix = 'ts505-';
const String _expectedErrorBody = '{"message":"Internal Server Error"}';

Future<void> main() async {
  final result = <String, Object?>{'status': 'failed'};

  try {
    final manifestBefore = '${jsonEncode(<Map<String, Object?>>[
      <String, Object?>{
        'id': _existingAttachmentPath,
        'name': _existingAttachmentName,
        'mediaType': 'text/plain',
        'sizeBytes': 41,
        'author': 'seed-user',
        'createdAt': '2026-05-12T00:00:00Z',
        'storagePath': _existingAttachmentPath,
        'revisionOrOid': 'blob-seed-1',
        'storageBackend': AttachmentStorageMode.repositoryPath.persistedValue,
        'repositoryPath': _existingAttachmentPath,
      },
    ])}\n';
    final provider = _ScriptedReleaseUploadFailureProvider(
      manifestPath: _manifestPath,
      manifestContent: manifestBefore,
    );
    final repository = ProviderBackedTrackStateRepository(provider: provider);
    final issue = _seedIssue();
    final snapshot = TrackerSnapshot(project: _projectConfig, issues: <TrackStateIssue>[issue]);

    await repository.connect(
      const RepositoryConnection(
        repository: _repositoryName,
        branch: _branch,
        token: 'mock-token',
      ),
    );
    repository.replaceCachedState(
      snapshot: snapshot,
      tree: const <RepositoryTreeEntry>[
        RepositoryTreeEntry(path: _manifestPath, type: 'blob'),
      ],
    );

    final uploadBytes = Uint8List.fromList(
      utf8.encode('%PDF-1.4\nTS-505 synthetic release upload payload\n'),
    );
    final uploadOutcome = <String, Object?>{'status': 'unknown'};

    try {
      await repository.uploadIssueAttachment(
        issue: issue,
        name: _failedAttachmentName,
        bytes: uploadBytes,
      );
      uploadOutcome['status'] = 'success';
    } catch (error, stackTrace) {
      uploadOutcome['status'] = 'error';
      uploadOutcome['message'] = error.toString();
      uploadOutcome['stackTrace'] = stackTrace.toString();
    }

    result.addAll(<String, Object?>{
      'status': 'passed',
      'ticket': 'TS-505',
      'repository': _repositoryName,
      'branch': _branch,
      'issueKey': _issueKey,
      'issuePath': _issuePath,
      'manifestPath': _manifestPath,
      'failedAttachmentName': _failedAttachmentName,
      'existingAttachmentName': _existingAttachmentName,
      'manifestBefore': manifestBefore,
      'manifestAfter': provider.manifestContent,
      'metadataReadCalls': provider.metadataReadCalls,
      'metadataWriteCalls': provider.metadataWriteCalls,
      'releaseWriteCalls': provider.releaseWriteCalls,
      'releaseReadCalls': provider.releaseReadCalls,
      'releaseDeleteCalls': provider.releaseDeleteCalls,
      'uploadOutcome': uploadOutcome,
      'providerSession': _serializeSession(repository.session),
    });
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}

TrackStateIssue _seedIssue() => const TrackStateIssue(
  key: _issueKey,
  project: 'DEMO',
  issueType: IssueType.story,
  issueTypeId: 'story',
  status: IssueStatus.todo,
  statusId: 'todo',
  priority: IssuePriority.medium,
  priorityId: 'medium',
  summary: 'Seeded TS-505 issue',
  description: 'Synthetic issue used to verify failed github-releases uploads.',
  assignee: 'release-tester',
  reporter: 'release-tester',
  labels: <String>[],
  components: <String>[],
  fixVersionIds: <String>[],
  watchers: <String>[],
  customFields: <String, Object?>{},
  parentKey: 'DEMO-1',
  epicKey: null,
  parentPath: 'DEMO/DEMO-1',
  epicPath: null,
  progress: 0,
  updatedLabel: 'just now',
  acceptanceCriteria: <String>[],
  comments: <IssueComment>[],
  links: <IssueLink>[],
  attachments: <IssueAttachment>[
    IssueAttachment(
      id: _existingAttachmentPath,
      name: _existingAttachmentName,
      mediaType: 'text/plain',
      sizeBytes: 41,
      author: 'seed-user',
      createdAt: '2026-05-12T00:00:00Z',
      storagePath: _existingAttachmentPath,
      revisionOrOid: 'blob-seed-1',
      storageBackend: AttachmentStorageMode.repositoryPath,
      repositoryPath: _existingAttachmentPath,
    ),
  ],
  isArchived: false,
  hasDetailLoaded: true,
  hasCommentsLoaded: true,
  hasAttachmentsLoaded: true,
  storagePath: _issueStoragePath,
  rawMarkdown: '# Summary\n\nSeeded TS-505 issue\n',
);

const ProjectConfig _projectConfig = ProjectConfig(
  key: 'DEMO',
  name: 'TrackState Demo',
  repository: _repositoryName,
  branch: _branch,
  defaultLocale: 'en',
  issueTypeDefinitions: <TrackStateConfigEntry>[],
  statusDefinitions: <TrackStateConfigEntry>[],
  fieldDefinitions: <TrackStateFieldDefinition>[],
  attachmentStorage: ProjectAttachmentStorageSettings(
    mode: AttachmentStorageMode.githubReleases,
    githubReleases: GitHubReleasesAttachmentStorageSettings(tagPrefix: _tagPrefix),
  ),
);

Map<String, Object?>? _serializeSession(ProviderSession? session) {
  if (session == null) {
    return null;
  }
  return <String, Object?>{
    'providerType': session.providerType.toString(),
    'connectionState': session.connectionState.toString(),
    'resolvedUserIdentity': session.resolvedUserIdentity,
    'canRead': session.canRead,
    'canWrite': session.canWrite,
    'supportsReleaseAttachmentWrites': session.supportsReleaseAttachmentWrites,
  };
}

class _InMemoryTextFile {
  _InMemoryTextFile({
    required this.content,
    required this.revision,
  });

  String content;
  String revision;
}

class _ScriptedReleaseUploadFailureProvider
    implements TrackStateProviderAdapter, RepositoryReleaseAttachmentStore {
  _ScriptedReleaseUploadFailureProvider({
    required String manifestPath,
    required String manifestContent,
  }) : _manifestPath = manifestPath,
       _textFiles = <String, _InMemoryTextFile>{
         manifestPath: _InMemoryTextFile(
           content: manifestContent,
           revision: 'manifest-revision-1',
         ),
       };

  final String _manifestPath;
  final Map<String, _InMemoryTextFile> _textFiles;
  final List<Map<String, Object?>> metadataReadCalls = <Map<String, Object?>>[];
  final List<Map<String, Object?>> metadataWriteCalls = <Map<String, Object?>>[];
  final List<Map<String, Object?>> releaseWriteCalls = <Map<String, Object?>>[];
  final List<Map<String, Object?>> releaseReadCalls = <Map<String, Object?>>[];
  final List<Map<String, Object?>> releaseDeleteCalls = <Map<String, Object?>>[];

  String get manifestContent => _textFiles[_manifestPath]?.content ?? '';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => _repositoryName;

  @override
  String get dataRef => _branch;

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(
        login: 'release-tester',
        displayName: 'Release Tester',
        accountId: '505',
      );

  @override
  Future<RepositoryPermission> getPermission() async =>
      const RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        supportsReleaseAttachmentWrites: true,
        canCheckCollaborators: false,
      );

  @override
  Future<String> resolveWriteBranch() async => _branch;

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == _branch);

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    metadataReadCalls.add(<String, Object?>{'path': path, 'ref': ref});
    final file = _textFiles[path];
    if (file == null) {
      throw TrackStateProviderException('Missing text fixture for $path.');
    }
    return RepositoryTextFile(
      path: path,
      content: file.content,
      revision: file.revision,
    );
  }

  @override
  Future<RepositoryWriteResult> writeTextFile(RepositoryWriteRequest request) async {
    metadataWriteCalls.add(<String, Object?>{
      'path': request.path,
      'branch': request.branch,
      'message': request.message,
      'expectedRevision': request.expectedRevision,
      'content': request.content,
    });
    final nextRevision = 'manifest-revision-${metadataWriteCalls.length + 1}';
    _textFiles[request.path] = _InMemoryTextFile(
      content: request.content,
      revision: nextRevision,
    );
    return RepositoryWriteResult(
      path: request.path,
      branch: request.branch,
      revision: nextRevision,
    );
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => RepositoryCommitResult(
    branch: request.branch,
    message: request.message,
    revision: 'commit-1',
  );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      const <RepositoryTreeEntry>[];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    throw TrackStateProviderException('No attachment fixture exists for $path.');
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => throw const TrackStateProviderException(
    'TS-505 does not exercise repository-path attachment writes.',
  );

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<RepositoryAttachment> readReleaseAttachment(
    RepositoryReleaseAttachmentReadRequest request,
  ) async {
    releaseReadCalls.add(<String, Object?>{
      'releaseTag': request.releaseTag,
      'assetName': request.assetName,
      'assetId': request.assetId,
    });
    throw TrackStateProviderException(
      'No release attachment fixture exists for ${request.assetName}.',
    );
  }

  @override
  Future<RepositoryReleaseAttachmentWriteResult> writeReleaseAttachment(
    RepositoryReleaseAttachmentWriteRequest request,
  ) async {
    releaseWriteCalls.add(<String, Object?>{
      'issueKey': request.issueKey,
      'releaseTag': request.releaseTag,
      'releaseTitle': request.releaseTitle,
      'assetName': request.assetName,
      'mediaType': request.mediaType,
      'branch': request.branch,
      'bytesLength': request.bytes.length,
      'allowedAssetNames': request.allowedAssetNames.toList()..sort(),
    });
    throw TrackStateProviderException(
      'Could not upload GitHub release asset ${request.assetName} to '
      '${request.releaseTag} (500): $_expectedErrorBody',
    );
  }

  @override
  Future<void> deleteReleaseAttachment(
    RepositoryReleaseAttachmentDeleteRequest request,
  ) async {
    releaseDeleteCalls.add(<String, Object?>{
      'releaseTag': request.releaseTag,
      'assetId': request.assetId,
      'assetName': request.assetName,
    });
  }
}
