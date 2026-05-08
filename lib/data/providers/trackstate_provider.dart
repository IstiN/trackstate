import 'dart:typed_data';

import '../../domain/models/trackstate_models.dart';

abstract interface class RepositoryFileReader {
  Future<RepositoryTextFile> readTextFile(String path, {required String ref});
}

abstract interface class RepositoryTreeLister {
  Future<List<RepositoryTreeEntry>> listTree({required String ref});
}

abstract interface class RepositorySessionManager {
  Future<RepositoryUser> authenticate(RepositoryConnection connection);
}

abstract interface class RepositoryCommitManager {
  Future<String> resolveWriteBranch();
  Future<RepositoryBranch> getBranch(String name);
  Future<RepositoryWriteResult> writeTextFile(RepositoryWriteRequest request);
  Future<RepositoryCommitResult> createCommit(RepositoryCommitRequest request);
}

abstract interface class RepositoryPermissionChecker {
  Future<RepositoryPermission> getPermission();
}

abstract interface class RepositoryAttachmentStore {
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  });
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  );
  Future<bool> isLfsTracked(String path);
}

abstract interface class TrackStateProviderAdapter
    implements
        RepositoryFileReader,
        RepositoryTreeLister,
        RepositorySessionManager,
        RepositoryCommitManager,
        RepositoryPermissionChecker,
        RepositoryAttachmentStore {
  ProviderType get providerType;
  String get repositoryLabel;
  String get dataRef;
}

enum ProviderType { github, local }

enum ProviderConnectionState { disconnected, connecting, connected }

class ProviderSession {
  ProviderSession({
    required this.providerType,
    required this.connectionState,
    required this.resolvedUserIdentity,
    required this.canRead,
    required this.canWrite,
    required this.canCreateBranch,
    required this.canManageAttachments,
    required this.canCheckCollaborators,
  });

  ProviderType providerType;
  ProviderConnectionState connectionState;
  String resolvedUserIdentity;
  bool canRead;
  bool canWrite;
  bool canCreateBranch;
  bool canManageAttachments;
  bool canCheckCollaborators;

  ProviderSession copy() => ProviderSession(
    providerType: providerType,
    connectionState: connectionState,
    resolvedUserIdentity: resolvedUserIdentity,
    canRead: canRead,
    canWrite: canWrite,
    canCreateBranch: canCreateBranch,
    canManageAttachments: canManageAttachments,
    canCheckCollaborators: canCheckCollaborators,
  );

  void update({
    required ProviderType providerType,
    required ProviderConnectionState connectionState,
    required String resolvedUserIdentity,
    required bool canRead,
    required bool canWrite,
    required bool canCreateBranch,
    required bool canManageAttachments,
    required bool canCheckCollaborators,
  }) {
    this.providerType = providerType;
    this.connectionState = connectionState;
    this.resolvedUserIdentity = resolvedUserIdentity;
    this.canRead = canRead;
    this.canWrite = canWrite;
    this.canCreateBranch = canCreateBranch;
    this.canManageAttachments = canManageAttachments;
    this.canCheckCollaborators = canCheckCollaborators;
  }
}

class RepositoryTreeEntry {
  const RepositoryTreeEntry({required this.path, required this.type});

  final String path;
  final String type;
}

class RepositoryTextFile {
  const RepositoryTextFile({
    required this.path,
    required this.content,
    this.revision,
  });

  final String path;
  final String content;
  final String? revision;
}

class RepositoryWriteRequest {
  const RepositoryWriteRequest({
    required this.path,
    required this.content,
    required this.message,
    required this.branch,
    this.expectedRevision,
  });

  final String path;
  final String content;
  final String message;
  final String branch;
  final String? expectedRevision;
}

class RepositoryWriteResult {
  const RepositoryWriteResult({
    required this.path,
    required this.branch,
    this.revision,
  });

  final String path;
  final String branch;
  final String? revision;
}

class RepositoryCommitRequest {
  const RepositoryCommitRequest({
    required this.path,
    required this.content,
    required this.message,
    required this.branch,
    this.expectedRevision,
  });

  final String path;
  final String content;
  final String message;
  final String branch;
  final String? expectedRevision;
}

class RepositoryCommitResult {
  const RepositoryCommitResult({
    required this.branch,
    required this.message,
    this.revision,
  });

  final String branch;
  final String message;
  final String? revision;
}

class RepositoryBranch {
  const RepositoryBranch({
    required this.name,
    required this.exists,
    required this.isCurrent,
  });

  final String name;
  final bool exists;
  final bool isCurrent;
}

class RepositoryPermission {
  const RepositoryPermission({
    required this.canRead,
    required this.canWrite,
    required this.isAdmin,
    bool? canCreateBranch,
    bool? canManageAttachments,
    bool? canCheckCollaborators,
  }) : canCreateBranch = canCreateBranch ?? canWrite,
       canManageAttachments = canManageAttachments ?? canWrite,
       canCheckCollaborators = canCheckCollaborators ?? isAdmin;

  final bool canRead;
  final bool canWrite;
  final bool isAdmin;
  final bool canCreateBranch;
  final bool canManageAttachments;
  final bool canCheckCollaborators;
}

class RepositoryAttachment {
  const RepositoryAttachment({
    required this.path,
    required this.bytes,
    this.revision,
  });

  final String path;
  final Uint8List bytes;
  final String? revision;
}

class RepositoryAttachmentWriteRequest {
  const RepositoryAttachmentWriteRequest({
    required this.path,
    required this.bytes,
    required this.message,
    required this.branch,
    this.expectedRevision,
  });

  final String path;
  final Uint8List bytes;
  final String message;
  final String branch;
  final String? expectedRevision;
}

class RepositoryAttachmentWriteResult {
  const RepositoryAttachmentWriteResult({
    required this.path,
    required this.branch,
    this.revision,
  });

  final String path;
  final String branch;
  final String? revision;
}

class TrackStateProviderException implements Exception {
  const TrackStateProviderException(this.message);

  final String message;

  @override
  String toString() => message;
}
