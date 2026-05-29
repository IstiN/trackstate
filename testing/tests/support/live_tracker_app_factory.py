from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.config.live_setup_test_config import LiveSetupTestConfig
from testing.core.interfaces.web_app_session import WebAppSession
from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightWebAppRuntime,
)
from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)

WebAppRuntimeFactory = Callable[[], AbstractContextManager[WebAppSession]]


class TrackStateTrackerAppContext(AbstractContextManager[TrackStateTrackerPage]):
    def __init__(
        self,
        *,
        config: LiveSetupTestConfig,
        runtime_factory: WebAppRuntimeFactory = PlaywrightWebAppRuntime,
    ) -> None:
        self._config = config
        self._runtime_factory = runtime_factory
        self._runtime: AbstractContextManager[WebAppSession] | None = None

    def __enter__(self) -> TrackStateTrackerPage:
        self._runtime = self._runtime_factory()
        session = self._runtime.__enter__()
        return TrackStateTrackerPage(session, self._config.app_url)

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._runtime is None:
            return None
        return self._runtime.__exit__(exc_type, exc, exc_tb)


def create_live_tracker_app(
    config: LiveSetupTestConfig,
    *,
    runtime_factory: WebAppRuntimeFactory = PlaywrightWebAppRuntime,
) -> TrackStateTrackerAppContext:
    return TrackStateTrackerAppContext(config=config, runtime_factory=runtime_factory)


def create_live_tracker_app_with_stored_token(
    config: LiveSetupTestConfig,
    *,
    token: str,
) -> TrackStateTrackerAppContext:
    hosted_workspace_id = f"hosted:{config.repository.lower()}@{config.ref}"
    workspace_state: dict[str, object] = {
        "activeWorkspaceId": hosted_workspace_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": hosted_workspace_id,
                "displayName": "",
                "targetType": "hosted",
                "target": config.repository,
                "defaultBranch": config.ref,
                "writeBranch": config.ref,
            },
        ],
    }
    return TrackStateTrackerAppContext(
        config=config,
        runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
            repository=config.repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=(hosted_workspace_id,),
        ),
    )
