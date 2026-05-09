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

  Completer<void> _authenticationGate = Completer<void>();
  RepositoryConnection? _connection;
  RepositoryPermission _permission;
  RepositoryUser _authenticatedUser;
  Object? _authenticationFailure;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/repository';

  void updateAuthenticatedUser(RepositoryUser authenticatedUser) {
    _authenticatedUser = authenticatedUser;
  }

  void updatePermission(RepositoryPermission permission) {
    _permission = permission;
  }

  void setAuthenticationFailure(Object? failure) {
    _authenticationFailure = failure;
  }

  void resetAuthenticationGate() {
    if (_authenticationGate.isCompleted) {
      _authenticationGate = Completer<void>();
    }
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
    if (_authenticationFailure != null) {
      throw StateError(_authenticationFailure.toString());
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

void _expect(
  bool condition,
  String failureMessage,
  List<String> failures,
) {
  if (!condition) {
    failures.add(failureMessage);
  }
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
        login: 'reactive-user',
        displayName: 'Reactive Session User',
      ),
    );
    final repository = ProviderBackedTrackStateRepository(provider: provider);
    final failures = <String>[];
    const connection = RepositoryConnection(
      repository: 'mock/repository',
      branch: 'main',
      token: 'mock-token',
    );

    final firstConnectFuture = repository.connect(connection);
    await Future<void>.delayed(Duration.zero);

    final sessionReference = repository.session;
    result['initialSessionReference'] = _serializeSession(sessionReference);
    if (sessionReference == null) {
      throw StateError(
        'Step 2 failed: repository.session was null while the provider was still connecting, so a client could not hold a live session reference.',
      );
    }

    _expect(
      sessionReference.connectionState == ProviderConnectionState.connecting,
      'Step 2 failed: the captured session reference did not expose ProviderConnectionState.connecting before the first authentication completed. '
      'Observed ${sessionReference.connectionState}.',
      failures,
    );
    _expect(
      sessionReference.canCreateBranch == false,
      'Step 2 failed: the captured session reference already allowed branch creation before the provider reported its first connected/write-capable state.',
      failures,
    );

    provider.updatePermission(
      const RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
      ),
    );
    provider.updateAuthenticatedUser(
      const RepositoryUser(
        login: 'reactive-user',
        displayName: 'Reactive Session User',
      ),
    );
    provider.setAuthenticationFailure(null);
    provider.completeAuthentication();
    await firstConnectFuture;

    final firstConnectedSession = repository.session;
    result['firstConnectedSessionReference'] = _serializeSession(sessionReference);
    result['firstConnectedRepositorySession'] = _serializeSession(
      firstConnectedSession,
    );
    result['sameInstanceAfterFirstConnection'] = identical(
      sessionReference,
      firstConnectedSession,
    );

    _expect(
      firstConnectedSession != null,
      'Step 4 failed: repository.session was null after the first successful connection.',
      failures,
    );
    if (firstConnectedSession != null) {
      _expect(
        firstConnectedSession.connectionState ==
            ProviderConnectionState.connected,
        'Step 4 failed: a fresh repository.session getter did not expose ProviderConnectionState.connected after the first transition. '
        'Observed ${firstConnectedSession.connectionState}.',
        failures,
      );
      _expect(
        firstConnectedSession.resolvedUserIdentity == 'reactive-user',
        'Step 4 failed: a fresh repository.session getter did not expose the first connected identity. '
        'Observed ${firstConnectedSession.resolvedUserIdentity}.',
        failures,
      );
      _expect(
        firstConnectedSession.canCreateBranch,
        'Step 4 failed: a fresh repository.session getter did not reflect canCreateBranch=true after the first transition.',
        failures,
      );
    }
    _expect(
      sessionReference.connectionState == ProviderConnectionState.connected,
      'Step 4 failed: the previously obtained session reference did not update to ProviderConnectionState.connected after the first transition. '
      'Observed ${sessionReference.connectionState}.',
      failures,
    );
    _expect(
      sessionReference.resolvedUserIdentity == 'reactive-user',
      'Step 4 failed: the previously obtained session reference did not expose the first connected identity. '
      'Observed ${sessionReference.resolvedUserIdentity}.',
      failures,
    );
    _expect(
      sessionReference.canCreateBranch,
      'Step 4 failed: the previously obtained session reference did not update canCreateBranch to true after the first transition.',
      failures,
    );

    provider.resetAuthenticationGate();
    provider.updatePermission(
      const RepositoryPermission(
        canRead: false,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
        canManageAttachments: false,
        canCheckCollaborators: false,
      ),
    );
    provider.setAuthenticationFailure('simulated provider failure');
    final secondConnectFuture = repository.connect(connection);
    await Future<void>.delayed(Duration.zero);
    provider.completeAuthentication();
    try {
      await secondConnectFuture;
      failures.add(
        'Step 5 failed: the reconnect that should have driven the repository into its restricted failure state unexpectedly succeeded.',
      );
    } catch (error) {
      result['reconnectFailure'] = error.toString();
    }

    final failedSession = repository.session;
    result['disconnectedSessionReference'] = _serializeSession(sessionReference);
    result['disconnectedRepositorySession'] = _serializeSession(
      failedSession,
    );
    result['sameInstanceAfterDisconnect'] = identical(
      sessionReference,
      failedSession,
    );

    _expect(
      failedSession != null,
      'Step 6 failed: repository.session was null after the failed reconnect.',
      failures,
    );
    if (failedSession != null) {
      _expect(
        failedSession.connectionState == ProviderConnectionState.error,
        'Step 6 failed: a fresh repository.session getter did not expose ProviderConnectionState.error after the failed reconnect. '
        'Observed ${failedSession.connectionState}.',
        failures,
      );
    }
    _expect(
      sessionReference.connectionState == ProviderConnectionState.error,
      'Step 6 failed: the previously obtained session reference did not update to ProviderConnectionState.error after the failed reconnect. '
      'Observed ${sessionReference.connectionState}.',
      failures,
    );
    _expect(
      sessionReference.resolvedUserIdentity == 'mock/repository',
      'Step 6 failed: the previously obtained session reference did not expose the restricted failure identity after the failed reconnect. '
      'Observed ${sessionReference.resolvedUserIdentity}.',
      failures,
    );
    for (final field in [
      sessionReference.canRead,
      sessionReference.canWrite,
      sessionReference.canCreateBranch,
      sessionReference.canManageAttachments,
      sessionReference.canCheckCollaborators,
    ]) {
      _expect(
        field == false,
        'Step 6 failed: the previously obtained session reference kept one or more restricted capabilities enabled after the failed reconnect. '
        'Observed ${_serializeSession(sessionReference)}.',
        failures,
      );
    }

    provider.resetAuthenticationGate();
    provider.updatePermission(
      const RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: false,
      ),
    );
    provider.updateAuthenticatedUser(
      const RepositoryUser(
        login: 'updated-user',
        displayName: 'Updated Session User',
      ),
    );
    provider.setAuthenticationFailure(null);
    final thirdConnectFuture = repository.connect(connection);
    await Future<void>.delayed(Duration.zero);
    provider.completeAuthentication();
    await thirdConnectFuture;

    final finalConnectedSession = repository.session;
    result['finalConnectedSessionReference'] = _serializeSession(sessionReference);
    result['finalConnectedRepositorySession'] = _serializeSession(
      finalConnectedSession,
    );
    result['sameInstanceAfterRecovery'] = identical(
      sessionReference,
      finalConnectedSession,
    );

    _expect(
      finalConnectedSession != null,
      'Step 8 failed: repository.session was null after the final successful reconnect.',
      failures,
    );
    if (finalConnectedSession != null) {
      _expect(
        finalConnectedSession.connectionState ==
            ProviderConnectionState.connected,
        'Step 8 failed: a fresh repository.session getter did not expose ProviderConnectionState.connected after the final transition. '
        'Observed ${finalConnectedSession.connectionState}.',
        failures,
      );
      _expect(
        finalConnectedSession.resolvedUserIdentity == 'updated-user',
        'Step 8 failed: a fresh repository.session getter did not expose the recovered user identity. '
        'Observed ${finalConnectedSession.resolvedUserIdentity}.',
        failures,
      );
      _expect(
        finalConnectedSession.canCreateBranch == false,
        'Step 8 failed: a fresh repository.session getter did not expose the recovered canCreateBranch=false restriction. '
        'Observed ${finalConnectedSession.canCreateBranch}.',
        failures,
      );
    }
    _expect(
      sessionReference.connectionState == ProviderConnectionState.connected,
      'Step 8 failed: the previously obtained session reference did not recover to ProviderConnectionState.connected after the final transition. '
      'Observed ${sessionReference.connectionState}.',
      failures,
    );
    _expect(
      sessionReference.resolvedUserIdentity == 'updated-user',
      'Step 8 failed: the previously obtained session reference did not expose the recovered user identity. '
      'Observed ${sessionReference.resolvedUserIdentity}.',
      failures,
    );
    _expect(
      sessionReference.canCreateBranch == false,
      'Step 8 failed: the previously obtained session reference did not expose the recovered canCreateBranch=false restriction. '
      'Observed ${sessionReference.canCreateBranch}.',
      failures,
    );

    if (failures.isNotEmpty) {
      throw StateError(failures.join('\n'));
    }

    result['status'] = 'passed';
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}
