import 'dart:convert';
import 'dart:typed_data';

import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

class UnexpectedOperationExceptionTrackStateProviderAdapter
    implements TrackStateProviderAdapter {
  int authenticateAttempts = 0;
  int permissionRequests = 0;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/unexpected-operation-repository';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    authenticateAttempts += 1;
    return const RepositoryUser(
      login: 'operation-user',
      displayName: 'Operation User',
    );
  }

  @override
  Future<RepositoryPermission> getPermission() async {
    permissionRequests += 1;
    if (permissionRequests == 1) {
      return const RepositoryPermission(
        canRead: false,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
        canManageAttachments: false,
        canCheckCollaborators: false,
      );
    }
    throw StateError('Unexpected operation-level exception for TS-118.');
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
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      const [];

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => throw StateError(
    'TS-118 should not attempt to create commits after a failed connection.',
  );

  @override
  Future<String> resolveWriteBranch() async => dataRef;

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => throw StateError(
    'TS-118 should not attempt to write attachments after a failed connection.',
  );

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => throw StateError(
    'TS-118 should not attempt to write issue files after a failed connection.',
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
    final provider = UnexpectedOperationExceptionTrackStateProviderAdapter();
    final repository = ProviderBackedTrackStateRepository(provider: provider);
    const connection = RepositoryConnection(
      repository: 'mock/unexpected-operation-repository',
      branch: 'main',
      token: 'mock-token',
    );

    Object? connectError;
    StackTrace? connectStackTrace;
    try {
      await repository.connect(connection);
    } catch (error, stackTrace) {
      connectError = error;
      connectStackTrace = stackTrace;
    }

    if (connectError == null) {
      throw StateError(
        'Step 3 failed: connect() unexpectedly succeeded instead of surfacing the configured operation-level exception.',
      );
    }

    final session = repository.session;
    if (session == null) {
      throw StateError(
        'Step 4 failed: repository.session was null after the unexpected operation-level exception, so a client could not observe the failure state.',
      );
    }

    result['authenticateAttempts'] = provider.authenticateAttempts;
    result['permissionRequests'] = provider.permissionRequests;
    result['connectError'] = connectError.toString();
    result['connectStackTrace'] = connectStackTrace?.toString();
    result['session'] = _serializeSession(session);
    result['status'] = 'passed';
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}
