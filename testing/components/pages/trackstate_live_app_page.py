from __future__ import annotations

from dataclasses import dataclass

from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError


@dataclass(frozen=True)
class RuntimeState:
    kind: str
    body_text: str


@dataclass(frozen=True)
class ConnectDialogState:
    body_text: str
    fine_grained_token_input_count: int
    remember_browser_option_count: int


class TrackStateLiveAppPage:
    LOAD_ERROR_TEXT = (
        "TrackState data was not found in the configured repository runtime."
    )
    CONNECT_READY_TEXT = "Connect GitHub"
    TOKEN_INPUT_SELECTOR = 'input[aria-label="Fine-grained token"]'
    CONNECT_BUTTON_SELECTOR = 'flt-semantics[role="button"]'
    REMEMBER_BROWSER_SELECTOR = (
        'flt-semantics[role="checkbox"][aria-label*="Remember on this browser"]'
    )

    def __init__(self, session: WebAppSession, app_url: str) -> None:
        self.session = session
        self.app_url = app_url

    def open(self) -> None:
        self.session.goto(
            self.app_url,
            wait_until="domcontentloaded",
            timeout_ms=120_000,
        )
        self.session.activate_accessibility()

    def wait_for_runtime_state(self, timeout_seconds: int = 90) -> RuntimeState:
        try:
            wait_match = self.session.wait_for_any_text(
                [self.LOAD_ERROR_TEXT, self.CONNECT_READY_TEXT],
                timeout_ms=timeout_seconds * 1_000,
            )
        except WebAppTimeoutError:
            return RuntimeState(
                kind="timeout",
                body_text=self.session.body_text(),
            )

        if wait_match.matched_text == self.LOAD_ERROR_TEXT:
            return RuntimeState(kind="data-load-failed", body_text=wait_match.body_text)
        return RuntimeState(kind="connect-ready", body_text=wait_match.body_text)

    def screenshot(self, path: str) -> None:
        self.session.screenshot(path)

    def body_text(self) -> str:
        return self.session.body_text()

    def open_connect_dialog(self) -> None:
        self.session.click('flt-semantics[aria-label="Connect GitHub"]')
        self.session.wait_for_selector(self.TOKEN_INPUT_SELECTOR, timeout_ms=30_000)

    def read_connect_dialog_state(self) -> ConnectDialogState:
        return ConnectDialogState(
            body_text=self.session.body_text(),
            fine_grained_token_input_count=self.session.count(self.TOKEN_INPUT_SELECTOR),
            remember_browser_option_count=self.session.count(
                self.REMEMBER_BROWSER_SELECTOR,
            ),
        )

    def fill_fine_grained_token(self, token: str) -> None:
        self.session.fill(self.TOKEN_INPUT_SELECTOR, token)

    def submit_connect_token(self) -> None:
        self.session.click(
            self.CONNECT_BUTTON_SELECTOR,
            has_text="Connect token",
            timeout_ms=30_000,
        )

    def open_settings(self) -> None:
        self.session.click(
            self.CONNECT_BUTTON_SELECTOR,
            has_text="Settings",
            timeout_ms=30_000,
        )

    def wait_for_body_text(
        self,
        text: str,
        timeout_seconds: int = 60,
    ) -> str:
        try:
            return self.session.wait_for_text(
                text,
                timeout_ms=timeout_seconds * 1_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Timed out waiting for "{text}". Visible body text: {self.body_text()}',
            ) from error
