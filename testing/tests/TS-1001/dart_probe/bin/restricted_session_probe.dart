import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

class HangingRestrictedProviderAdapter implements TrackStateProviderAdapter {
  HangingRestrictedProviderAdapter();

  final Completer<void> _authenticationGate = Completer<void>();
  RepositoryConnection? _connection;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/repository';

  void releaseAuthenticationFailure() {
    if (!_authenticationGate.isCompleted) {
      _authenticationGate.complete();
    }
  }

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    _connection = connection;
    await _authenticationGate.future;
    throw StateError(
      'Intentional probe shutdown after observing the unresolved auth session.',
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
    canRead: false,
    canWrite: false,
    isAdmin: false,
    canCreateBranch: false,
  );

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async => const [];

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
    final provider = HangingRestrictedProviderAdapter();
    final repository = ProviderBackedTrackStateRepository(provider: provider);

    final connectFuture = repository.connect(
      const RepositoryConnection(
        repository: 'mock/repository',
        branch: 'main',
        token: 'mock-token',
      ),
    );

    await Future<void>.delayed(Duration.zero);

    final session = repository.session;
    result['session'] = _serializeSession(session);
    if (session == null) {
      throw StateError(
        'The unresolved auth probe did not expose repository.session.',
      );
    }
    if (session.connectionState != ProviderConnectionState.connecting) {
      throw StateError(
        'Expected ProviderConnectionState.connecting while auth remained unresolved. '
        'Observed ${session.connectionState}.',
      );
    }
    if (session.canWrite) {
      throw StateError(
        'Expected canWrite=false while auth remained unresolved.',
      );
    }
    if (session.canCreateBranch) {
      throw StateError(
        'Expected canCreateBranch=false while auth remained unresolved.',
      );
    }

    provider.releaseAuthenticationFailure();
    await connectFuture.catchError((Object _) {});
    result['status'] = 'passed';
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}
