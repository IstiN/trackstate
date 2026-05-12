from __future__ import annotations

import json

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
    PlaywrightWebAppSession,
)


class DeferredIssueHydrationDelayRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        delayed_detail_paths: list[str],
        delayed_comment_paths: list[str],
        delay_ms: int,
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._delayed_detail_paths = tuple(delayed_detail_paths)
        self._delayed_comment_paths = tuple(delayed_comment_paths)
        self._delay_ms = delay_ms

    def __enter__(self) -> PlaywrightWebAppSession:
        session = super().__enter__()
        if self._context is None:
            raise RuntimeError("DeferredCommentsDelayRuntime expected a browser context.")
        self._context.add_init_script(
            script=(
                "(() => {"
                "const trackedPathsByGroup = {"
                f"  detail: {json.dumps(list(self._delayed_detail_paths))},"
                f"  comments: {json.dumps(list(self._delayed_comment_paths))},"
                "};"
                f"const delayMs = {json.dumps(self._delay_ms)};"
                "const createGroupState = (trackedPaths) => ({"
                "  trackedPaths: [...trackedPaths],"
                "  delayedPaths: [],"
                "  activeCount: 0,"
                "  startedUrls: [],"
                "  completedUrls: [],"
                "  lastDelayStartedAt: null,"
                "  lastDelayCompletedAt: null,"
                "});"
                "const groups = Object.fromEntries("
                "  Object.entries(trackedPathsByGroup).map(([groupName, trackedPaths]) => ["
                "    groupName,"
                "    createGroupState(trackedPaths),"
                "  ])"
                ");"
                "const state = {"
                "  delayMs,"
                "  activeCount: 0,"
                "  lastDelayStartedAt: null,"
                "  lastDelayCompletedAt: null,"
                "  groups,"
                "};"
                "window.__ts452DelayState = state;"
                "const originalFetch = window.fetch.bind(window);"
                "window.fetch = async (input, init) => {"
                "  const requestUrl = typeof input === 'string'"
                "    ? input"
                "    : (input && typeof input === 'object' && 'url' in input ? input.url : '');"
                "  const delayedMatch = Object.entries(groups).find(([, groupState]) =>"
                "    groupState.trackedPaths.some((path) => requestUrl.includes(`/contents/${path}`))"
                "  );"
                "  if (!delayedMatch) {"
                "    return originalFetch(input, init);"
                "  }"
                "  const [groupName, groupState] = delayedMatch;"
                "  const matchedPath = groupState.trackedPaths.find((path) =>"
                "    requestUrl.includes(`/contents/${path}`)"
                "  );"
                "  if (!matchedPath) {"
                "    return originalFetch(input, init);"
                "  }"
                "  if (groupState.delayedPaths.includes(matchedPath)) {"
                "    return originalFetch(input, init);"
                "  }"
                "  groupState.delayedPaths.push(matchedPath);"
                "  groupState.startedUrls.push(requestUrl);"
                "  groupState.activeCount += 1;"
                "  state.activeCount += 1;"
                "  state.lastDelayedGroup = groupName;"
                "  groupState.lastDelayStartedAt = Date.now();"
                "  state.lastDelayStartedAt = Date.now();"
                "  try {"
                "    await new Promise((resolve) => setTimeout(resolve, delayMs));"
                "    return await originalFetch(input, init);"
                "  } finally {"
                "    groupState.activeCount -= 1;"
                "    state.activeCount -= 1;"
                "    groupState.completedUrls.push(requestUrl);"
                "    groupState.lastDelayCompletedAt = Date.now();"
                "    state.lastDelayCompletedAt = Date.now();"
                "  }"
                "};"
                "})();"
            ),
        )
        return session
