from __future__ import annotations

from dataclasses import dataclass
import time

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
        self.auth_probe_completed_at_monotonic: float | None = None
        self.first_auth_probe_completed_at_monotonic: float | None = None

    def __enter__(self) -> PlaywrightWebAppSession:
        session = super().__enter__()
        if self._page is None:
            raise RuntimeError(
                "Ts1025StartupDiagnosticsRuntime expected a browser page.",
            )
        self._page.on("console", self._record_console_event)
        self._page.on("pageerror", self._record_page_error)
        self._page.on("requestfinished", self._record_request_finished)
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

    def _record_request_finished(self, request) -> None:
        request_url = str(request.url)
        if "api.github.com" not in request_url or not self._matches_delayed_path(request_url):
            return
        completed_at_monotonic = time.monotonic()
        matched_timing = None
        for timing in self.delayed_request_timings:
            if timing.get("url") != request_url:
                continue
            if timing.get("completed_at_monotonic") is not None:
                continue
            matched_timing = timing
            break
        if matched_timing is not None:
            matched_timing["completed_at_monotonic"] = completed_at_monotonic
        if self.first_auth_probe_completed_at_monotonic is None:
            self.first_auth_probe_completed_at_monotonic = completed_at_monotonic
        self.auth_probe_completed_at_monotonic = completed_at_monotonic
