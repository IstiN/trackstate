import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

class MutableTrackStateProviderAdapter implements TrackStateProviderAdapter {
  MutableTrackStateProviderAdapter({
    required RepositoryPermission permission,
    required RepositoryUser authenticatedUser,
  }) : _permission = permission,
       _authenticatedUser = authenticatedUser;

  final Completer<void> _authenticationGate = Completer<void>();
  RepositoryConnection? _connection;
  RepositoryPermission _permission;
  final RepositoryUser _authenticatedUser;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/repository';

  void updatePermission(RepositoryPermission permission) {
    _permission = permission;
  }

  void completeAuthentication() {
    if (!_authenticationGate.isCompleted) {
      _authenticationGate.complete();
    }
  }

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    _connection = connection;
    await _authenticationGate.future;
    return _authenticatedUser;
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
  Future<RepositoryPermission> getPermission() async => _permission;

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

Map<String, Object?>? _serializeSession(ProviderSession? session) {
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
  final result = <String, Object?>{'status': 'failed'};

  try {
    final provider = MutableTrackStateProviderAdapter(
      permission: const RepositoryPermission(
        canRead: true,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
      ),
      authenticatedUser: const RepositoryUser(
        login: 'sync-user',
        displayName: 'Session Sync User',
      ),
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

    final initialSession = repository.session;
    result['initialSession'] = _serializeSession(initialSession);
    if (initialSession == null) {
      throw StateError(
        'Step 2 failed: repository.session was null while the provider was still connecting, so product logic could not observe an in-progress session.',
      );
    }
    if (initialSession.connectionState != ProviderConnectionState.connecting) {
      throw StateError(
        'Step 2 failed: repository.session did not expose ProviderConnectionState.connecting before authentication completed. '
        'Observed ${initialSession.connectionState}.',
      );
    }
    if (initialSession.canCreateBranch) {
      throw StateError(
        'Step 2 failed: canCreateBranch was already true before the provider reported its connected/write-capable state.',
      );
    }

    provider.updatePermission(
      const RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
      ),
    );
    provider.completeAuthentication();

    await connectFuture;

    final finalSession = repository.session;
    result['finalSession'] = _serializeSession(finalSession);
    if (finalSession == null) {
      throw StateError(
        'Step 4 failed: repository.session was null after the provider transitioned to connected.',
      );
    }
    if (finalSession.connectionState != ProviderConnectionState.connected) {
      throw StateError(
        'Step 4 failed: repository.session did not update to ProviderConnectionState.connected after the provider transition. '
        'Observed ${finalSession.connectionState}.',
      );
    }
    if (!finalSession.canCreateBranch) {
      throw StateError(
        'Step 4 failed: repository.session did not reflect the provider update that enabled canCreateBranch.',
      );
    }

    result['status'] = 'passed';
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}
