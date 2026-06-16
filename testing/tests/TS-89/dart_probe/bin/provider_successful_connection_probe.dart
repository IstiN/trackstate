import 'dart:convert';
import 'dart:typed_data';

import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

class SuccessfulTrackStateProviderAdapter implements TrackStateProviderAdapter {
  RepositoryConnection? _connection;
  int authenticateAttempts = 0;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/authorized-repository';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    _connection = connection;
    authenticateAttempts += 1;
    return const RepositoryUser(
      login: 'connected-user',
      displayName: 'Connected User',
    );
  }

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async => RepositoryAttachment(path: path, bytes: Uint8List(0));

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async => RepositoryTextFile(path: path, content: '');

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == 'main');

  @override
  Future<RepositoryPermission> getPermission() async => const RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: true,
    canCreateBranch: true,
    canManageAttachments: true,
    canCheckCollaborators: true,
  );

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      const [];

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => RepositoryCommitResult(
    branch: request.branch,
    message: request.message,
    revision: 'mock-revision',
  );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<String> resolveWriteBranch() async => _connection?.branch ?? dataRef;

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => RepositoryAttachmentWriteResult(
    path: request.path,
    branch: request.branch,
    revision: 'mock-revision',
  );

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => RepositoryWriteResult(
    path: request.path,
    branch: request.branch,
    revision: 'mock-revision',
  );
}

Map<String, Object?>? serializeSession(ProviderSession? session) {
  if (session == null) {
    return null;
  }
  return {
    'providerType': session.providerType.toString(),
    'connectionState': session.connectionState.toString(),
    'resolvedUserIdentity': session.resolvedUserIdentity,
    'canRead': session.canRead,
    'canWrite': session.canWrite,
    'canCreateBranch': session.canCreateBranch,
    'canManageAttachments': session.canManageAttachments,
    'canCheckCollaborators': session.canCheckCollaborators,
  };
}

Future<void> main() async {
  final provider = SuccessfulTrackStateProviderAdapter();
  final repository = ProviderBackedTrackStateRepository(provider: provider);

  final user = await repository.connect(
    const RepositoryConnection(
      repository: 'mock/authorized-repository',
      branch: 'main',
      token: 'mock-token',
    ),
  );

  print(
    jsonEncode({
      'authenticateAttempts': provider.authenticateAttempts,
      'connectedUser': user.login,
      'session': serializeSession(repository.session),
    }),
  );
}
