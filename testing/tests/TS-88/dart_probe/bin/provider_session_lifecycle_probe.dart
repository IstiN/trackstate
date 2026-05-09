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
        canRead: false,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
      ),
      authenticatedUser: const RepositoryUser(
        login: 'lifecycle-user',
        displayName: 'Lifecycle User',
      ),
    );
    final repository = ProviderBackedTrackStateRepository(provider: provider);

    final initialSession = repository.session;
    final initialSessionSnapshot = _serializeSession(initialSession);
    result['initialSession'] = initialSessionSnapshot;

    final connectFuture = repository.connect(
      const RepositoryConnection(
        repository: 'mock/repository',
        branch: 'main',
        token: 'mock-token',
      ),
    );

    await Future<void>.delayed(Duration.zero);

    final connectingSession = repository.session;
    final connectingSessionSnapshot = _serializeSession(connectingSession);
    result['connectingSession'] = connectingSessionSnapshot;

    provider.completeAuthentication();
    await connectFuture;

    final failures = <String>[];
    if (initialSessionSnapshot == null) {
      failures.add(
        'Step 2 failed: repository.session was null immediately after initialization, so product logic could not observe ProviderConnectionState.disconnected.',
      );
    } else if (initialSessionSnapshot['connectionState'] !=
        ProviderConnectionState.disconnected.toString()) {
      failures.add(
        'Step 2 failed: repository.session did not expose ProviderConnectionState.disconnected immediately after initialization. '
        'Observed ${initialSessionSnapshot['connectionState']}.',
      );
    }

    if (connectingSessionSnapshot == null) {
      failures.add(
        'Step 4 failed: repository.session was null while authentication was in progress, so product logic could not observe ProviderConnectionState.connecting.',
      );
    } else if (connectingSessionSnapshot['connectionState'] !=
        ProviderConnectionState.connecting.toString()) {
      failures.add(
        'Step 4 failed: repository.session did not expose ProviderConnectionState.connecting after authentication started. '
        'Observed ${connectingSessionSnapshot['connectionState']}.',
      );
    }

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
