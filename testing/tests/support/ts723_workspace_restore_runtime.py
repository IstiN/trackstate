from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath

from playwright.sync_api import sync_playwright

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
    PlaywrightWebAppSession,
)
from testing.tests.support.stored_workspace_profiles_runtime import (
    _workspace_token_storage_keys,
)


@dataclass(frozen=True)
class WorkspaceRestoreConsoleEvent:
    level: str
    text: str


class Ts723WorkspaceRestoreRuntime(PlaywrightStoredTokenWebAppRuntime):
    RUNTIME_PROBE_PREFIX = "[TS-893][local-revalidation]"
    RUNTIME_ACTIVITY_PREFIX = "[TS-893][local-revalidation-activity]"

    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        workspace_token_profile_ids: tuple[str, ...] = (),
        viewport: dict[str, int] | None = None,
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._workspace_state = workspace_state
        self._workspace_token_profile_ids = tuple(workspace_token_profile_ids)
        self._viewport = viewport or {"width": 1440, "height": 900}
        self._active_local_handle_name = _active_local_handle_name(workspace_state)
        self.console_events: list[WorkspaceRestoreConsoleEvent] = []
        self.page_errors: list[str] = []

    def __enter__(self) -> PlaywrightWebAppSession:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(viewport=self._viewport)
        self._context.route("https://api.github.com/**", self._handle_github_api_route)
        self._context.add_init_script(script=self._build_preload_script())
        self._page = self._context.new_page()
        self._page.on("console", self._record_console_event)
        self._page.on("pageerror", self._record_page_error)
        return PlaywrightWebAppSession(self._page)

    def storage_snapshot(self) -> dict[str, str | None]:
        if self._page is None:
            raise RuntimeError(
                "TS-723 storage snapshot requested before the page was created.",
            )
        payload = self._page.evaluate(
            """
            (keys) => {
              const snapshot = {};
              for (const key of keys) {
                snapshot[key] = window.localStorage.getItem(key);
              }
              return snapshot;
            }
            """,
            [
                "trackstate.workspaceProfiles.state",
                "flutter.trackstate.workspaceProfiles.state",
                f"trackstate.githubToken.{self._repository_storage_key}",
                f"flutter.trackstate.githubToken.{self._repository_storage_key}",
            ],
        )
        if not isinstance(payload, dict):
            raise AssertionError(f"TS-723 expected a storage snapshot map, got: {payload!r}")
        return {
            str(key): (None if value is None else str(value))
            for key, value in payload.items()
        }

    def _build_preload_script(self) -> str:
        serialized_workspace_state = json.dumps(self._workspace_state)
        workspace_token_storage_keys = _workspace_token_storage_keys(
            self._workspace_state,
            workspace_token_profile_ids=self._workspace_token_profile_ids,
        )
        return f"""
(() => {{
  const repositoryStorageKey = {json.dumps(self._repository_storage_key)};
  const token = {json.dumps(self._token)};
  const workspaceState = {json.dumps(serialized_workspace_state)};
  const workspaceTokenStorageKeys = {json.dumps(workspace_token_storage_keys)};
  const trackedHandleName = {json.dumps(self._active_local_handle_name)};
  const probePrefix = {json.dumps(self.RUNTIME_PROBE_PREFIX)};
  const activityPrefix = {json.dumps(self.RUNTIME_ACTIVITY_PREFIX)};
  const trackedHandleLineage = new WeakMap();

  for (const key of [
    'trackstate.workspaceProfiles.state',
    'flutter.trackstate.workspaceProfiles.state',
  ]) {{
    window.localStorage.setItem(key, workspaceState);
  }}

  for (const key of [
    `trackstate.githubToken.${{repositoryStorageKey}}`,
    `flutter.trackstate.githubToken.${{repositoryStorageKey}}`,
    ...workspaceTokenStorageKeys,
  ]) {{
    window.localStorage.setItem(key, token);
  }}

  const handleName = (handle) => {{
    if (!handle || typeof handle !== 'object' || !('name' in handle)) {{
      return null;
    }}
    const rawName = handle.name;
    if (typeof rawName !== 'string') {{
      return null;
    }}
    const normalized = rawName.trim();
    return normalized || null;
  }};

  const extendLineage = (lineage, childName) => {{
    if (!Array.isArray(lineage) || lineage.length === 0) {{
      return null;
    }}
    if (typeof childName !== 'string' || !childName.trim()) {{
      return [...lineage];
    }}
    const normalizedChildName = childName.trim();
    if (lineage[lineage.length - 1] === normalizedChildName) {{
      return [...lineage];
    }}
    return [...lineage, normalizedChildName];
  }};

  const trackHandle = (handle, lineage) => {{
    if (!handle || typeof handle !== 'object' || !Array.isArray(lineage) || lineage.length === 0) {{
      return handle;
    }}
    trackedHandleLineage.set(handle, [...lineage]);
    return handle;
  }};

  const trackedLineageForHandle = (handle) => {{
    if (!handle || typeof handle !== 'object') {{
      return null;
    }}
    const existing = trackedHandleLineage.get(handle);
    if (Array.isArray(existing) && existing.length > 0) {{
      return [...existing];
    }}
    const name = handleName(handle);
    if (trackedHandleName && name === trackedHandleName) {{
      const rootLineage = [trackedHandleName];
      trackedHandleLineage.set(handle, rootLineage);
      return [...rootLineage];
    }}
    return null;
  }};

  const isTrackedHandle = (handle) => {{
    return Array.isArray(trackedLineageForHandle(handle));
  }};

  const trackDescendantHandle = (parentLineage, handle, childName) => {{
    const lineage = extendLineage(parentLineage, childName ?? handleName(handle));
    if (!lineage) {{
      return handle;
    }}
    return trackHandle(handle, lineage);
  }};

  const trackReturnedValue = (value, lineage, args) => {{
    if (!lineage) {{
      return value;
    }}
    if (Array.isArray(value)) {{
      if (value.length >= 2) {{
        const entryName = typeof value[0] === 'string' ? value[0] : null;
        trackDescendantHandle(lineage, value[1], entryName);
      }}
      return value;
    }}
    const requestedChildName =
      Array.isArray(args) && typeof args[0] === 'string' ? args[0] : null;
    return trackDescendantHandle(lineage, value, requestedChildName);
  }};

  const normalizeError = (error) => {{
    if (!error) {{
      return 'Unknown error';
    }}
    if (typeof error === 'string') {{
      return error;
    }}
    if (typeof error === 'object') {{
      const name = 'name' in error ? String(error.name || '') : '';
      const message = 'message' in error ? String(error.message || '') : '';
      const combined = [name, message].filter(Boolean).join(': ');
      if (combined) {{
        return combined;
      }}
    }}
    try {{
      return String(error);
    }} catch (_) {{
      return 'Unserializable error';
    }}
  }};

  const emitProbe = (details) => {{
    console.debug(`${{probePrefix}} ${{JSON.stringify(details)}}`);
  }};

  const emitActivity = (details) => {{
    console.debug(`${{activityPrefix}} ${{JSON.stringify(details)}}`);
  }};

  const wrapAsyncIterable = (iterable, details) => {{
    if (!iterable || typeof iterable[Symbol.asyncIterator] !== 'function') {{
      return iterable;
    }}
    return {{
      [Symbol.asyncIterator]() {{
        const iterator = iterable[Symbol.asyncIterator]();
        return {{
          next(...args) {{
            return Promise.resolve(iterator.next(...args))
              .then((result) => {{
                if (result && !result.done) {{
                  trackReturnedValue(result.value, details.handleLineage, args);
                }}
                return result;
              }})
              .catch((error) => {{
                emitProbe({{
                  ...details,
                  stage: 'next',
                  error: normalizeError(error),
                }});
                throw error;
              }});
          }},
          return(...args) {{
            if (typeof iterator.return !== 'function') {{
              return Promise.resolve({{ done: true, value: undefined }});
            }}
            return Promise.resolve(iterator.return(...args));
          }},
          throw(...args) {{
            if (typeof iterator.throw !== 'function') {{
              return Promise.reject(args[0]);
            }}
            return Promise.resolve(iterator.throw(...args));
          }},
        }};
      }},
    }};
  }};

  const wrapHandleMethod = (prototype, methodName, wrapResult) => {{
    const original = prototype?.[methodName];
    if (typeof original !== 'function') {{
      return;
    }}
    prototype[methodName] = function (...args) {{
      const handleLineage = trackedLineageForHandle(this);
      const tracked = Array.isArray(handleLineage);
      const details = {{
        method: methodName,
        handleKind: this?.kind ?? null,
        handleName: handleName(this),
        handleLineage: tracked ? handleLineage : null,
        tracked,
      }};
      let result;
      try {{
        emitActivity({{
          ...details,
          stage: 'invoke',
        }});
        result = original.apply(this, args);
      }} catch (error) {{
        if (tracked) {{
          emitProbe({{
            ...details,
            stage: 'throw',
            error: normalizeError(error),
          }});
        }}
        throw error;
      }}
      if (wrapResult) {{
        if (result && typeof result.then === 'function') {{
          return result
            .then((resolved) => wrapResult(resolved, details, args))
            .catch((error) => {{
              if (tracked) {{
                emitProbe({{
                  ...details,
                  stage: 'reject',
                  error: normalizeError(error),
                }});
              }}
              throw error;
            }});
        }}
        return wrapResult(result, details, args);
      }}
      if (result && typeof result.then === 'function') {{
        return result.catch((error) => {{
          if (tracked) {{
            emitProbe({{
              ...details,
              stage: 'reject',
              error: normalizeError(error),
            }});
          }}
          throw error;
        }});
      }}
      return result;
    }};
  }};

  wrapHandleMethod(globalThis.FileSystemHandle?.prototype, 'queryPermission');
  wrapHandleMethod(globalThis.FileSystemHandle?.prototype, 'requestPermission');
  wrapHandleMethod(
    globalThis.FileSystemDirectoryHandle?.prototype,
    'entries',
    (result, details) => wrapAsyncIterable(result, details),
  );
  wrapHandleMethod(
    globalThis.FileSystemDirectoryHandle?.prototype,
    'keys',
    (result, details) => wrapAsyncIterable(result, details),
  );
  wrapHandleMethod(
    globalThis.FileSystemDirectoryHandle?.prototype,
    'values',
    (result, details) => wrapAsyncIterable(result, details),
  );
  wrapHandleMethod(
    globalThis.FileSystemDirectoryHandle?.prototype,
    'getDirectoryHandle',
    (result, details, args) => trackReturnedValue(result, details.handleLineage, args),
  );
  wrapHandleMethod(
    globalThis.FileSystemDirectoryHandle?.prototype,
    'getFileHandle',
    (result, details, args) => trackReturnedValue(result, details.handleLineage, args),
  );
  wrapHandleMethod(globalThis.FileSystemDirectoryHandle?.prototype, 'resolve');
  wrapHandleMethod(globalThis.FileSystemFileHandle?.prototype, 'getFile');
  wrapHandleMethod(globalThis.FileSystemFileHandle?.prototype, 'createWritable');
}})();
"""

    def _record_console_event(self, message) -> None:
        self.console_events.append(
            WorkspaceRestoreConsoleEvent(
                level=str(message.type),
                text=str(message.text),
            ),
        )

    def _record_page_error(self, error: object) -> None:
        self.page_errors.append(str(error))

    @property
    def _repository_storage_key(self) -> str:
        return self._repository.replace("/", ".")

    @property
    def probe_console_events(self) -> tuple[WorkspaceRestoreConsoleEvent, ...]:
        return self._console_events_with_prefix(self.RUNTIME_PROBE_PREFIX)

    @property
    def activity_console_events(self) -> tuple[WorkspaceRestoreConsoleEvent, ...]:
        return self._console_events_with_prefix(self.RUNTIME_ACTIVITY_PREFIX)

    @property
    def tracked_probe_console_events(self) -> tuple[WorkspaceRestoreConsoleEvent, ...]:
        return tuple(
            event
            for event in self.probe_console_events
            if self._is_tracked_saved_workspace_event(
                event,
                prefix=self.RUNTIME_PROBE_PREFIX,
            )
        )

    @property
    def tracked_activity_console_events(self) -> tuple[WorkspaceRestoreConsoleEvent, ...]:
        return tuple(
            event
            for event in self.activity_console_events
            if self._is_tracked_saved_workspace_event(
                event,
                prefix=self.RUNTIME_ACTIVITY_PREFIX,
            )
        )

    def _console_events_with_prefix(
        self,
        prefix: str,
    ) -> tuple[WorkspaceRestoreConsoleEvent, ...]:
        return tuple(
            event for event in self.console_events if event.text.startswith(prefix)
        )

    def _is_tracked_saved_workspace_event(
        self,
        event: WorkspaceRestoreConsoleEvent,
        *,
        prefix: str,
    ) -> bool:
        if not self._active_local_handle_name:
            return False
        payload = self._console_event_payload(event, prefix=prefix)
        if not isinstance(payload, dict) or payload.get("tracked") is not True:
            return False
        lineage = payload.get("handleLineage")
        return (
            isinstance(lineage, list)
            and len(lineage) > 0
            and lineage[0] == self._active_local_handle_name
        )

    def _console_event_payload(
        self,
        event: WorkspaceRestoreConsoleEvent,
        *,
        prefix: str,
    ) -> dict[str, object] | None:
        payload = event.text[len(prefix) :].strip()
        if not payload:
            return None
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None


def _active_local_handle_name(workspace_state: dict[str, object]) -> str | None:
    active_workspace_id = workspace_state.get("activeWorkspaceId")
    raw_profiles = workspace_state.get("profiles", [])
    if not isinstance(raw_profiles, list):
        return None
    for profile in raw_profiles:
        if not isinstance(profile, dict):
            continue
        if profile.get("id") != active_workspace_id:
            continue
        if profile.get("targetType") != "local":
            continue
        target = str(profile.get("target", "")).strip()
        if not target:
            return None
        name = PurePosixPath(target).name.strip()
        return name or None
    return None
