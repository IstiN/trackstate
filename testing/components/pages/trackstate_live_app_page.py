from __future__ import annotations

import time
from dataclasses import dataclass

from playwright.sync_api import Page


@dataclass(frozen=True)
class RuntimeState:
    kind: str
    body_text: str


class TrackStateLiveAppPage:
    def __init__(self, page: Page, app_url: str) -> None:
        self.page = page
        self.app_url = app_url

    def open(self) -> None:
        self.page.goto(
            self.app_url,
            wait_until="domcontentloaded",
            timeout=120_000,
        )
        self.page.wait_for_timeout(8_000)
        self.page.eval_on_selector("flt-semantics-placeholder", "el => el.click()")
        self.page.wait_for_timeout(3_000)

    def wait_for_runtime_state(self, timeout_seconds: int = 90) -> RuntimeState:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            body_text = self.page.locator("body").inner_text()
            if "TrackState data was not found in the configured repository runtime." in body_text:
                return RuntimeState(kind="data-load-failed", body_text=body_text)
            if "Connect GitHub" in body_text:
                return RuntimeState(kind="connect-ready", body_text=body_text)
            self.page.wait_for_timeout(1_000)
        return RuntimeState(
            kind="timeout",
            body_text=self.page.locator("body").inner_text(),
        )

    def screenshot(self, path: str) -> None:
        self.page.screenshot(path=path, full_page=True)

    def body_text(self) -> str:
        return self.page.locator("body").inner_text()

    def open_connect_dialog(self) -> None:
        self.page.locator('flt-semantics[aria-label="Connect GitHub"]').first.click()
        self.page.wait_for_timeout(2_000)

    def fill_fine_grained_token(self, token: str) -> None:
        self.page.locator('input[aria-label="Fine-grained token"]').fill(token)

    def submit_connect_token(self) -> None:
        self.page.locator(
            'flt-semantics[role="button"]',
            has_text="Connect token",
        ).click()

    def open_settings(self) -> None:
        self.page.locator(
            'flt-semantics[role="button"]',
            has_text="Settings",
        ).click()
        self.page.wait_for_timeout(2_000)

    def wait_for_body_text(
        self,
        text: str,
        timeout_seconds: int = 60,
    ) -> str:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            body_text = self.body_text()
            if text in body_text:
                return body_text
            self.page.wait_for_timeout(1_000)
        raise AssertionError(
            f'Timed out waiting for "{text}". Visible body text: {self.body_text()}',
        )
