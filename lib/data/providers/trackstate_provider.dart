import '../../domain/models/trackstate_models.dart';
import 'foundation_compat.dart';

typedef ProviderSessionListener = void Function();

abstract interface class RepositoryFileReader {
  Future<RepositoryTextFile> readTextFile(String path, {required String ref});
}

abstract interface class RepositoryTreeLister {
  Future<List<RepositoryTreeEntry>> listTree({required String ref});
}

abstract interface class RepositorySessionManager {
  Future<RepositoryUser> authenticate(RepositoryConnection connection);
}

abstract interface class RepositoryUserLookup {
  Future<RepositoryUser> lookupUserByLogin(String login);
  Future<RepositoryUser> lookupUserByEmail(String email);
}

abstract interface class RepositoryCommitManager {
  Future<String> resolveWriteBranch();
  Future<RepositoryBranch> getBranch(String name);
  Future<RepositoryWriteResult> writeTextFile(RepositoryWriteRequest request);
  Future<RepositoryCommitResult> createCommit(RepositoryCommitRequest request);
  Future<void> ensureCleanWorktree();
}

abstract interface class RepositoryFileMutator {
  Future<RepositoryCommitResult> applyFileChanges(
    RepositoryFileChangeRequest request,
  );
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

abstract interface class RepositoryHistoryReader {
  Future<List<RepositoryHistoryCommit>> listHistory({
    required String ref,
    required String path,
    int limit = 50,
  });
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

enum ProviderConnectionState { disconnected, connecting, connected, error }

enum AttachmentUploadMode { full, noLfs, none }

class ProviderSession {
  ProviderSession({
    required this.providerType,
    required this.connectionState,
    required this.resolvedUserIdentity,
    required this.canRead,
    required this.canWrite,
    required this.canCreateBranch,
    required this.canManageAttachments,
    required this.attachmentUploadMode,
    required this.canCheckCollaborators,
  });

  ProviderType providerType;
  ProviderConnectionState connectionState;
  String resolvedUserIdentity;
  bool canRead;
  bool canWrite;
  bool canCreateBranch;
  bool canManageAttachments;
  AttachmentUploadMode attachmentUploadMode;
  bool canCheckCollaborators;
  final Set<ProviderSessionListener> _listeners = <ProviderSessionListener>{};

  void addListener(ProviderSessionListener listener) {
    _listeners.add(listener);
  }

  void removeListener(ProviderSessionListener listener) {
    _listeners.remove(listener);
  }

  void _notifyListeners() {
    if (_listeners.isEmpty) {
      return;
    }
    for (final listener in List<ProviderSessionListener>.of(_listeners)) {
      listener();
    }
  }

  void update({
    required ProviderType providerType,
    required ProviderConnectionState connectionState,
    required String resolvedUserIdentity,
    required bool canRead,
    required bool canWrite,
    required bool canCreateBranch,
    required bool canManageAttachments,
    required AttachmentUploadMode attachmentUploadMode,
    required bool canCheckCollaborators,
  }) {
    final changed =
        this.providerType != providerType ||
        this.connectionState != connectionState ||
        this.resolvedUserIdentity != resolvedUserIdentity ||
        this.canRead != canRead ||
        this.canWrite != canWrite ||
        this.canCreateBranch != canCreateBranch ||
        this.canManageAttachments != canManageAttachments ||
        this.attachmentUploadMode != attachmentUploadMode ||
        this.canCheckCollaborators != canCheckCollaborators;
    if (!changed) {
      return;
    }
    this.providerType = providerType;
    this.connectionState = connectionState;
    this.resolvedUserIdentity = resolvedUserIdentity;
    this.canRead = canRead;
    this.canWrite = canWrite;
    this.canCreateBranch = canCreateBranch;
    this.canManageAttachments = canManageAttachments;
    this.attachmentUploadMode = attachmentUploadMode;
    this.canCheckCollaborators = canCheckCollaborators;
    _notifyListeners();
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

class RepositoryFileChangeRequest {
  const RepositoryFileChangeRequest({
    required this.branch,
    required this.message,
    required this.changes,
  });

  final String branch;
  final String message;
  final List<RepositoryFileChange> changes;
}

abstract base class RepositoryFileChange {
  const RepositoryFileChange({required this.path, this.expectedRevision});

  final String path;
  final String? expectedRevision;
}

final class RepositoryTextFileChange extends RepositoryFileChange {
  const RepositoryTextFileChange({
    required super.path,
    required this.content,
    super.expectedRevision,
  });

  final String content;
}

final class RepositoryBinaryFileChange extends RepositoryFileChange {
  const RepositoryBinaryFileChange({
    required super.path,
    required this.bytes,
    super.expectedRevision,
  });

  final Uint8List bytes;
}

final class RepositoryDeleteFileChange extends RepositoryFileChange {
  const RepositoryDeleteFileChange({
    required super.path,
    super.expectedRevision,
  });
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
    AttachmentUploadMode? attachmentUploadMode,
    bool? canCheckCollaborators,
  }) : canCreateBranch = canCreateBranch ?? canWrite,
       canManageAttachments = canManageAttachments ?? canWrite,
       attachmentUploadMode =
           attachmentUploadMode ??
           ((canManageAttachments ?? canWrite)
               ? AttachmentUploadMode.full
               : AttachmentUploadMode.none),
       canCheckCollaborators = canCheckCollaborators ?? isAdmin;

  final bool canRead;
  final bool canWrite;
  final bool isAdmin;
  final bool canCreateBranch;
  final bool canManageAttachments;
  final AttachmentUploadMode attachmentUploadMode;
  final bool canCheckCollaborators;
}

class RepositoryAttachment {
  const RepositoryAttachment({
    required this.path,
    required this.bytes,
    this.revision,
    this.lfsOid,
    this.declaredSizeBytes,
  });

  final String path;
  final Uint8List bytes;
  final String? revision;
  final String? lfsOid;
  final int? declaredSizeBytes;
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

enum RepositoryHistoryChangeType { added, modified, removed, renamed }

class RepositoryHistoryFileChange {
  const RepositoryHistoryFileChange({
    required this.path,
    required this.changeType,
    this.previousPath,
  });

  final String path;
  final RepositoryHistoryChangeType changeType;
  final String? previousPath;
}

class RepositoryHistoryCommit {
  const RepositoryHistoryCommit({
    required this.sha,
    required this.author,
    required this.timestamp,
    required this.message,
    required this.changes,
    this.parentSha,
  });

  final String sha;
  final String? parentSha;
  final String author;
  final String timestamp;
  final String message;
  final List<RepositoryHistoryFileChange> changes;
}

class TrackStateProviderException implements Exception {
  const TrackStateProviderException(this.message);

  final String message;

  @override
  String toString() => message;
}

class GitHubRateLimitException extends TrackStateProviderException {
  const GitHubRateLimitException({
    required String message,
    required this.requestPath,
    required this.statusCode,
    this.retryAfter,
  }) : super(message);

  final String requestPath;
  final int statusCode;
  final DateTime? retryAfter;
}
