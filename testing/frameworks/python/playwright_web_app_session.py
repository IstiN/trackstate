from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Sequence

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from testing.core.interfaces.web_app_session import (
    WaitMatch,
    WaitState,
    WebAppSession,
    WebAppTimeoutError,
)


class PlaywrightWebAppSession(WebAppSession):
    def __init__(self, page: Page) -> None:
        self._page = page

    def goto(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 120_000,
    ) -> None:
        self._page.goto(url, wait_until=wait_until, timeout=timeout_ms)

    def activate_accessibility(self) -> None:
        placeholder_selector = "flt-semantics-placeholder"
        self.wait_for_selector(
            placeholder_selector,
            state="attached",
            timeout_ms=120_000,
        )
        self._locator(placeholder_selector).evaluate("element => element.click()")

    def wait_for_selector(
        self,
        selector: str,
        *,
        state: WaitState = "visible",
        timeout_ms: int = 30_000,
        has_text: str | None = None,
        index: int = 0,
    ) -> None:
        try:
            self._locator(selector, has_text=has_text, index=index).wait_for(
                state=state,
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError as error:
            raise WebAppTimeoutError(
                f'Timed out waiting for selector "{selector}" to become {state}.',
            ) from error

    def click(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None:
        try:
            locator = self._locator(selector, has_text=has_text, index=index)
            locator.wait_for(state="visible", timeout=timeout_ms)
            locator.click(timeout=timeout_ms)
        except PlaywrightTimeoutError as error:
            raise WebAppTimeoutError(
                f'Timed out clicking selector "{selector}".',
            ) from error

    def fill(
        self,
        selector: str,
        value: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None:
        try:
            locator = self._locator(selector, has_text=has_text, index=index)
            locator.wait_for(state="visible", timeout=timeout_ms)
            locator.fill(value, timeout=timeout_ms)
        except PlaywrightTimeoutError as error:
            raise WebAppTimeoutError(
                f'Timed out filling selector "{selector}".',
            ) from error

    def count(
        self,
        selector: str,
        *,
        has_text: str | None = None,
    ) -> int:
        return self._locator(selector, has_text=has_text).count()

    def body_text(self) -> str:
        return self._page.locator("body").inner_text()

    def wait_for_text(
        self,
        text: str,
        *,
        timeout_ms: int = 60_000,
    ) -> str:
        try:
            self._page.wait_for_function(
                "(expectedText) => (document.body?.innerText ?? '').includes(expectedText)",
                arg=text,
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError as error:
            raise WebAppTimeoutError(
                f'Timed out waiting for text "{text}".',
            ) from error
        return self.body_text()

    def wait_for_any_text(
        self,
        texts: Sequence[str],
        *,
        timeout_ms: int = 90_000,
    ) -> WaitMatch:
        try:
            wait_handle = self._page.wait_for_function(
                """
                (expectedTexts) => {
                    const bodyText = document.body?.innerText ?? '';
                    const matchedText = expectedTexts.find((text) => bodyText.includes(text));
                    return matchedText ? { matchedText, bodyText } : null;
                }
                """,
                arg=list(texts),
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError as error:
            raise WebAppTimeoutError(
                f"Timed out waiting for any expected text: {list(texts)}.",
            ) from error
        payload = wait_handle.json_value()
        return WaitMatch(
            matched_text=str(payload["matchedText"]),
            body_text=str(payload["bodyText"]),
        )

    def screenshot(self, path: str) -> None:
        self._page.screenshot(path=path, full_page=True)

    def _locator(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
    ):
        locator = self._page.locator(selector, has_text=has_text)
        return locator.nth(index)


class PlaywrightWebAppRuntime(AbstractContextManager[PlaywrightWebAppSession]):
    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> PlaywrightWebAppSession:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(viewport={"width": 1440, "height": 960})
        self._page = self._context.new_page()
        return PlaywrightWebAppSession(self._page)

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        return None
