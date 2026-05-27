from __future__ import annotations

import time
from typing import Any

from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppSession
from testing.tests.support.delayed_auth_workspace_profiles_runtime import (
    DelayedAuthWorkspaceProfilesRuntime,
)


class Ts984DelayedAuthProbeRuntime(DelayedAuthWorkspaceProfilesRuntime):
    def __enter__(self) -> PlaywrightWebAppSession:
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError(
                "Ts984DelayedAuthProbeRuntime expected a browser context and page.",
            )
        script = _shell_ready_probe_script()
        self._context.add_init_script(script=script)
        self._page.add_init_script(script=script)
        return session

    def wait_for_shell_ready_observation(self, *, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.read_shell_probe_state().get("first_shell_ready_after_launch_seconds") is not None:
                return True
            time.sleep(0.1)
        return self.read_shell_probe_state().get("first_shell_ready_after_launch_seconds") is not None

    def read_shell_probe_state(self) -> dict[str, Any]:
        if self._page is None:
            raise RuntimeError(
                "Ts984DelayedAuthProbeRuntime expected a browser page before reading state.",
            )
        payload = self._page.evaluate(
            """
            () => {
              const state = window.__ts984ShellReadyProbeState;
              if (!state) {
                return null;
              }
              return {
                firstShellReadyObservedAtMs: state.firstShellReadyObservedAtMs,
                firstShellReadyBodyText: state.firstShellReadyBodyText,
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            return {
                "first_shell_ready_after_launch_seconds": None,
                "first_shell_ready_body_text": "",
            }
        observed_at_ms = payload.get("firstShellReadyObservedAtMs")
        return {
            "first_shell_ready_after_launch_seconds": (
                round(float(observed_at_ms) / 1000, 2)
                if isinstance(observed_at_ms, (int, float))
                else None
            ),
            "first_shell_ready_body_text": str(payload.get("firstShellReadyBodyText", "")),
        }


def _shell_ready_probe_script() -> str:
    return """
(() => {
  const state = {
    firstShellReadyObservedAtMs: null,
    firstShellReadyBodyText: '',
  };
  window.__ts984ShellReadyProbeState = state;

  const readyLabels = ['Dashboard', 'Board', 'JQL Search', 'Hierarchy', 'Settings'];
  const currentBodyText = () => document.body?.innerText ?? document.body?.textContent ?? '';
  const shellReadyNow = () => {
    const bodyText = currentBodyText();
    return readyLabels.every((label) => bodyText.includes(label))
      && bodyText.includes('TrackState.AI');
  };
  const observeShellReady = () => {
    if (state.firstShellReadyObservedAtMs !== null || !shellReadyNow()) {
      return;
    }
    state.firstShellReadyObservedAtMs = performance.now();
    state.firstShellReadyBodyText = currentBodyText();
  };
  const attachObserver = () => {
    observeShellReady();
    if (!document.documentElement) {
      requestAnimationFrame(attachObserver);
      return;
    }
    new MutationObserver(() => observeShellReady()).observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  };
  attachObserver();
  window.addEventListener('load', () => observeShellReady(), { once: false });
})();
"""
