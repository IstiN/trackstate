import 'dart:async';
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

  test(
    'provider-backed repository exposes a restricted session after connect fails',
    () async {
      final repository = ProviderBackedTrackStateRepository(
        provider: _FailingTrackStateProviderAdapter(),
      );

      await expectLater(
        () => repository.connect(
          const RepositoryConnection(
            repository: 'mock/repository',
            branch: 'main',
            token: 'mock-token',
          ),
        ),
        throwsA(isA<TrackStateProviderException>()),
      );

      final ProviderSession session =
          repository.session ??
          (throw StateError(
            'Expected a restricted provider session after connect fails.',
          ));

      expect(session.providerType, ProviderType.github);
      expect(session.connectionState, ProviderConnectionState.disconnected);
      expect(session.resolvedUserIdentity, 'mock/repository');
      expect(session.canRead, isFalse);
      expect(session.canWrite, isFalse);
      expect(session.canCreateBranch, isFalse);
      expect(session.canManageAttachments, isFalse);
      expect(session.canCheckCollaborators, isFalse);
    },
  );

  test(
    'provider-backed repository session reflects connecting and live permission updates',
    () async {
      final provider = _FakeTrackStateProviderAdapter(
        permission: const RepositoryPermission(
          canRead: true,
          canWrite: false,
          isAdmin: false,
          canCreateBranch: false,
          canManageAttachments: false,
          canCheckCollaborators: false,
        ),
        delayAuthentication: true,
      );
      final repository = ProviderBackedTrackStateRepository(provider: provider);

      final connectFuture = repository.connect(
        const RepositoryConnection(
          repository: 'mock/repository',
          branch: 'main',
          token: 'mock-token',
        ),
      );

      await Future<void>.delayed(Duration.zero);

      final ProviderSession initialSession =
          repository.session ??
          (throw StateError('Expected a provider session while connecting.'));

      expect(
        initialSession.connectionState,
        ProviderConnectionState.connecting,
      );
      expect(initialSession.resolvedUserIdentity, 'mock/repository');
      expect(initialSession.canRead, isTrue);
      expect(initialSession.canWrite, isFalse);
      expect(initialSession.canCreateBranch, isFalse);
      expect(initialSession.canManageAttachments, isFalse);
      expect(initialSession.canCheckCollaborators, isFalse);

      provider.updatePermission(
        const RepositoryPermission(
          canRead: true,
          canWrite: true,
          isAdmin: false,
          canCreateBranch: true,
          canManageAttachments: true,
          canCheckCollaborators: false,
        ),
      );
      provider.completeAuthentication();
      await connectFuture;

      final ProviderSession finalSession =
          repository.session ??
          (throw StateError('Expected a provider session after connect.'));

      expect(finalSession.connectionState, ProviderConnectionState.connected);
      expect(finalSession.resolvedUserIdentity, 'mock-user');
      expect(finalSession.canRead, isTrue);
      expect(finalSession.canWrite, isTrue);
      expect(finalSession.canCreateBranch, isTrue);
      expect(finalSession.canManageAttachments, isTrue);
      expect(finalSession.canCheckCollaborators, isFalse);
    },
  );

  test(
    'provider-backed repository keeps captured session references synchronized',
    () async {
      final provider = _FakeTrackStateProviderAdapter(
        permission: const RepositoryPermission(
          canRead: true,
          canWrite: false,
          isAdmin: false,
          canCreateBranch: false,
          canManageAttachments: false,
          canCheckCollaborators: false,
        ),
        delayAuthentication: true,
      );
      final repository = ProviderBackedTrackStateRepository(provider: provider);

      final connectFuture = repository.connect(
        const RepositoryConnection(
          repository: 'mock/repository',
          branch: 'main',
          token: 'mock-token',
        ),
      );

      await Future<void>.delayed(Duration.zero);

      final ProviderSession capturedSession =
          repository.session ??
          (throw StateError('Expected a provider session while connecting.'));

      expect(
        capturedSession.connectionState,
        ProviderConnectionState.connecting,
      );
      expect(capturedSession.resolvedUserIdentity, 'mock/repository');
      expect(capturedSession.canCreateBranch, isFalse);

      provider.updatePermission(
        const RepositoryPermission(
          canRead: true,
          canWrite: true,
          isAdmin: false,
          canCreateBranch: true,
          canManageAttachments: true,
          canCheckCollaborators: false,
        ),
      );
      provider.completeAuthentication();
      await connectFuture;

      final ProviderSession latestSession =
          repository.session ??
          (throw StateError('Expected a provider session after connect.'));

      expect(identical(capturedSession, latestSession), isTrue);
      expect(
        capturedSession.connectionState,
        ProviderConnectionState.connected,
      );
      expect(capturedSession.resolvedUserIdentity, 'mock-user');
      expect(capturedSession.canCreateBranch, isTrue);
      expect(capturedSession.canManageAttachments, isTrue);
    },
  );
}

class _FakeTrackStateProviderAdapter implements TrackStateProviderAdapter {
  _FakeTrackStateProviderAdapter({
    required RepositoryPermission permission,
    this.delayAuthentication = false,
  }) : _permission = permission;

  final bool delayAuthentication;
  final Completer<void> _authenticationGate = Completer<void>();
  RepositoryPermission _permission;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/repository';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    if (delayAuthentication) {
      await _authenticationGate.future;
    }
    return const RepositoryUser(login: 'mock-user', displayName: 'Mock User');
  }

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
  Future<RepositoryPermission> getPermission() async => _permission;

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

  void updatePermission(RepositoryPermission permission) {
    _permission = permission;
  }

  void completeAuthentication() {
    if (!_authenticationGate.isCompleted) {
      _authenticationGate.complete();
    }
  }
}

class _FailingTrackStateProviderAdapter implements TrackStateProviderAdapter {
  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/repository';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    throw const TrackStateProviderException('Unauthorized');
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => throw UnimplementedError();

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == 'main');

  @override
  Future<RepositoryPermission> getPermission() async =>
      const RepositoryPermission(
        canRead: false,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
        canManageAttachments: false,
        canCheckCollaborators: false,
      );

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
  ) async => throw UnimplementedError();

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => throw UnimplementedError();
}
