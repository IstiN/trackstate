from __future__ import annotations

import json

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
)
from testing.tests.support.stored_workspace_profiles_runtime import (
    _workspace_token_storage_keys,
)


class Ts980RestorePersistenceRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        workspace_token_profile_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
        )
        self._workspace_state = workspace_state
        self._workspace_token_profile_ids = tuple(workspace_token_profile_ids)
        self.console_events: list[dict[str, str]] = []
        self.page_errors: list[str] = []

    def __enter__(self):
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError(
                "TS-980 restore persistence runtime expected a browser context and page.",
            )
        self._context.add_init_script(
            script=_build_one_time_workspace_preload_script(
                self._workspace_state,
                repository=self._repository,
                token=self._token,
                workspace_token_profile_ids=self._workspace_token_profile_ids,
            ),
        )
        self._context.add_init_script(
            script=_restorable_directory_handle_persistence_script(),
        )
        self._context.add_init_script(script=_manual_reauth_probe_script())
        self._page.on("console", self._record_console_event)
        self._page.on("pageerror", self._record_page_error)
        return session

    def _record_console_event(self, message) -> None:
        self.console_events.append(
            {
                "level": str(message.type),
                "text": str(message.text),
            },
        )

    def _record_page_error(self, error: object) -> None:
        self.page_errors.append(str(error))


def install_restorable_directory_picker(
    *,
    tracker_page: TrackStateTrackerPage,
    directory_snapshot: dict[str, object],
) -> None:
    tracker_page.session.evaluate(
        """
        (snapshot) => {
          const normalizeArgs = (args) => {
            try {
              return JSON.parse(JSON.stringify(args));
            } catch (_) {
              return Array.from(args, (value) => String(value));
            }
          };
          const manualProbe = window.__ts980ManualReauthProbe || null;
          const recordProbe = (bucket, args) => {
            if (!manualProbe || !Array.isArray(manualProbe[bucket])) {
              return;
            }
            manualProbe[bucket].push({
              callNumber: manualProbe[bucket].length + 1,
              args: normalizeArgs(args),
            });
          };
          const state = window.__ts980RestorableDirectoryPickerState = {
            calls: [],
            selectedDirectoryName: null,
            snapshotRootPath:
              typeof snapshot?.rootPath === 'string' ? snapshot.rootPath : null,
            seededPaths: Array.isArray(snapshot?.files)
              ? snapshot.files
                  .map((entry) => (entry && typeof entry.path === 'string' ? entry.path : null))
                  .filter((entry) => entry !== null)
              : [],
            errors: [],
            source: 'real-workspace-snapshot',
          };
          const createHandleFromSnapshot =
            typeof globalThis.__ts980CreateDirectoryHandleFromSnapshot === 'function'
              ? globalThis.__ts980CreateDirectoryHandleFromSnapshot
              : null;
          if (!createHandleFromSnapshot) {
            state.errors.push(
              'Missing __ts980CreateDirectoryHandleFromSnapshot helper before installing picker.',
            );
            return;
          }
          const rootHandle = createHandleFromSnapshot(snapshot);
          globalThis.showDirectoryPicker = async (...args) => {
            state.calls.push({
              callNumber: state.calls.length + 1,
              args: normalizeArgs(args),
            });
            recordProbe('showDirectoryPickerCalls', args);
            state.selectedDirectoryName = rootHandle.name;
            return rootHandle;
          };
        }
        """,
        arg=directory_snapshot,
    )


def read_manual_reauth_probe(tracker_page: TrackStateTrackerPage) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        """
        () => {
          const probe = window.__ts980ManualReauthProbe || {};
          return {
            showDirectoryPickerCalls: Array.isArray(probe.showDirectoryPickerCalls)
              ? probe.showDirectoryPickerCalls
              : [],
            requestPermissionCalls: Array.isArray(probe.requestPermissionCalls)
              ? probe.requestPermissionCalls
              : [],
            queryPermissionCalls: Array.isArray(probe.queryPermissionCalls)
              ? probe.queryPermissionCalls
              : [],
            wrapErrors: Array.isArray(probe.wrapErrors) ? probe.wrapErrors : [],
          };
        }
        """,
    )
    if not isinstance(payload, dict):
        return {
            "showDirectoryPickerCalls": [],
            "requestPermissionCalls": [],
            "queryPermissionCalls": [],
            "wrapErrors": [],
        }
    return {
        "showDirectoryPickerCalls": list(payload.get("showDirectoryPickerCalls", [])),
        "requestPermissionCalls": list(payload.get("requestPermissionCalls", [])),
        "queryPermissionCalls": list(payload.get("queryPermissionCalls", [])),
        "wrapErrors": list(payload.get("wrapErrors", [])),
    }


def read_restorable_directory_picker_state(
    tracker_page: TrackStateTrackerPage,
) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        """
        () => {
          const state = window.__ts980RestorableDirectoryPickerState || {};
          return {
            calls: Array.isArray(state.calls) ? state.calls : [],
            selectedDirectoryName:
              typeof state.selectedDirectoryName === 'string'
                ? state.selectedDirectoryName
                : null,
            snapshotRootPath:
              typeof state.snapshotRootPath === 'string'
                ? state.snapshotRootPath
                : null,
            seededPaths: Array.isArray(state.seededPaths) ? state.seededPaths : [],
            errors: Array.isArray(state.errors) ? state.errors : [],
            source: typeof state.source === 'string' ? state.source : null,
          };
        }
        """,
    )
    if not isinstance(payload, dict):
        return {
            "calls": [],
            "selectedDirectoryName": None,
            "snapshotRootPath": None,
            "seededPaths": [],
            "errors": [],
            "source": None,
        }
    return {
        "calls": list(payload.get("calls", [])),
        "selectedDirectoryName": payload.get("selectedDirectoryName"),
        "snapshotRootPath": payload.get("snapshotRootPath"),
        "seededPaths": list(payload.get("seededPaths", [])),
        "errors": list(payload.get("errors", [])),
        "source": payload.get("source"),
    }


def _build_one_time_workspace_preload_script(
    workspace_state: dict[str, object],
    *,
    repository: str,
    token: str,
    workspace_token_profile_ids: tuple[str, ...],
) -> str:
    serialized_state = json.dumps(json.dumps(workspace_state))
    workspace_token_keys = _workspace_token_storage_keys(
        workspace_state,
        workspace_token_profile_ids=workspace_token_profile_ids,
    )
    return "".join(
        [
            "(() => {",
            f"const state = {serialized_state};",
            f"const token = {json.dumps(token)};",
            "for (const key of [",
            "  'trackstate.workspaceProfiles.state',",
            "  'flutter.trackstate.workspaceProfiles.state',",
            "]) {",
            "  if (window.localStorage.getItem(key) === null) {",
            "    window.localStorage.setItem(key, state);",
            "  }",
            "}",
            "for (const key of [",
            *[f"  {json.dumps(key)}," for key in workspace_token_keys],
            "]) {",
            "  if (window.localStorage.getItem(key) === null) {",
            "    window.localStorage.setItem(key, token);",
            "  }",
            "}",
            "})();",
        ],
    )


def _restorable_directory_handle_persistence_script() -> str:
    return """
    (() => {
      const snapshotStoragePrefix = '__ts980.persistedDirectorySnapshot:';
      const cloneJson = (value) => JSON.parse(JSON.stringify(value));
      const normalizeWorkspacePath = (value) => String(value ?? '').trim();
      const persistSnapshot = (workspacePath, snapshot) => {
        const normalizedPath = normalizeWorkspacePath(workspacePath);
        if (!normalizedPath || !snapshot || typeof snapshot !== 'object') {
          return;
        }
        window.localStorage.setItem(
          `${snapshotStoragePrefix}${normalizedPath}`,
          JSON.stringify(snapshot),
        );
      };
      const readPersistedSnapshot = (workspacePath) => {
        const normalizedPath = normalizeWorkspacePath(workspacePath);
        if (!normalizedPath) {
          return null;
        }
        const raw = window.localStorage.getItem(
          `${snapshotStoragePrefix}${normalizedPath}`,
        );
        if (!raw) {
          return null;
        }
        try {
          return JSON.parse(raw);
        } catch (_) {
          window.localStorage.removeItem(`${snapshotStoragePrefix}${normalizedPath}`);
          return null;
        }
      };
      const clearPersistedSnapshot = (workspacePath) => {
        const normalizedPath = normalizeWorkspacePath(workspacePath);
        if (!normalizedPath) {
          return;
        }
        window.localStorage.removeItem(`${snapshotStoragePrefix}${normalizedPath}`);
      };
      const clearAllPersistedSnapshots = () => {
        const keys = [];
        for (let index = 0; index < window.localStorage.length; index += 1) {
          const key = window.localStorage.key(index);
          if (typeof key === 'string' && key.startsWith(snapshotStoragePrefix)) {
            keys.push(key);
          }
        }
        for (const key of keys) {
          window.localStorage.removeItem(key);
        }
      };
      const textEncoder = new TextEncoder();
      const decodeBase64 = (value) => {
        const raw = atob(typeof value === 'string' ? value : '');
        const bytes = new Uint8Array(raw.length);
        for (let index = 0; index < raw.length; index += 1) {
          bytes[index] = raw.charCodeAt(index);
        }
        return bytes;
      };
      const cloneBytes = (value) => new Uint8Array(value);
      const cloneArrayBuffer = (value) => {
        const view = value instanceof Uint8Array
          ? value
          : new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
        return view.slice().buffer;
      };
      const createDirectoryNode = (name) => ({
        kind: 'directory',
        name,
        children: new Map(),
      });
      const createFileNode = (name, bytes) => ({
        kind: 'file',
        name,
        bytes: cloneBytes(bytes),
      });
      const buildDirectoryTree = (snapshot) => {
        const rootName = typeof snapshot?.rootName === 'string' && snapshot.rootName.trim()
          ? snapshot.rootName.trim()
          : 'trackstate-ts980-workspace';
        const rootNode = createDirectoryNode(rootName);
        for (const entry of Array.isArray(snapshot?.files) ? snapshot.files : []) {
          if (!entry || typeof entry.path !== 'string' || typeof entry.base64 !== 'string') {
            continue;
          }
          const segments = entry.path
            .split('/')
            .map((segment) => segment.trim())
            .filter((segment) => segment.length > 0);
          if (segments.length === 0) {
            continue;
          }
          let current = rootNode;
          for (const segment of segments.slice(0, -1)) {
            const existing = current.children.get(segment);
            if (existing && existing.kind !== 'directory') {
              throw new DOMException(
                `Could not create directory ${segment}. A file already exists at that path.`,
                'TypeMismatchError',
              );
            }
            if (existing) {
              current = existing;
              continue;
            }
            const created = createDirectoryNode(segment);
            current.children.set(segment, created);
            current = created;
          }
          current.children.set(
            segments.at(-1),
            createFileNode(segments.at(-1), decodeBase64(entry.base64)),
          );
        }
        return { rootName, rootNode };
      };
      const notFoundError = (message) => new DOMException(message, 'NotFoundError');
      const typeMismatchError = (message) =>
        new DOMException(message, 'TypeMismatchError');
      const sameEntry = (left, right) => {
        const leftPath = Array.isArray(left?.__ts980Path) ? left.__ts980Path : null;
        const rightPath = Array.isArray(right?.__ts980Path) ? right.__ts980Path : null;
        return (
          Array.isArray(leftPath)
          && Array.isArray(rightPath)
          && leftPath.length === rightPath.length
          && leftPath.every((segment, index) => segment === rightPath[index])
        );
      };
      const attachMetadata = (handle, node, pathSegments, snapshot) => {
        Object.defineProperty(handle, '__ts980Node', {
          configurable: true,
          enumerable: false,
          value: node,
        });
        Object.defineProperty(handle, '__ts980Path', {
          configurable: true,
          enumerable: false,
          value: [...pathSegments],
        });
        Object.defineProperty(handle, '__ts980DirectorySnapshot', {
          configurable: true,
          enumerable: false,
          value: cloneJson(snapshot),
        });
        return handle;
      };
      const createWritable = (node) => {
        let nextBytes = cloneBytes(node.bytes);
        const writeChunk = (value) => {
          if (typeof value === 'string') {
            nextBytes = textEncoder.encode(value);
            return;
          }
          if (value instanceof Uint8Array) {
            nextBytes = cloneBytes(value);
            return;
          }
          if (value instanceof ArrayBuffer) {
            nextBytes = new Uint8Array(value.slice(0));
            return;
          }
          if (ArrayBuffer.isView(value)) {
            nextBytes = new Uint8Array(
              value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength),
            );
            return;
          }
          nextBytes = textEncoder.encode(String(value ?? ''));
        };
        return {
          async write(chunk) {
            if (chunk && typeof chunk === 'object' && 'type' in chunk) {
              if (chunk.type === 'truncate') {
                nextBytes = nextBytes.slice(0, Number(chunk.size) || 0);
                return;
              }
              if (chunk.type === 'write') {
                writeChunk(chunk.data);
                return;
              }
            }
            writeChunk(chunk);
          },
          async close() {
            node.bytes = cloneBytes(nextBytes);
          },
        };
      };
      const createHandleFactory = (snapshot) => {
        const { rootName, rootNode } = buildDirectoryTree(snapshot);
        const createFileHandle = (node, pathSegments) =>
          attachMetadata(
            {
              kind: 'file',
              name: node.name,
              async queryPermission() {
                return 'granted';
              },
              async requestPermission() {
                return 'granted';
              },
              async isSameEntry(other) {
                return sameEntry(this, other);
              },
              async getFile() {
                return new File([cloneArrayBuffer(node.bytes)], node.name, {
                  type: 'application/octet-stream',
                });
              },
              async createWritable() {
                return createWritable(node);
              },
            },
            node,
            pathSegments,
            snapshot,
          );
        const createHandle = (node, pathSegments) =>
          node.kind === 'directory'
            ? createDirectoryHandle(node, pathSegments)
            : createFileHandle(node, pathSegments);
        const createDirectoryHandle = (node, pathSegments) =>
          attachMetadata(
            {
              kind: 'directory',
              name: node.name,
              async queryPermission() {
                return 'granted';
              },
              async requestPermission() {
                return 'granted';
              },
              async isSameEntry(other) {
                return sameEntry(this, other);
              },
              async *values() {
                for (const child of node.children.values()) {
                  yield createHandle(child, [...pathSegments, child.name]);
                }
              },
              async *keys() {
                for (const childName of node.children.keys()) {
                  yield childName;
                }
              },
              async *entries() {
                for (const [childName, child] of node.children.entries()) {
                  yield [childName, createHandle(child, [...pathSegments, childName])];
                }
              },
              async getDirectoryHandle(name, options = {}) {
                const normalized = String(name ?? '').trim();
                if (!normalized) {
                  throw notFoundError('Directory name must not be empty.');
                }
                let child = node.children.get(normalized);
                if (!child) {
                  if (options && options.create) {
                    child = createDirectoryNode(normalized);
                    node.children.set(normalized, child);
                  } else {
                    throw notFoundError(`Directory ${normalized} does not exist.`);
                  }
                }
                if (child.kind !== 'directory') {
                  throw typeMismatchError(
                    `Expected ${normalized} to be a directory but found a file.`,
                  );
                }
                return createDirectoryHandle(child, [...pathSegments, normalized]);
              },
              async getFileHandle(name, options = {}) {
                const normalized = String(name ?? '').trim();
                if (!normalized) {
                  throw notFoundError('File name must not be empty.');
                }
                let child = node.children.get(normalized);
                if (!child) {
                  if (options && options.create) {
                    child = createFileNode(normalized, new Uint8Array());
                    node.children.set(normalized, child);
                  } else {
                    throw notFoundError(`File ${normalized} does not exist.`);
                  }
                }
                if (child.kind !== 'file') {
                  throw typeMismatchError(
                    `Expected ${normalized} to be a file but found a directory.`,
                  );
                }
                return createFileHandle(child, [...pathSegments, normalized]);
              },
              async removeEntry(name) {
                const normalized = String(name ?? '').trim();
                if (!node.children.delete(normalized)) {
                  throw notFoundError(`${normalized} does not exist.`);
                }
              },
              async resolve(handle) {
                const descendant = Array.isArray(handle?.__ts980Path)
                  ? handle.__ts980Path
                  : null;
                if (!Array.isArray(descendant) || descendant.length < pathSegments.length) {
                  return null;
                }
                for (let index = 0; index < pathSegments.length; index += 1) {
                  if (descendant[index] !== pathSegments[index]) {
                    return null;
                  }
                }
                return descendant.slice(pathSegments.length);
              },
            },
            node,
            pathSegments,
            snapshot,
          );
        return createDirectoryHandle(rootNode, [rootName]);
      };
      globalThis.__ts980CreateDirectoryHandleFromSnapshot = (snapshot) => {
        if (!snapshot || typeof snapshot !== 'object') {
          return null;
        }
        return createHandleFactory(snapshot);
      };
      globalThis.__ts980PersistDirectorySnapshot = persistSnapshot;
      globalThis.__ts980ReadPersistedDirectorySnapshot = readPersistedSnapshot;
      const originalIndexedDb = window.indexedDB;
      const interceptedDatabasePrefix = 'trackstate.browserLocalWorkspaceSelections:';
      const createRequest = ({ result = null, operation = null }) => ({
        result,
        error: null,
        operation,
        onsuccess: null,
        onerror: null,
      });
      const completeRequest = (request, value) => {
        request.result = value;
        setTimeout(() => {
          if (typeof request.onsuccess === 'function') {
            request.onsuccess(new Event('success'));
          }
        }, 0);
      };
      const failRequest = (request, error) => {
        request.error = error;
        setTimeout(() => {
          if (typeof request.onerror === 'function') {
            request.onerror(new Event('error'));
          }
        }, 0);
      };
      const completeTransaction = (transaction) => {
        setTimeout(() => {
          if (typeof transaction.oncomplete === 'function') {
            transaction.oncomplete(new Event('complete'));
          }
        }, 0);
      };
      const createTransaction = () => {
        const transaction = {
          error: null,
          oncomplete: null,
          onabort: null,
          onerror: null,
          objectStore() {
            return {
              put(value, key) {
                const request = createRequest({ operation: 'put' });
                setTimeout(() => {
                  try {
                    const snapshot =
                      value && typeof value === 'object' && value.__ts980DirectorySnapshot
                        ? cloneJson(value.__ts980DirectorySnapshot)
                        : null;
                    if (snapshot === null) {
                      throw new TypeError(
                        'Missing __ts980DirectorySnapshot metadata for fake IndexedDB persistence.',
                      );
                    }
                    persistSnapshot(key, snapshot);
                    completeRequest(request, key);
                    completeTransaction(transaction);
                  } catch (error) {
                    failRequest(request, error);
                    transaction.error = error;
                    if (typeof transaction.onerror === 'function') {
                      transaction.onerror(new Event('error'));
                    }
                  }
                }, 0);
                return request;
              },
              get(key) {
                const request = createRequest({ operation: 'get' });
                setTimeout(() => {
                  try {
                    const snapshot = readPersistedSnapshot(key);
                    const handle = snapshot
                      ? globalThis.__ts980CreateDirectoryHandleFromSnapshot(snapshot)
                      : null;
                    completeRequest(request, handle);
                    completeTransaction(transaction);
                  } catch (error) {
                    failRequest(request, error);
                    transaction.error = error;
                    if (typeof transaction.onerror === 'function') {
                      transaction.onerror(new Event('error'));
                    }
                  }
                }, 0);
                return request;
              },
              delete(key) {
                const request = createRequest({ operation: 'delete' });
                setTimeout(() => {
                  try {
                    clearPersistedSnapshot(key);
                    completeRequest(request, undefined);
                    completeTransaction(transaction);
                  } catch (error) {
                    failRequest(request, error);
                    transaction.error = error;
                    if (typeof transaction.onerror === 'function') {
                      transaction.onerror(new Event('error'));
                    }
                  }
                }, 0);
                return request;
              },
              clear() {
                const request = createRequest({ operation: 'clear' });
                setTimeout(() => {
                  try {
                    clearAllPersistedSnapshots();
                    completeRequest(request, undefined);
                    completeTransaction(transaction);
                  } catch (error) {
                    failRequest(request, error);
                    transaction.error = error;
                    if (typeof transaction.onerror === 'function') {
                      transaction.onerror(new Event('error'));
                    }
                  }
                }, 0);
                return request;
              },
            };
          },
        };
        return transaction;
      };
      const createDatabase = () => ({
        objectStoreNames: {
          contains(name) {
            return String(name ?? '') === 'directoryHandles';
          },
        },
        createObjectStore() {
          return {};
        },
        transaction() {
          return createTransaction();
        },
        close() {},
      });
      const fakeIndexedDb = {
        open(name) {
          const databaseName = String(name ?? '');
          if (
            !databaseName.startsWith(interceptedDatabasePrefix)
            && originalIndexedDb
            && typeof originalIndexedDb.open === 'function'
          ) {
            return originalIndexedDb.open.apply(originalIndexedDb, arguments);
          }
          const request = {
            result: null,
            error: null,
            onsuccess: null,
            onerror: null,
            onblocked: null,
            onupgradeneeded: null,
          };
          setTimeout(() => {
            try {
              request.result = createDatabase();
              if (typeof request.onupgradeneeded === 'function') {
                request.onupgradeneeded(new Event('upgradeneeded'));
              }
              if (typeof request.onsuccess === 'function') {
                request.onsuccess(new Event('success'));
              }
            } catch (error) {
              request.error = error;
              if (typeof request.onerror === 'function') {
                request.onerror(new Event('error'));
              }
            }
          }, 0);
          return request;
        },
      };
      Object.defineProperty(window, 'indexedDB', {
        configurable: true,
        writable: true,
        value: fakeIndexedDb,
      });
    })();
    """


def _manual_reauth_probe_script() -> str:
    return """
    (() => {
      const state = window.__ts980ManualReauthProbe = {
        showDirectoryPickerCalls: [],
        requestPermissionCalls: [],
        queryPermissionCalls: [],
        wrapErrors: [],
      };
      const serialize = (value) => {
        try {
          return JSON.parse(JSON.stringify(value));
        } catch (error) {
          state.wrapErrors.push(String(error));
          return String(value);
        }
      };
      const wrap = (target, key, bucket) => {
        if (!target || typeof target[key] !== 'function') {
          return;
        }
        const original = target[key];
        target[key] = async function(...args) {
          state[bucket].push({
            callNumber: state[bucket].length + 1,
            args: serialize(args),
          });
          return await original.apply(this, args);
        };
      };
      wrap(window, 'showDirectoryPicker', 'showDirectoryPickerCalls');
      const fileSystemHandleProto = window.FileSystemHandle && window.FileSystemHandle.prototype;
      wrap(fileSystemHandleProto, 'requestPermission', 'requestPermissionCalls');
      wrap(fileSystemHandleProto, 'queryPermission', 'queryPermissionCalls');
    })();
    """
