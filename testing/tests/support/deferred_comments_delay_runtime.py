from __future__ import annotations

import json

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
    PlaywrightWebAppSession,
)


class DeferredCommentsDelayRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        delayed_comment_paths: list[str],
        delay_ms: int,
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._delayed_comment_paths = tuple(delayed_comment_paths)
        self._delay_ms = delay_ms

    def __enter__(self) -> PlaywrightWebAppSession:
        session = super().__enter__()
        if self._context is None:
            raise RuntimeError("DeferredCommentsDelayRuntime expected a browser context.")
        self._context.add_init_script(
            script=(
                "(() => {"
                f"const trackedPaths = {json.dumps(list(self._delayed_comment_paths))};"
                f"const delayMs = {json.dumps(self._delay_ms)};"
                "const state = {"
                "  trackedPaths: [...trackedPaths],"
                "  delayMs,"
                "  activeCount: 0,"
                "  startedUrls: [],"
                "  completedUrls: [],"
                "  lastDelayStartedAt: null,"
                "  lastDelayCompletedAt: null,"
                "};"
                "window.__ts452DelayState = state;"
                "const originalFetch = window.fetch.bind(window);"
                "window.fetch = async (input, init) => {"
                "  const requestUrl = typeof input === 'string'"
                "    ? input"
                "    : (input && typeof input === 'object' && 'url' in input ? input.url : '');"
                "  const shouldDelay = trackedPaths.some((path) =>"
                "    requestUrl.includes(`/contents/${path}`)"
                "  );"
                "  if (!shouldDelay) {"
                "    return originalFetch(input, init);"
                "  }"
                "  state.startedUrls.push(requestUrl);"
                "  state.activeCount += 1;"
                "  state.lastDelayStartedAt = Date.now();"
                "  try {"
                "    await new Promise((resolve) => setTimeout(resolve, delayMs));"
                "    return await originalFetch(input, init);"
                "  } finally {"
                "    state.activeCount -= 1;"
                "    state.completedUrls.push(requestUrl);"
                "    state.lastDelayCompletedAt = Date.now();"
                "  }"
                "};"
                "})();"
            ),
        )
        return session
