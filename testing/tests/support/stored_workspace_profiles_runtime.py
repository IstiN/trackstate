from __future__ import annotations

import json
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
