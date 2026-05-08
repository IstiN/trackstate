import 'dart:convert';
import 'dart:typed_data';

import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

class FakeTrackStateProviderAdapter implements TrackStateProviderAdapter {
  RepositoryConnection? _connection;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/repository';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    _connection = connection;
    return const RepositoryUser(login: 'mock-user', displayName: 'Mock User');
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
  Future<RepositoryPermission> getPermission() async =>
      const RepositoryPermission(canRead: true, canWrite: true, isAdmin: false);

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
  Future<String> resolveWriteBranch() async => _connection?.branch ?? 'main';

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

Future<void> main() async {
  final repository = ProviderBackedTrackStateRepository(
    provider: FakeTrackStateProviderAdapter(),
  );
  await repository.connect(
    const RepositoryConnection(
      repository: 'mock/repository',
      branch: 'main',
      token: 'mock-token',
    ),
  );

  final ProviderSession? session = repository.session;
  final activeSession =
      session ?? (throw StateError('Repository session was null after connect.'));

  print(
    jsonEncode({
      'providerType': activeSession.providerType.toString(),
      'connectionState': activeSession.connectionState.toString(),
      'resolvedUserIdentity': activeSession.resolvedUserIdentity.toString(),
      'canRead': activeSession.canRead,
      'canWrite': activeSession.canWrite,
      'canCreateBranch': activeSession.canCreateBranch,
      'canManageAttachments': activeSession.canManageAttachments,
      'canCheckCollaborators': activeSession.canCheckCollaborators,
    }),
  );
}
