from __future__ import annotations

import json

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
        serialized_state = json.dumps(self._workspace_state)
        self._context.add_init_script(
            script=(
                "(() => {"
                f"const state = {json.dumps(serialized_state)};"
                "for (const key of ["
                "  'trackstate.workspaceProfiles.state',"
                "  'flutter.trackstate.workspaceProfiles.state',"
                "]) {"
                "  window.localStorage.setItem(key, state);"
                "}"
                "})();"
            ),
        )
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
        serialized_state = json.dumps(self._workspace_state)
        self._context.add_init_script(
            script=(
                "(() => {"
                f"const state = {json.dumps(serialized_state)};"
                "for (const key of ["
                "  'trackstate.workspaceProfiles.state',"
                "  'flutter.trackstate.workspaceProfiles.state',"
                "]) {"
                "  window.localStorage.setItem(key, state);"
                "}"
                "})();"
            ),
        )
        return session
