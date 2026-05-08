import 'dart:convert';
import 'dart:typed_data';

import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

class RetryableTrackStateProviderAdapter implements TrackStateProviderAdapter {
  RetryableTrackStateProviderAdapter({
    required RepositoryPermission connectedPermission,
    required RepositoryUser authenticatedUser,
  }) : _connectedPermission = connectedPermission,
       _authenticatedUser = authenticatedUser;

  int authenticateAttempts = 0;
  RepositoryConnection? _connection;
  bool _shouldFailAuthentication = true;
  RepositoryPermission _permission = const RepositoryPermission(
    canRead: false,
    canWrite: false,
    isAdmin: false,
    canCreateBranch: false,
    canManageAttachments: false,
    canCheckCollaborators: false,
  );
  final RepositoryPermission _connectedPermission;
  final RepositoryUser _authenticatedUser;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/retry-repository';

  void allowSuccessfulAuthentication() {
    _shouldFailAuthentication = false;
    _permission = _connectedPermission;
  }

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    authenticateAttempts += 1;
    _connection = connection;
    if (_shouldFailAuthentication) {
      throw const TrackStateProviderException(
        'Unauthorized: simulated connection failure for TS-90.',
      );
    }
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
    final provider = RetryableTrackStateProviderAdapter(
      connectedPermission: const RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: true,
        canCreateBranch: true,
        canManageAttachments: true,
        canCheckCollaborators: true,
      ),
      authenticatedUser: const RepositoryUser(
        login: 'retry-user',
        displayName: 'Retry User',
      ),
    );
    final repository = ProviderBackedTrackStateRepository(provider: provider);
    const connection = RepositoryConnection(
      repository: 'mock/retry-repository',
      branch: 'main',
      token: 'mock-token',
    );

    Object? firstConnectError;
    StackTrace? firstConnectStackTrace;
    try {
      await repository.connect(connection);
    } catch (error, stackTrace) {
      firstConnectError = error;
      firstConnectStackTrace = stackTrace;
    }

    if (firstConnectError == null) {
      throw StateError(
        'Step 1 failed: the initial connection attempt unexpectedly succeeded instead of surfacing the unauthorized failure state.',
      );
    }

    final failedSession = repository.session;
    if (failedSession == null) {
      throw StateError(
        'Step 2 failed: repository.session was null after the failed connection attempt, so a client could not observe the restricted failure state before retrying.',
      );
    }
    final failedSessionSnapshot = _serializeSession(failedSession);
    final authenticateAttemptsAfterFailure = provider.authenticateAttempts;

    provider.allowSuccessfulAuthentication();
    final connectedUser = await repository.connect(connection);

    final recoveredSession = repository.session;
    if (recoveredSession == null) {
      throw StateError(
        'Step 5 failed: repository.session was null after the successful retry, so a client could not observe the recovered connected state.',
      );
    }
    final recoveredSessionSnapshot = _serializeSession(recoveredSession);

    result['firstConnectError'] = firstConnectError.toString();
    result['firstConnectStackTrace'] = firstConnectStackTrace?.toString();
    result['authenticateAttemptsAfterFailure'] = authenticateAttemptsAfterFailure;
    result['failedSession'] = failedSessionSnapshot;
    result['authenticateAttemptsAfterRetry'] = provider.authenticateAttempts;
    result['connectedUserLogin'] = connectedUser.login;
    result['recoveredSession'] = recoveredSessionSnapshot;
    result['status'] = 'passed';
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}
