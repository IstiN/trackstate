import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'provider-backed repository exposes a neutral provider session contract after connect',
    () async {
      final repository = ProviderBackedTrackStateRepository(
        provider: _FakeTrackStateProviderAdapter(
          permission: const RepositoryPermission(
            canRead: true,
            canWrite: true,
            isAdmin: false,
            canCreateBranch: true,
            canManageAttachments: true,
            canCheckCollaborators: false,
          ),
        ),
      );

      await repository.connect(
        const RepositoryConnection(
          repository: 'mock/repository',
          branch: 'main',
          token: 'mock-token',
        ),
      );

      final ProviderSession session =
          repository.session ??
          (throw StateError('Expected a provider session after connect.'));

      expect(session.providerType, ProviderType.github);
      expect(session.connectionState, ProviderConnectionState.connected);
      expect(session.resolvedUserIdentity, 'mock-user');
      expect(session.canRead, isTrue);
      expect(session.canWrite, isTrue);
      expect(session.canCreateBranch, isTrue);
      expect(session.canManageAttachments, isTrue);
      expect(session.canCheckCollaborators, isFalse);
    },
  );
}

class _FakeTrackStateProviderAdapter implements TrackStateProviderAdapter {
  _FakeTrackStateProviderAdapter({required this.permission});

  final RepositoryPermission permission;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/repository';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'mock-user', displayName: 'Mock User');

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => RepositoryCommitResult(
    branch: request.branch,
    message: request.message,
    revision: 'mock-revision',
  );

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == 'main');

  @override
  Future<RepositoryPermission> getPermission() async => permission;

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      const [];

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
  Future<String> resolveWriteBranch() async => 'main';

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
