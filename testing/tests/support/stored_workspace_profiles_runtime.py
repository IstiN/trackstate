from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.parse import quote

try:
    from testing.frameworks.python.playwright_web_app_session import (
        PlaywrightWebAppRuntime,
        PlaywrightStoredTokenWebAppRuntime,
        PlaywrightWebAppSession,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised in no-Playwright unit envs
    class PlaywrightWebAppSession:  # type: ignore[no-redef]
        pass

    class PlaywrightWebAppRuntime:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self._context = None
            self._page = None

        def __enter__(self):
            raise ModuleNotFoundError("playwright")

    class PlaywrightStoredTokenWebAppRuntime(  # type: ignore[no-redef]
        PlaywrightWebAppRuntime,
    ):
        def __init__(self, *, repository: str, token: str) -> None:
            super().__init__()
            self._repository = repository
            self._token = token


class WorkspaceProfilesRuntime(PlaywrightWebAppRuntime):
    def __init__(
        self,
        *,
        workspace_state: dict[str, object],
    ) -> None:
        super().__init__()
        self._workspace_state = workspace_state

    def __enter__(self) -> PlaywrightWebAppSession:
        session = super().__enter__()
        if self._context is None:
            raise RuntimeError(
                "WorkspaceProfilesRuntime expected a browser context.",
            )
        script = _build_preload_script(self._workspace_state)
        self._context.add_init_script(script=script)
        if self._page is not None:
            self._page.add_init_script(script=script)
        return session


class StoredWorkspaceProfilesRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        workspace_token_profile_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._workspace_state = workspace_state
        self._workspace_token_profile_ids = tuple(workspace_token_profile_ids)

    def __enter__(self) -> PlaywrightWebAppSession:
        session = super().__enter__()
        if self._context is None:
            raise RuntimeError(
                "StoredWorkspaceProfilesRuntime expected a browser context.",
            )
        script = _build_preload_script(
            self._workspace_state,
            repository=self._repository,
            token=self._token,
            workspace_token_profile_ids=self._workspace_token_profile_ids,
        )
        self._context.add_init_script(script=script)
        if self._page is not None:
            self._page.add_init_script(script=script)
        return session


def _build_preload_script(
    workspace_state: dict[str, object],
    *,
    repository: str | None = None,
    token: str | None = None,
    workspace_token_profile_ids: tuple[str, ...] = (),
) -> str:
    serialized_state = json.dumps(workspace_state)
    local_workspace_fixtures = _local_workspace_restore_fixtures(workspace_state)
    scripts = [
        "(() => {",
        f"const state = {json.dumps(serialized_state)};",
        "for (const key of [",
        "  'trackstate.workspaceProfiles.state',",
        "  'flutter.trackstate.workspaceProfiles.state',",
        "]) {",
        "  window.localStorage.setItem(key, state);",
        "}",
    ]
    if repository and token:
        repository_keys = {
            repository.replace("/", "."),
            repository.lower().replace("/", "."),
        }
        workspace_storage_keys = _workspace_token_storage_keys(
            workspace_state,
            workspace_token_profile_ids=workspace_token_profile_ids,
        )
        scripts.extend(
            [
                f"const token = {json.dumps(token)};",
                "for (const key of [",
                *[
                    f"  {json.dumps(storage_key)},"
                    for repository_storage_key in sorted(repository_keys)
                    for storage_key in (
                        f"trackstate.githubToken.{repository_storage_key}",
                        f"flutter.trackstate.githubToken.{repository_storage_key}",
                    )
                ],
                *[f"  {json.dumps(key)}," for key in workspace_storage_keys],
                "]) {",
                "  window.localStorage.setItem(key, token);",
                "}",
            ],
        )
    if local_workspace_fixtures:
        serialized_fixtures = json.dumps(local_workspace_fixtures)
        scripts.extend(
            [
                f"const localWorkspaceFixtures = {serialized_fixtures};",
                """
const createRestorableLocalWorkspaceHandle = (fixture) => {
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
  const notFoundError = (message) => new DOMException(message, 'NotFoundError');
  const typeMismatchError = (message) =>
    new DOMException(message, 'TypeMismatchError');
  const rootName =
    typeof fixture?.rootName === 'string' && fixture.rootName.trim()
      ? fixture.rootName.trim()
      : 'trackstate-local-workspace';
  const rootNode = createDirectoryNode(rootName);
  for (const entry of Array.isArray(fixture?.files) ? fixture.files : []) {
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
        throw typeMismatchError(
          `Could not create directory ${segment}. A file already exists at that path.`,
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
  const sameEntry = (left, right) => {
    const leftPath = Array.isArray(left?.__trackstateFixturePath)
      ? left.__trackstateFixturePath
      : null;
    const rightPath = Array.isArray(right?.__trackstateFixturePath)
      ? right.__trackstateFixturePath
      : null;
    return (
      Array.isArray(leftPath)
      && Array.isArray(rightPath)
      && leftPath.length === rightPath.length
      && leftPath.every((segment, index) => segment === rightPath[index])
    );
  };
  const attachMetadata = (handle, node, pathSegments) => {
    Object.defineProperty(handle, '__trackstateFixtureNode', {
      configurable: true,
      enumerable: false,
      value: node,
    });
    Object.defineProperty(handle, '__trackstateFixturePath', {
      configurable: true,
      enumerable: false,
      value: [...pathSegments],
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
          const descendant = Array.isArray(handle?.__trackstateFixturePath)
            ? handle.__trackstateFixturePath
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
    );
  return createDirectoryHandle(rootNode, [rootName]);
};
const markerPrefix =
  `trackstate.browserLocalWorkspaceSelections.marker:${window.location.pathname}${window.location.search}:`;
const fixtureHandles =
  globalThis.__trackstateStoredWorkspaceRuntimeFixtureHandles instanceof Map
    ? globalThis.__trackstateStoredWorkspaceRuntimeFixtureHandles
    : new Map();
for (const fixture of localWorkspaceFixtures) {
  if (!fixture || typeof fixture.workspacePath !== 'string') {
    continue;
  }
  const workspacePath = fixture.workspacePath.trim();
  if (!workspacePath) {
    continue;
  }
  fixtureHandles.set(workspacePath, createRestorableLocalWorkspaceHandle(fixture));
  window.localStorage.setItem(`${markerPrefix}${workspacePath}`, '1');
}
globalThis.__trackstateStoredWorkspaceRuntimeFixtureHandles = fixtureHandles;
if (
  !globalThis.__trackstateStoredWorkspaceRuntimeIndexedDbGetPatched &&
  typeof globalThis.IDBObjectStore?.prototype?.get === 'function'
) {
  globalThis.__trackstateStoredWorkspaceRuntimeIndexedDbGetPatched = true;
  const originalGet = globalThis.IDBObjectStore.prototype.get;
  globalThis.IDBObjectStore.prototype.get = function patchedTrackStateRuntimeGet(key) {
    const fixtures = globalThis.__trackstateStoredWorkspaceRuntimeFixtureHandles;
    const workspacePath = typeof key === 'string' ? key : String(key ?? '');
    if (
      this?.name === 'directoryHandles' &&
      fixtures instanceof Map &&
      fixtures.has(workspacePath)
    ) {
      const request = {
        result: fixtures.get(workspacePath),
        error: null,
        onsuccess: null,
        onerror: null,
      };
      queueMicrotask(() => {
        if (typeof request.onsuccess === 'function') {
          request.onsuccess(new Event('success'));
        }
      });
      return request;
    }
    return originalGet.call(this, key);
  };
}
""",
            ],
        )
    scripts.append("})();")
    return "".join(scripts)


def _workspace_token_storage_keys(
    workspace_state: dict[str, object],
    *,
    workspace_token_profile_ids: tuple[str, ...] = (),
) -> list[str]:
    raw_profiles = workspace_state.get("profiles", [])
    if not isinstance(raw_profiles, list):
        return []
    allowed_profile_ids = {profile_id for profile_id in workspace_token_profile_ids if profile_id}
    if not allowed_profile_ids:
        return []
    keys: list[str] = []
    for profile in raw_profiles:
        if not isinstance(profile, dict):
            continue
        workspace_id = str(profile.get("id", "")).strip()
        if not workspace_id or workspace_id not in allowed_profile_ids:
            continue
        encoded_id = quote(workspace_id, safe="")
        keys.extend(
            [
                f"trackstate.githubToken.workspace.{encoded_id}",
                f"flutter.trackstate.githubToken.workspace.{encoded_id}",
            ],
        )
    return keys


def _local_workspace_restore_fixtures(
    workspace_state: dict[str, object],
) -> list[dict[str, object]]:
    raw_profiles = workspace_state.get("profiles", [])
    if not isinstance(raw_profiles, list):
        return []
    fixtures: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    for profile in raw_profiles:
        if not isinstance(profile, dict):
            continue
        if str(profile.get("targetType", "")).strip() != "local":
            continue
        workspace_path = str(profile.get("target", "")).strip()
        if not workspace_path or workspace_path in seen_paths:
            continue
        local_path = Path(workspace_path)
        if not local_path.is_dir():
            continue
        files = _workspace_directory_snapshot(local_path)
        if not files:
            continue
        fixtures.append(
            {
                "workspacePath": workspace_path,
                "rootName": local_path.name,
                "files": files,
            },
        )
        seen_paths.add(workspace_path)
    return fixtures


def _workspace_directory_snapshot(local_path: Path) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for absolute_path in sorted(local_path.rglob("*")):
        if not absolute_path.is_file():
            continue
        relative_path = absolute_path.relative_to(local_path).as_posix()
        if _should_skip_snapshot_path(relative_path):
            continue
        files.append(
            {
                "path": relative_path,
                "base64": base64.b64encode(absolute_path.read_bytes()).decode("ascii"),
            },
        )
    return files


def _should_skip_snapshot_path(relative_path: str) -> bool:
    normalized = relative_path.strip().replace("\\", "/")
    if not normalized:
        return True
    if normalized.startswith(".git/objects/"):
        return True
    if normalized.startswith(".git/hooks/"):
        return True
    if normalized.startswith(".git/logs/"):
        return True
    if normalized == ".git/index.lock":
        return True
    return False
