import 'dart:convert';
import 'dart:typed_data';

import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

class PassiveTrackStateProviderAdapter implements TrackStateProviderAdapter {
  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'mock/uninitialized-repository';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      throw const TrackStateProviderException(
        'TS-91 must not authenticate while verifying the default session state.',
      );

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
    'TS-91 must not attempt to create commits before connect().',
  );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<String> resolveWriteBranch() async => dataRef;

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => throw const TrackStateProviderException(
    'TS-91 must not attempt to write attachments before connect().',
  );

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => throw const TrackStateProviderException(
    'TS-91 must not attempt to write issue files before connect().',
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
  final provider = PassiveTrackStateProviderAdapter();
  final repository = ProviderBackedTrackStateRepository(provider: provider);

  print(
    jsonEncode({
      'providerLabel': provider.repositoryLabel,
      'session': serializeSession(repository.session),
    }),
  );
}
