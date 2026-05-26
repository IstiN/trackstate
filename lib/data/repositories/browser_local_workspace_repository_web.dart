@JS()
library;

import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:meta/meta.dart';
import 'package:web/web.dart' as web;

import '../../domain/models/trackstate_models.dart';
import '../providers/trackstate_provider.dart';
import 'trackstate_repository.dart';

@JS('Array.fromAsync')
external JSPromise<JSArray<JSAny?>> _arrayFromAsync(JSAny iterable);

extension type _DirectoryValuesAccessor._(JSObject _value) implements JSObject {
  external JSAny values();
}

extension type _FileSystemPermissionHandle._(JSObject _value)
    implements JSObject {
  external JSPromise<JSString> queryPermission([
    _FileSystemPermissionDescriptor descriptor,
  ]);
  external JSPromise<JSString> requestPermission([
    _FileSystemPermissionDescriptor descriptor,
  ]);
}

extension type _FileSystemPermissionDescriptor._(JSObject _value)
    implements JSObject {
  external factory _FileSystemPermissionDescriptor({String mode});
}

final Map<String, web.FileSystemDirectoryHandle> _selectedDirectoriesByPath =
    <String, web.FileSystemDirectoryHandle>{};
const _browserLocalWorkspaceHandleDatabaseName =
    'trackstate.browserLocalWorkspaceHandles';
const _browserLocalWorkspaceHandleStoreName = 'directoryHandles';
final _readWritePermissionDescriptor = _FileSystemPermissionDescriptor(
  mode: 'readwrite',
);

Future<TrackStateRepository?> openBrowserLocalWorkspaceRepository({
  required String repositoryPath,
  required String defaultBranch,
  required String writeBranch,
}) async {
  return _openRememberedBrowserLocalWorkspaceRepository(
    repositoryPath: repositoryPath,
    defaultBranch: defaultBranch,
    writeBranch: writeBranch,
    requestPermissionIfNeeded: false,
  );
}

Future<TrackStateRepository?> requestBrowserLocalWorkspaceRepositoryAccess({
  required String repositoryPath,
  required String defaultBranch,
  required String writeBranch,
}) {
  return _openRememberedBrowserLocalWorkspaceRepository(
    repositoryPath: repositoryPath,
    defaultBranch: defaultBranch,
    writeBranch: writeBranch,
    requestPermissionIfNeeded: true,
  );
}

Future<void> rememberBrowserLocalWorkspaceSelection({
  required String workspacePath,
  required Object selection,
}) async {
  final normalizedPath = _normalizeWorkspacePath(workspacePath);
  if (normalizedPath.isEmpty) {
    return;
  }
  final handle = selection as web.FileSystemDirectoryHandle;
  if (handle.kind != 'directory') {
    return;
  }
  _selectedDirectoriesByPath[normalizedPath] = handle;
  unawaited(_persistRememberedDirectoryHandle(normalizedPath, handle));
}

String _normalizeWorkspacePath(String path) => path.trim();

@visibleForTesting
Future<void> clearRememberedBrowserLocalWorkspaceSelections({
  bool clearPersisted = true,
}) async {
  _selectedDirectoriesByPath.clear();
  if (!clearPersisted) {
    return;
  }
  await _clearPersistedBrowserLocalWorkspaceSelections();
}

Future<TrackStateRepository?> _openRememberedBrowserLocalWorkspaceRepository({
  required String repositoryPath,
  required String defaultBranch,
  required String writeBranch,
  required bool requestPermissionIfNeeded,
}) async {
  final normalizedPath = _normalizeWorkspacePath(repositoryPath);
  if (normalizedPath.isEmpty) {
    return null;
  }
  final handle = await _resolveRememberedDirectoryHandle(normalizedPath);
  if (handle == null) {
    return null;
  }
  if (requestPermissionIfNeeded && !await _requestDirectoryPermission(handle)) {
    return null;
  }
  return _BrowserLocalTrackStateRepository(
    directoryHandle: handle,
    repositoryPath: normalizedPath,
    dataRef: defaultBranch,
    writeBranch: writeBranch,
  );
}

Future<web.FileSystemDirectoryHandle?> _resolveRememberedDirectoryHandle(
  String normalizedPath,
) async {
  final rememberedHandle = _selectedDirectoriesByPath[normalizedPath];
  if (rememberedHandle != null) {
    return rememberedHandle;
  }
  final persistedHandle = await _loadPersistedDirectoryHandle(normalizedPath);
  if (persistedHandle == null) {
    return null;
  }
  _selectedDirectoriesByPath[normalizedPath] = persistedHandle;
  return persistedHandle;
}

Future<bool> _requestDirectoryPermission(
  web.FileSystemDirectoryHandle handle,
) async {
  final currentState = await _queryDirectoryPermissionState(handle);
  if (currentState == 'granted') {
    return true;
  }
  try {
    final nextState = await _FileSystemPermissionHandle._(
      handle as JSObject,
    ).requestPermission(_readWritePermissionDescriptor).toDart;
    return nextState.toDart == 'granted';
  } on Object {
    return false;
  }
}

Future<String?> _queryDirectoryPermissionState(
  web.FileSystemDirectoryHandle handle,
) async {
  try {
    final state = await _FileSystemPermissionHandle._(
      handle as JSObject,
    ).queryPermission(_readWritePermissionDescriptor).toDart;
    return state.toDart;
  } on Object {
    return null;
  }
}

Future<void> _persistRememberedDirectoryHandle(
  String normalizedPath,
  web.FileSystemDirectoryHandle handle,
) async {
  final database = await _openRememberedDirectoryHandleDatabase();
  if (database == null) {
    return;
  }
  try {
    final transaction = database.transaction(
      _browserLocalWorkspaceHandleStoreName.toJS,
      'readwrite',
    );
    final store = transaction.objectStore(
      _browserLocalWorkspaceHandleStoreName,
    );
    await _awaitIdbRequest<void>(
      store.put(handle, normalizedPath.toJS),
      (_) {},
    );
    await _awaitIdbTransactionComplete(transaction);
  } on Object {
    // Ignore persistence failures so in-memory browser access still works.
  } finally {
    database.close();
  }
}

Future<web.FileSystemDirectoryHandle?> _loadPersistedDirectoryHandle(
  String normalizedPath,
) async {
  final database = await _openRememberedDirectoryHandleDatabase();
  if (database == null) {
    return null;
  }
  try {
    final transaction = database.transaction(
      _browserLocalWorkspaceHandleStoreName.toJS,
      'readonly',
    );
    final store = transaction.objectStore(
      _browserLocalWorkspaceHandleStoreName,
    );
    final result = await _awaitIdbRequest<JSAny?>(
      store.get(normalizedPath.toJS),
      (value) => value,
    );
    await _awaitIdbTransactionComplete(transaction);
    if (result == null) {
      return null;
    }
    final handle = result as web.FileSystemDirectoryHandle;
    if (handle.kind != 'directory') {
      await _deletePersistedDirectoryHandle(normalizedPath);
      return null;
    }
    return handle;
  } on Object {
    return null;
  } finally {
    database.close();
  }
}

Future<void> _deletePersistedDirectoryHandle(String normalizedPath) async {
  final database = await _openRememberedDirectoryHandleDatabase();
  if (database == null) {
    return;
  }
  try {
    final transaction = database.transaction(
      _browserLocalWorkspaceHandleStoreName.toJS,
      'readwrite',
    );
    final store = transaction.objectStore(
      _browserLocalWorkspaceHandleStoreName,
    );
    await _awaitIdbRequest<void>(store.delete(normalizedPath.toJS), (_) {});
    await _awaitIdbTransactionComplete(transaction);
  } on Object {
    return;
  } finally {
    database.close();
  }
}

Future<void> _clearPersistedBrowserLocalWorkspaceSelections() async {
  final database = await _openRememberedDirectoryHandleDatabase();
  if (database == null) {
    return;
  }
  try {
    final transaction = database.transaction(
      _browserLocalWorkspaceHandleStoreName.toJS,
      'readwrite',
    );
    final store = transaction.objectStore(
      _browserLocalWorkspaceHandleStoreName,
    );
    await _awaitIdbRequest<void>(store.clear(), (_) {});
    await _awaitIdbTransactionComplete(transaction);
  } on Object {
    return;
  } finally {
    database.close();
  }
}

Future<web.IDBDatabase?> _openRememberedDirectoryHandleDatabase() {
  final completer = Completer<web.IDBDatabase?>();
  final openRequest = web.window.indexedDB.open(
    _browserLocalWorkspaceHandleDatabaseName,
    1,
  );
  openRequest.onupgradeneeded = ((web.Event _) {
    final database = openRequest.result as web.IDBDatabase;
    if (!database.objectStoreNames.contains(
      _browserLocalWorkspaceHandleStoreName,
    )) {
      database.createObjectStore(_browserLocalWorkspaceHandleStoreName);
    }
  }).toJS;
  openRequest.onsuccess = ((web.Event _) {
    if (completer.isCompleted) {
      return;
    }
    completer.complete(openRequest.result as web.IDBDatabase);
  }).toJS;
  openRequest.onerror = ((web.Event _) {
    if (completer.isCompleted) {
      return;
    }
    completer.complete(null);
  }).toJS;
  openRequest.onblocked = ((web.Event _) {
    if (completer.isCompleted) {
      return;
    }
    completer.complete(null);
  }).toJS;
  return completer.future;
}

Future<T> _awaitIdbRequest<T>(
  web.IDBRequest request,
  T Function(JSAny? value) convert,
) {
  final completer = Completer<T>();
  request.onsuccess = ((web.Event _) {
    if (completer.isCompleted) {
      return;
    }
    completer.complete(convert(request.result));
  }).toJS;
  request.onerror = ((web.Event _) {
    if (completer.isCompleted) {
      return;
    }
    completer.completeError(
      request.error ?? StateError('IndexedDB request failed.'),
    );
  }).toJS;
  return completer.future;
}

Future<void> _awaitIdbTransactionComplete(web.IDBTransaction transaction) {
  final completer = Completer<void>();
  transaction.oncomplete = ((web.Event _) {
    if (!completer.isCompleted) {
      completer.complete();
    }
  }).toJS;
  transaction.onerror = ((web.Event _) {
    if (!completer.isCompleted) {
      completer.completeError(
        transaction.error ?? StateError('IndexedDB transaction failed.'),
      );
    }
  }).toJS;
  transaction.onabort = ((web.Event _) {
    if (!completer.isCompleted) {
      completer.completeError(
        transaction.error ?? StateError('IndexedDB transaction was aborted.'),
      );
    }
  }).toJS;
  return completer.future;
}

class _BrowserLocalTrackStateRepository
    extends ProviderBackedTrackStateRepository {
  _BrowserLocalTrackStateRepository({
    required web.FileSystemDirectoryHandle directoryHandle,
    required String repositoryPath,
    required String dataRef,
    required String writeBranch,
  }) : super(
         provider: _BrowserLocalWorkspaceProvider(
           directoryHandle: directoryHandle,
           repositoryPath: repositoryPath,
           dataRef: dataRef,
           writeBranch: writeBranch,
         ),
         usesLocalPersistence: true,
         supportsGitHubAuth: false,
       );
}

class _BrowserLocalWorkspaceProvider
    implements TrackStateProviderAdapter, RepositoryFileMutator {
  _BrowserLocalWorkspaceProvider({
    required web.FileSystemDirectoryHandle directoryHandle,
    required this.repositoryPath,
    required String dataRef,
    required String writeBranch,
  }) : _directoryHandle = directoryHandle,
       dataRef = dataRef.trim().isEmpty ? 'HEAD' : dataRef.trim(),
       _writeBranch = writeBranch.trim().isEmpty ? 'main' : writeBranch.trim();

  final web.FileSystemDirectoryHandle _directoryHandle;
  final String repositoryPath;
  @override
  final String dataRef;
  final String _writeBranch;
  int _contentRevision = 0;

  @override
  ProviderType get providerType => ProviderType.local;

  @override
  String get repositoryLabel => repositoryPath;

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    return RepositoryUser(
      login: 'local-user',
      displayName: _displayName(repositoryPath),
    );
  }

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    final permission = await getPermission();
    final revision = await _revision();
    final state = RepositorySyncState(
      providerType: providerType,
      repositoryRevision: revision,
      sessionRevision:
          '${await resolveWriteBranch()}:${permission.canRead}:${permission.canWrite}:${permission.supportsReleaseAttachmentWrites}',
      connectionState: ProviderConnectionState.connected,
      workingTreeRevision: revision,
      permission: permission,
    );
    if (previousState == null) {
      return RepositorySyncCheck(state: state);
    }
    final signals = <WorkspaceSyncSignal>{};
    if (previousState.repositoryRevision != state.repositoryRevision) {
      signals.add(WorkspaceSyncSignal.localHead);
    }
    if ((previousState.workingTreeRevision ?? '') !=
        (state.workingTreeRevision ?? '')) {
      signals.add(WorkspaceSyncSignal.localWorktree);
    }
    return RepositorySyncCheck(state: state, signals: signals);
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryBranch> getBranch(String name) async => RepositoryBranch(
    name: name,
    exists: name.trim().isNotEmpty,
    isCurrent: name.trim() == _writeBranch,
  );

  @override
  Future<RepositoryPermission> getPermission() async =>
      const RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        supportsReleaseAttachmentWrites: false,
      );

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async {
    final entries = <RepositoryTreeEntry>[];
    await _collectTreeEntries(
      directory: _directoryHandle,
      prefix: '',
      entries: entries,
    );
    entries.sort((left, right) => left.path.compareTo(right.path));
    return entries;
  }

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    final fileHandle = await _resolveFileHandle(path);
    final file = await fileHandle.getFile().toDart;
    final bytes = (await file.arrayBuffer().toDart).toDart.asUint8List();
    return RepositoryAttachment(
      path: path,
      bytes: bytes,
      revision: _fileRevision(path),
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final fileHandle = await _resolveFileHandle(path);
    final file = await fileHandle.getFile().toDart;
    final content = (await file.text().toDart).toDart;
    return RepositoryTextFile(
      path: path,
      content: content,
      revision: _fileRevision(path),
    );
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async {
    validateRepositoryTextWrite(
      RepositoryWriteRequest(
        path: request.path,
        content: request.content,
        message: request.message,
        branch: request.branch,
        expectedRevision: request.expectedRevision,
      ),
    );
    await _writeTextFile(
      path: request.path,
      content: request.content,
      create: true,
    );
    _contentRevision += 1;
    return RepositoryCommitResult(
      branch: request.branch,
      message: request.message,
      revision: _fileRevision(request.path),
    );
  }

  @override
  Future<RepositoryCommitResult> applyFileChanges(
    RepositoryFileChangeRequest request,
  ) async {
    var changed = false;
    for (final change in request.changes) {
      if (change case final RepositoryTextFileChange textChange) {
        validateRepositoryTextChange(textChange);
        if (!await _textFileDiffers(textChange.path, textChange.content)) {
          continue;
        }
        await _writeTextFile(
          path: textChange.path,
          content: textChange.content,
          create: true,
        );
        changed = true;
      } else if (change case final RepositoryBinaryFileChange binaryChange) {
        if (!await _binaryFileDiffers(binaryChange.path, binaryChange.bytes)) {
          continue;
        }
        await _writeBinaryFile(
          path: binaryChange.path,
          bytes: binaryChange.bytes,
          create: true,
        );
        changed = true;
      } else if (change case final RepositoryDeleteFileChange deleteChange) {
        if (!await _fileExists(deleteChange.path)) {
          continue;
        }
        await _deleteFile(deleteChange.path);
        changed = true;
      }
    }
    if (!changed) {
      return RepositoryCommitResult(
        branch: request.branch,
        message: request.message,
        revision: await _revision(),
        createdCommit: false,
      );
    }
    _contentRevision += 1;
    return RepositoryCommitResult(
      branch: request.branch,
      message: request.message,
      revision: await _revision(),
    );
  }

  @override
  Future<String> resolveWriteBranch() async => _writeBranch;

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    await _writeBinaryFile(
      path: request.path,
      bytes: request.bytes,
      create: true,
    );
    _contentRevision += 1;
    return RepositoryAttachmentWriteResult(
      path: request.path,
      branch: request.branch,
      revision: _fileRevision(request.path),
    );
  }

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    validateRepositoryTextWrite(request);
    await _writeTextFile(
      path: request.path,
      content: request.content,
      create: true,
    );
    _contentRevision += 1;
    return RepositoryWriteResult(
      path: request.path,
      branch: request.branch,
      revision: _fileRevision(request.path),
    );
  }

  Future<void> _collectTreeEntries({
    required web.FileSystemDirectoryHandle directory,
    required String prefix,
    required List<RepositoryTreeEntry> entries,
  }) async {
    final values = (await _arrayFromAsync(
      _DirectoryValuesAccessor._(directory as JSObject).values(),
    ).toDart).toDart;
    for (final rawEntry in values) {
      if (rawEntry == null) {
        continue;
      }
      final handle = rawEntry as web.FileSystemHandle;
      final name = handle.name.trim();
      if (name.isEmpty) {
        continue;
      }
      final path = prefix.isEmpty ? name : '$prefix/$name';
      if (handle.kind == 'directory') {
        entries.add(RepositoryTreeEntry(path: path, type: 'tree'));
        await _collectTreeEntries(
          directory: handle as web.FileSystemDirectoryHandle,
          prefix: path,
          entries: entries,
        );
      } else {
        entries.add(RepositoryTreeEntry(path: path, type: 'blob'));
      }
    }
  }

  Future<void> _deleteFile(String path) async {
    final segments = _pathSegments(path);
    if (segments.isEmpty) {
      throw const TrackStateProviderException(
        'Repository path must not be empty.',
      );
    }
    final parent = await _resolveDirectoryHandle(
      segments.take(segments.length - 1),
      create: false,
    );
    await parent.removeEntry(segments.last).toDart;
  }

  Future<bool> _fileExists(String path) async {
    try {
      await _resolveFileHandle(path);
      return true;
    } on TrackStateProviderException {
      return false;
    }
  }

  String _fileRevision(String path) => '${_contentRevision + 1}:$path';

  List<String> _pathSegments(String path) => path
      .split('/')
      .map((segment) => segment.trim())
      .where((segment) => segment.isNotEmpty)
      .toList();

  Future<String> _revision() async {
    final tree = await listTree(ref: dataRef);
    final treeHash = tree.map((entry) => entry.path).join('\n').hashCode;
    return '$_contentRevision:${tree.length}:$treeHash';
  }

  Future<web.FileSystemDirectoryHandle> _resolveDirectoryHandle(
    Iterable<String> segments, {
    required bool create,
  }) async {
    var current = _directoryHandle;
    for (final segment in segments) {
      current = await current
          .getDirectoryHandle(
            segment,
            web.FileSystemGetDirectoryOptions(create: create),
          )
          .toDart;
    }
    return current;
  }

  Future<web.FileSystemFileHandle> _resolveFileHandle(
    String path, {
    bool create = false,
  }) async {
    final segments = _pathSegments(path);
    if (segments.isEmpty) {
      throw const TrackStateProviderException(
        'Repository path must not be empty.',
      );
    }
    try {
      final parent = await _resolveDirectoryHandle(
        segments.take(segments.length - 1),
        create: create,
      );
      return await parent
          .getFileHandle(
            segments.last,
            web.FileSystemGetFileOptions(create: create),
          )
          .toDart;
    } on Object catch (error) {
      throw TrackStateProviderException(
        'Could not access $path in $repositoryPath. ${_errorMessage(error)}',
      );
    }
  }

  Future<void> _writeBinaryFile({
    required String path,
    required Uint8List bytes,
    required bool create,
  }) async {
    final fileHandle = await _resolveFileHandle(path, create: create);
    final writable = await fileHandle.createWritable().toDart;
    await writable.write(bytes.toJS).toDart;
    await writable.close().toDart;
  }

  Future<bool> _binaryFileDiffers(String path, Uint8List bytes) async {
    try {
      final fileHandle = await _resolveFileHandle(path);
      final file = await fileHandle.getFile().toDart;
      final currentBytes = (await file.arrayBuffer().toDart).toDart
          .asUint8List();
      if (currentBytes.length != bytes.length) {
        return true;
      }
      for (var index = 0; index < currentBytes.length; index += 1) {
        if (currentBytes[index] != bytes[index]) {
          return true;
        }
      }
      return false;
    } on TrackStateProviderException {
      return true;
    }
  }

  Future<void> _writeTextFile({
    required String path,
    required String content,
    required bool create,
  }) async {
    final fileHandle = await _resolveFileHandle(path, create: create);
    final writable = await fileHandle.createWritable().toDart;
    await writable.write(content.toJS).toDart;
    await writable.close().toDart;
  }

  Future<bool> _textFileDiffers(String path, String content) async {
    try {
      final fileHandle = await _resolveFileHandle(path);
      final file = await fileHandle.getFile().toDart;
      return (await file.text().toDart).toDart != content;
    } on TrackStateProviderException {
      return true;
    }
  }
}

String _displayName(String repositoryPath) {
  final normalizedPath = repositoryPath.trim().replaceAll(
    RegExp(r'[\\/]+$'),
    '',
  );
  if (normalizedPath.isEmpty) {
    return 'Local workspace';
  }
  final segments = normalizedPath.split(RegExp(r'[\\/]'));
  return segments.isEmpty ? normalizedPath : segments.last;
}

String _errorMessage(Object error) {
  if (error case web.DOMException(:final message)) {
    final normalized = message.trim();
    if (normalized.isNotEmpty) {
      return normalized;
    }
  }
  if (error case TrackStateProviderException(:final message)) {
    return message;
  }
  final normalized = error.toString().trim();
  return normalized.isEmpty ? 'Browser file system access failed.' : normalized;
}
