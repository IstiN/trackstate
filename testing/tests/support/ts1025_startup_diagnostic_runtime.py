from __future__ import annotations

from typing import Any

from playwright.sync_api import ConsoleMessage

from testing.tests.support.ts984_delayed_auth_probe_runtime import (
    Ts984DelayedAuthProbeRuntime,
)


class Ts1025StartupDiagnosticRuntime(Ts984DelayedAuthProbeRuntime):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._playwright_console_messages: list[dict[str, str]] = []
        self._page_errors: list[str] = []

    def __enter__(self):
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError(
                "Ts1025StartupDiagnosticRuntime expected a browser context and page.",
            )
        script = _startup_console_capture_script()
        self._context.add_init_script(script=script)
        self._page.add_init_script(script=script)
        self._page.on("console", self._record_console_message)
        self._page.on("pageerror", lambda error: self._page_errors.append(str(error)))
        return session

    def read_startup_diagnostic_state(self) -> dict[str, Any]:
        if self._page is None:
            raise RuntimeError(
                "Ts1025StartupDiagnosticRuntime expected a browser page before reading state.",
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
                "playwright_page_errors": list(self._page_errors),
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
            "playwright_page_errors": list(self._page_errors),
        }

    def _record_console_message(self, message: ConsoleMessage) -> None:
        self._playwright_console_messages.append(
            {
                "type": message.type,
                "text": message.text,
            },
        )


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
