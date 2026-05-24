from __future__ import annotations

from dataclasses import dataclass

from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppSession
from testing.tests.support.ts984_delayed_auth_probe_runtime import (
    Ts984DelayedAuthProbeRuntime,
)


@dataclass(frozen=True)
class Ts1025ConsoleEvent:
    level: str
    text: str


class Ts1025StartupDiagnosticsRuntime(Ts984DelayedAuthProbeRuntime):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.console_events: list[Ts1025ConsoleEvent] = []
        self.page_errors: list[str] = []

    def __enter__(self) -> PlaywrightWebAppSession:
        session = super().__enter__()
        if self._page is None:
            raise RuntimeError(
                "Ts1025StartupDiagnosticsRuntime expected a browser page.",
            )
        self._page.on("console", self._record_console_event)
        self._page.on("pageerror", self._record_page_error)
        return session

    def _record_console_event(self, message) -> None:
        self.console_events.append(
            Ts1025ConsoleEvent(
                level=str(message.type),
                text=str(message.text),
            ),
        )

    def _record_page_error(self, error: object) -> None:
        self.page_errors.append(str(error))
