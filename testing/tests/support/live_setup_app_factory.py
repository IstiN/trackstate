from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable

from testing.components.pages.trackstate_live_app_page import TrackStateLiveAppPage
from testing.core.config.live_setup_test_config import LiveSetupTestConfig
from testing.core.interfaces.web_app_session import WebAppSession
from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppRuntime

WebAppRuntimeFactory = Callable[[], AbstractContextManager[WebAppSession]]


class TrackStateLiveAppContext(AbstractContextManager[TrackStateLiveAppPage]):
    def __init__(
        self,
        *,
        config: LiveSetupTestConfig,
        runtime_factory: WebAppRuntimeFactory = PlaywrightWebAppRuntime,
    ) -> None:
        self._config = config
        self._runtime_factory = runtime_factory
        self._runtime: AbstractContextManager[WebAppSession] | None = None

    def __enter__(self) -> TrackStateLiveAppPage:
        self._runtime = self._runtime_factory()
        session = self._runtime.__enter__()
        return TrackStateLiveAppPage(session, self._config.app_url)

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._runtime is None:
            return None
        return self._runtime.__exit__(exc_type, exc, exc_tb)


def create_live_setup_app(
    config: LiveSetupTestConfig,
    *,
    runtime_factory: WebAppRuntimeFactory = PlaywrightWebAppRuntime,
) -> TrackStateLiveAppContext:
    return TrackStateLiveAppContext(config=config, runtime_factory=runtime_factory)
