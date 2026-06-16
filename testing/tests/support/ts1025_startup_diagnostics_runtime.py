from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from playwright.sync_api import ConsoleMessage

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
        self._playwright_console_messages: list[dict[str, str]] = []
        self.auth_probe_completed_at_monotonic: float | None = None
        self.first_auth_probe_completed_at_monotonic: float | None = None

    def __enter__(self) -> PlaywrightWebAppSession:
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError(
                "Ts1025StartupDiagnosticsRuntime expected a browser context and page.",
            )
        script = _startup_console_capture_script()
        self._context.add_init_script(script=script)
        self._page.add_init_script(script=script)
        self._page.on("console", self._record_console_event)
        self._page.on("pageerror", self._record_page_error)
        self._page.on("requestfinished", self._record_request_finished)
        return session

    def read_startup_diagnostic_state(self) -> dict[str, Any]:
        if self._page is None:
            raise RuntimeError(
                "Ts1025StartupDiagnosticsRuntime expected a browser page before reading state.",
            )
        payload = self._page.evaluate(
            """
            () => {
              const state = window.__ts1025StartupDiagnostics;
              if (!state) {
                return null;
              }
              return {
                consoleEvents: Array.isArray(state.consoleEvents)
                  ? state.consoleEvents.map((entry) => ({
                      level: String(entry?.level ?? 'log'),
                      text: String(entry?.text ?? ''),
                      observedAtMs: entry?.observedAtMs ?? null,
                    }))
                  : [],
                pageErrors: Array.isArray(state.pageErrors)
                  ? state.pageErrors.map((entry) => String(entry))
                  : [],
                unhandledRejections: Array.isArray(state.unhandledRejections)
                  ? state.unhandledRejections.map((entry) => String(entry))
                  : [],
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            return {
                "in_page_console_events": [],
                "in_page_page_errors": [],
                "in_page_unhandled_rejections": [],
                "playwright_console_messages": list(self._playwright_console_messages),
                "playwright_page_errors": list(self.page_errors),
            }
        console_events = payload.get("consoleEvents", [])
        page_errors = payload.get("pageErrors", [])
        unhandled_rejections = payload.get("unhandledRejections", [])
        return {
            "in_page_console_events": [
                {
                    "level": str(entry.get("level", "log")),
                    "text": str(entry.get("text", "")),
                    "observed_at_ms": entry.get("observedAtMs"),
                }
                for entry in console_events
                if isinstance(entry, dict)
            ],
            "in_page_page_errors": [
                str(entry) for entry in page_errors if isinstance(entry, str)
            ],
            "in_page_unhandled_rejections": [
                str(entry) for entry in unhandled_rejections if isinstance(entry, str)
            ],
            "playwright_console_messages": list(self._playwright_console_messages),
            "playwright_page_errors": list(self.page_errors),
        }

    def _record_console_event(self, message: ConsoleMessage) -> None:
        self.console_events.append(
            Ts1025ConsoleEvent(
                level=str(message.type),
                text=str(message.text),
            ),
        )
        self._playwright_console_messages.append(
            {
                "type": message.type,
                "text": message.text,
            },
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


def _startup_console_capture_script() -> str:
    return """
(() => {
  if (window.__ts1025StartupDiagnostics) {
    return;
  }
  const state = {
    consoleEvents: [],
    pageErrors: [],
    unhandledRejections: [],
  };
  window.__ts1025StartupDiagnostics = state;

  const safeStringify = (value) => {
    if (typeof value === 'string') {
      return value;
    }
    try {
      return JSON.stringify(value);
    } catch (error) {
      return String(value);
    }
  };
  const captureConsole = (level, args) => {
    state.consoleEvents.push({
      level,
      text: Array.from(args).map((value) => safeStringify(value)).join(' '),
      observedAtMs: performance.now(),
    });
  };
  for (const level of ['debug', 'info', 'log', 'warn', 'error']) {
    const original = console[level]?.bind(console);
    if (!original) {
      continue;
    }
    console[level] = (...args) => {
      captureConsole(level, args);
      return original(...args);
    };
  }
  window.addEventListener('error', (event) => {
    state.pageErrors.push(
      String(event?.error?.stack || event?.error || event?.message || 'Unknown error'),
    );
  });
  window.addEventListener('unhandledrejection', (event) => {
    state.unhandledRejections.push(
      String(event?.reason?.stack || event?.reason || 'Unhandled rejection'),
    );
  });
})();
"""
