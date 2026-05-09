import 'dart:convert';
import 'dart:typed_data';

import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

class FailingTrackStateProviderAdapter implements TrackStateProviderAdapter {
  int authenticateAttempts = 0;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/unauthorized-repository';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    authenticateAttempts += 1;
    throw const TrackStateProviderException(
      'Unauthorized: simulated connection failure for TS-80.',
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
    canManageAttachments: false,
    canCheckCollaborators: false,
  );

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      const [];

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => throw const TrackStateProviderException(
    'TS-80 should not attempt to create commits after a failed connection.',
  );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<String> resolveWriteBranch() async => dataRef;

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => throw const TrackStateProviderException(
    'TS-80 should not attempt to write attachments after a failed connection.',
  );

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => throw const TrackStateProviderException(
    'TS-80 should not attempt to write issue files after a failed connection.',
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
  final provider = FailingTrackStateProviderAdapter();
  final repository = ProviderBackedTrackStateRepository(provider: provider);

  Object? connectError;
  StackTrace? connectStackTrace;
  try {
    await repository.connect(
      const RepositoryConnection(
        repository: 'mock/unauthorized-repository',
        branch: 'main',
        token: 'mock-token',
      ),
    );
  } catch (error, stackTrace) {
    connectError = error;
    connectStackTrace = stackTrace;
  }

  print(
    jsonEncode({
      'authenticateAttempts': provider.authenticateAttempts,
      'connectError': connectError?.toString(),
      'connectStackTrace': connectStackTrace?.toString(),
      'session': serializeSession(repository.session),
    }),
  );
}
