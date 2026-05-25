from __future__ import annotations

import json
from dataclasses import dataclass

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
    PlaywrightWebAppSession,
)


@dataclass(frozen=True)
class BootstrapSchemaGuardConsoleEvent:
    level: str
    text: str


class Ts683BootstrapSchemaGuardRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        malformed_workspace_state: dict[str, object],
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._malformed_workspace_state = malformed_workspace_state
        self.console_events: list[BootstrapSchemaGuardConsoleEvent] = []
        self.page_errors: list[str] = []

    @property
    def prefixed_workspace_key(self) -> str:
        return "flutter.trackstate.workspaceProfiles.state"

    @property
    def prefixed_token_key(self) -> str:
        return f"flutter.trackstate.githubToken.{self._repository_storage_key}"

    @property
    def repository_storage_key(self) -> str:
        return self._repository_storage_key

    @property
    def malformed_workspace_value(self) -> str:
        return json.dumps(self._malformed_workspace_state)

    @property
    def malformed_token_value(self) -> str:
        return self._token

    @property
    def expected_encoded_token_value(self) -> str:
        return json.dumps(self._token)

    def __enter__(self) -> PlaywrightWebAppSession:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(viewport={"width": 1440, "height": 960})
        self._context.route("https://api.github.com/**", self._handle_github_api_route)
        self._context.add_init_script(script=self._build_preload_script())
        self._page = self._context.new_page()
        self._page.on("console", self._record_console_event)
        self._page.on("pageerror", self._record_page_error)
        return PlaywrightWebAppSession(self._page)

    def storage_snapshot(self) -> dict[str, str | None]:
        if self._page is None:
            raise RuntimeError("TS-683 storage snapshot requested before the page was created.")
        payload = self._page.evaluate(
            """
            (keys) => {
              const snapshot = {};
              for (const key of keys) {
                snapshot[key] = window.localStorage.getItem(key);
              }
              return snapshot;
            }
            """,
            [
                self.prefixed_workspace_key,
                self.prefixed_token_key,
                "trackstate.workspaceProfiles.state",
                f"trackstate.githubToken.{self._repository_storage_key}",
            ],
        )
        if not isinstance(payload, dict):
            raise AssertionError(f"TS-683 expected a storage snapshot map, got: {payload!r}")
        return {
            str(key): (None if value is None else str(value))
            for key, value in payload.items()
        }

    def _build_preload_script(self) -> str:
        return "".join(
            [
                "(() => {",
                f"window.localStorage.setItem({json.dumps(self.prefixed_workspace_key)}, {json.dumps(self.malformed_workspace_value)});",
                f"window.localStorage.setItem({json.dumps(self.prefixed_token_key)}, {json.dumps(self.malformed_token_value)});",
                "})();",
            ],
        )

    def _record_console_event(self, message) -> None:
        self.console_events.append(
            BootstrapSchemaGuardConsoleEvent(
                level=str(message.type),
                text=str(message.text),
            ),
        )

    def _record_page_error(self, error: object) -> None:
        self.page_errors.append(str(error))

    @property
    def _repository_storage_key(self) -> str:
        return self._repository.replace("/", ".")
