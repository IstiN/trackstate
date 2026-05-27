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
final _BrowserLocalWorkspaceSelectionsPersistence
_browserLocalWorkspaceSelectionsPersistence =
    _BrowserLocalWorkspaceSelectionsPersistence();

@JS('window.indexedDB')
external web.IDBFactory? get _indexedDbFactory;
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
  await _browserLocalWorkspaceSelectionsPersistence.save(
    workspacePath: normalizedPath,
    handle: handle,
  );
}

@visibleForTesting
Future<void> debugResetBrowserLocalWorkspaceSelectionCache({
  bool clearPersisted = false,
}) async {
  _selectedDirectoriesByPath.clear();
  if (clearPersisted) {
    await _browserLocalWorkspaceSelectionsPersistence.clear();
  }
}

class _BrowserLocalWorkspaceSelectionsPersistence {
  static const String _storeName = 'directoryHandles';
  static const int _databaseVersion = 1;

  String get _databaseName {
    final location = web.window.location;
    return 'trackstate.browserLocalWorkspaceSelections:${location.pathname}${location.search}';
  }

  String get _storageMarkerPrefix {
    final location = web.window.location;
    return 'trackstate.browserLocalWorkspaceSelections.marker:${location.pathname}${location.search}:';
  }

  bool hasPersistedSelection({required String workspacePath}) {
    return web.window.localStorage.getItem(_markerKey(workspacePath)) == '1';
  }

  Future<void> save({
    required String workspacePath,
    required web.FileSystemDirectoryHandle handle,
  }) async {
    final database = await _openDatabase();
    if (database == null) {
      return;
    }
    try {
      final transaction = database.transaction(_storeName.toJS, 'readwrite');
      final request = transaction
          .objectStore(_storeName)
          .put(handle, workspacePath.toJS);
      await Future.wait<void>([
        _awaitRequestCompletion(
          request,
          operation: 'persist browser local workspace access',
        ),
        _awaitTransactionCompletion(
          transaction,
          operation: 'commit browser local workspace access',
        ),
      ]);
      _markPersistedSelection(workspacePath);
    } finally {
      database.close();
    }
  }

  Future<web.FileSystemDirectoryHandle?> restore({
    required String workspacePath,
  }) async {
    final database = await _openDatabase();
    if (database == null) {
      return null;
    }
    try {
      final transaction = database.transaction(_storeName.toJS, 'readonly');
      final request = transaction
          .objectStore(_storeName)
          .get(workspacePath.toJS);
      final result = await _awaitRequestResult(
        request,
        operation: 'restore browser local workspace access',
      );
      if (result == null || result.dartify() == null) {
        _clearPersistedSelectionMarker(workspacePath);
        return null;
      }
      final handle = result as web.FileSystemDirectoryHandle;
      if (handle.kind != 'directory') {
        await delete(workspacePath: workspacePath);
        return null;
      }
      _selectedDirectoriesByPath[workspacePath] = handle;
      return handle;
    } finally {
      database.close();
    }
  }

  Future<void> delete({required String workspacePath}) async {
    final database = await _openDatabase();
    if (database == null) {
      _clearPersistedSelectionMarker(workspacePath);
      return;
    }
    try {
      final transaction = database.transaction(_storeName.toJS, 'readwrite');
      final request = transaction
          .objectStore(_storeName)
          .delete(workspacePath.toJS);
      await Future.wait<void>([
        _awaitRequestCompletion(
          request,
          operation: 'delete browser local workspace access',
        ),
        _awaitTransactionCompletion(
          transaction,
          operation: 'commit browser local workspace access deletion',
        ),
      ]);
    } finally {
      _clearPersistedSelectionMarker(workspacePath);
      database.close();
    }
  }

  Future<void> clear() async {
    final database = await _openDatabase();
    if (database == null) {
      _clearPersistedSelectionMarkers();
      return;
    }
    try {
      final transaction = database.transaction(_storeName.toJS, 'readwrite');
      final request = transaction.objectStore(_storeName).clear();
      await Future.wait<void>([
        _awaitRequestCompletion(
          request,
          operation: 'clear browser local workspace access',
        ),
        _awaitTransactionCompletion(
          transaction,
          operation: 'commit browser local workspace access reset',
        ),
      ]);
    } finally {
      _clearPersistedSelectionMarkers();
      database.close();
    }
  }

  String _markerKey(String workspacePath) {
    return '$_storageMarkerPrefix$workspacePath';
  }

  void _markPersistedSelection(String workspacePath) {
    web.window.localStorage.setItem(_markerKey(workspacePath), '1');
  }

  void _clearPersistedSelectionMarker(String workspacePath) {
    web.window.localStorage.removeItem(_markerKey(workspacePath));
  }

  void _clearPersistedSelectionMarkers() {
    final keys = <String>[
      for (var index = 0; index < web.window.localStorage.length; index += 1)
        web.window.localStorage.key(index) ?? '',
    ];
    for (final key in keys) {
      if (key.startsWith(_storageMarkerPrefix)) {
        web.window.localStorage.removeItem(key);
      }
    }
  }

  Future<web.IDBDatabase?> _openDatabase() async {
    final factory = _indexedDbFactory;
    if (factory == null) {
      return null;
    }
    final request = factory.open(_databaseName, _databaseVersion);
    request.onupgradeneeded = ((web.Event _) {
      final database = request.result as web.IDBDatabase;
      if (!database.objectStoreNames.contains(_storeName)) {
        database.createObjectStore(_storeName);
      }
    }).toJS;
    final result = await _awaitOpenDatabaseRequest(
      request,
      operation: 'open browser local workspace access storage',
    );
    return result as web.IDBDatabase;
  }

  Future<JSAny?> _awaitRequestResult(
    web.IDBRequest request, {
    required String operation,
  }) {
    final completer = Completer<JSAny?>();
    request.onsuccess = ((web.Event _) {
      if (!completer.isCompleted) {
        completer.complete(request.result);
      }
    }).toJS;
    request.onerror = ((web.Event _) {
      if (!completer.isCompleted) {
        completer.completeError(_requestError(request, operation: operation));
      }
    }).toJS;
    return completer.future;
  }

  Future<void> _awaitRequestCompletion(
    web.IDBRequest request, {
    required String operation,
  }) async {
    await _awaitRequestResult(request, operation: operation);
  }

  Future<void> _awaitTransactionCompletion(
    web.IDBTransaction transaction, {
    required String operation,
  }) {
    final completer = Completer<void>();
    transaction.oncomplete = ((web.Event _) {
      if (!completer.isCompleted) {
        completer.complete();
      }
    }).toJS;
    transaction.onabort = ((web.Event _) {
      if (!completer.isCompleted) {
        completer.completeError(
          StateError('Failed to $operation: ${transaction.error ?? 'abort'}'),
        );
      }
    }).toJS;
    transaction.onerror = ((web.Event _) {
      if (!completer.isCompleted) {
        completer.completeError(
          StateError('Failed to $operation: ${transaction.error ?? 'error'}'),
        );
      }
    }).toJS;
    return completer.future;
  }

  Future<JSAny?> _awaitOpenDatabaseRequest(
    web.IDBOpenDBRequest request, {
    required String operation,
  }) {
    final completer = Completer<JSAny?>();
    request.onsuccess = ((web.Event _) {
      if (!completer.isCompleted) {
        completer.complete(request.result);
      }
    }).toJS;
    request.onerror = ((web.Event _) {
      if (!completer.isCompleted) {
        completer.completeError(_requestError(request, operation: operation));
      }
    }).toJS;
    request.onblocked = ((web.Event _) {
      if (!completer.isCompleted) {
        completer.completeError(
          StateError('Failed to $operation: IndexedDB request was blocked.'),
        );
      }
    }).toJS;
    return completer.future;
  }

  StateError _requestError(
    web.IDBRequest request, {
    required String operation,
  }) {
    return StateError(
      'Failed to $operation: ${request.error ?? 'unknown error'}',
    );
  }
}

String _normalizeWorkspacePath(String path) => path.trim();

@visibleForTesting
Future<void> clearRememberedBrowserLocalWorkspaceSelections({
  bool clearPersisted = true,
}) => debugResetBrowserLocalWorkspaceSelectionCache(
  clearPersisted: clearPersisted,
);

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
  if (!_browserLocalWorkspaceSelectionsPersistence.hasPersistedSelection(
    workspacePath: normalizedPath,
  )) {
    return null;
  }
  return _browserLocalWorkspaceSelectionsPersistence.restore(
    workspacePath: normalizedPath,
  );
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
    return 'granted';
  }
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
