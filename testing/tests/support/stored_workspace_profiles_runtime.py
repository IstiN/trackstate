from __future__ import annotations

import json
from urllib.parse import quote

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightWebAppRuntime,
    PlaywrightStoredTokenWebAppRuntime,
    PlaywrightWebAppSession,
)


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
        self._context.add_init_script(script=_build_preload_script(self._workspace_state))
        return session


class StoredWorkspaceProfilesRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._workspace_state = workspace_state

    def __enter__(self) -> PlaywrightWebAppSession:
        session = super().__enter__()
        if self._context is None:
            raise RuntimeError(
                "StoredWorkspaceProfilesRuntime expected a browser context.",
            )
        self._context.add_init_script(
            script=_build_preload_script(
                self._workspace_state,
                repository=self._repository,
                token=self._token,
            ),
        )
        return session


def _build_preload_script(
    workspace_state: dict[str, object],
    *,
    repository: str | None = None,
    token: str | None = None,
) -> str:
    serialized_state = json.dumps(workspace_state)
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
        repository_storage_key = repository.replace("/", ".")
        workspace_storage_keys = _workspace_token_storage_keys(workspace_state)
        scripts.extend(
            [
                f"const token = {json.dumps(token)};",
                "for (const key of [",
                f"  'trackstate.githubToken.{repository_storage_key}',",
                f"  'flutter.trackstate.githubToken.{repository_storage_key}',",
                *[f"  {json.dumps(key)}," for key in workspace_storage_keys],
                "]) {",
                "  window.localStorage.setItem(key, token);",
                "}",
            ],
        )
    scripts.append("})();")
    return "".join(scripts)


def _workspace_token_storage_keys(
    workspace_state: dict[str, object],
) -> list[str]:
    raw_profiles = workspace_state.get("profiles", [])
    if not isinstance(raw_profiles, list):
        return []
    keys: list[str] = []
    for profile in raw_profiles:
        if not isinstance(profile, dict):
            continue
        workspace_id = str(profile.get("id", "")).strip()
        if not workspace_id:
            continue
        encoded_id = quote(workspace_id, safe="")
        keys.extend(
            [
                f"trackstate.githubToken.workspace.{encoded_id}",
                f"flutter.trackstate.githubToken.workspace.{encoded_id}",
            ],
        )
    return keys
