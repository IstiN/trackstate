from __future__ import annotations

from contextlib import AbstractContextManager
from html import unescape
from html.parser import HTMLParser
from socket import timeout as SocketTimeout
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from testing.core.interfaces.web_app_session import (
    FocusedElementObservation,
    WaitMatch,
    WaitState,
    WebAppSession,
    WebAppTimeoutError,
)


class _BodyTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._hidden_depth > 0:
            self._hidden_depth -= 1
        if tag in {"p", "div", "section", "article", "main", "header", "footer", "li", "tr", "td", "th", "br", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._hidden_depth == 0 and data.strip():
            self._parts.append(data)

    def text(self) -> str:
        collapsed = re.sub(r"\n{3,}", "\n\n", "\n".join(self._parts))
        return unescape(collapsed).strip()


class UrllibWebAppSession(WebAppSession):
    def __init__(self) -> None:
        self._body_text = ""

    def goto(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 120_000,
    ) -> None:
        del wait_until
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
            },
        )
        try:
            with urlopen(request, timeout=max(timeout_ms / 1_000, 1)) as response:
                html = response.read().decode("utf-8", errors="replace")
        except HTTPError as error:
            html = error.read().decode("utf-8", errors="replace")
        except (URLError, OSError, SocketTimeout) as error:
            raise WebAppTimeoutError(f"Could not fetch {url}: {error}") from error
        parser = _BodyTextParser()
        parser.feed(html)
        self._body_text = parser.text()

    def activate_accessibility(self) -> None:
        return None

    def wait_for_selector(
        self,
        selector: str,
        *,
        state: WaitState = "visible",
        timeout_ms: int = 30_000,
        has_text: str | None = None,
        index: int = 0,
    ) -> None:
        del selector, state, timeout_ms, has_text, index
        raise NotImplementedError(
            "Selector-based browser interactions are not supported by the urllib "
            "web session fallback."
        )

    def click(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None:
        del selector, has_text, index, timeout_ms
        raise NotImplementedError(
            "Click interactions are not supported by the urllib web session fallback."
        )

    def fill(
        self,
        selector: str,
        value: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None:
        del selector, value, has_text, index, timeout_ms
        raise NotImplementedError(
            "Form interactions are not supported by the urllib web session fallback."
        )

    def count(
        self,
        selector: str,
        *,
        has_text: str | None = None,
    ) -> int:
        del selector, has_text
        raise NotImplementedError(
            "Selector counts are not supported by the urllib web session fallback."
        )

    def press(
        self,
        selector: str,
        key: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None:
        del selector, key, has_text, index, timeout_ms
        raise NotImplementedError(
            "Keyboard interactions are not supported by the urllib web session fallback."
        )

    def press_key(
        self,
        key: str,
        *,
        timeout_ms: int = 30_000,
    ) -> None:
        del key, timeout_ms
        raise NotImplementedError(
            "Keyboard interactions are not supported by the urllib web session fallback."
        )

    def focus(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None:
        del selector, has_text, index, timeout_ms
        raise NotImplementedError(
            "Focus interactions are not supported by the urllib web session fallback."
        )

    def body_text(self) -> str:
        return self._body_text

    def read_value(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> str:
        del selector, has_text, index, timeout_ms
        raise NotImplementedError(
            "Reading input values is not supported by the urllib web session fallback."
        )

    def read_text(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> str:
        del selector, has_text, index, timeout_ms
        raise NotImplementedError(
            "Reading element text is not supported by the urllib web session fallback."
        )

    def wait_for_input_value(
        self,
        selector: str,
        expected_value: str,
        *,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> str:
        del selector, expected_value, index, timeout_ms
        raise NotImplementedError(
            "Input polling is not supported by the urllib web session fallback."
        )

    def wait_for_count(
        self,
        selector: str,
        expected_count: int,
        *,
        timeout_ms: int = 30_000,
    ) -> None:
        del selector, expected_count, timeout_ms
        raise NotImplementedError(
            "Selector counts are not supported by the urllib web session fallback."
        )

    def wait_for_text(
        self,
        text: str,
        *,
        timeout_ms: int = 60_000,
    ) -> str:
        del timeout_ms
        if text not in self._body_text:
            raise WebAppTimeoutError(f'Timed out waiting for text "{text}".')
        return self._body_text

    def wait_for_any_text(
        self,
        texts: list[str] | tuple[str, ...],
        *,
        timeout_ms: int = 90_000,
    ) -> WaitMatch:
        del timeout_ms
        for text in texts:
            if text in self._body_text:
                return WaitMatch(matched_text=text, body_text=self._body_text)
        raise WebAppTimeoutError(
            f"Timed out waiting for any expected text: {list(texts)}."
        )

    def evaluate(
        self,
        expression: str,
        *,
        arg: object | None = None,
    ) -> object:
        del expression, arg
        raise NotImplementedError(
            "DOM evaluation is not supported by the urllib web session fallback."
        )

    def wait_for_function(
        self,
        expression: str,
        *,
        arg: object | None = None,
        timeout_ms: int = 30_000,
    ) -> object:
        del expression, arg, timeout_ms
        raise NotImplementedError(
            "Function-based DOM waits are not supported by the urllib web session fallback."
        )

    def active_element(self) -> FocusedElementObservation:
        raise NotImplementedError(
            "Active-element inspection is not supported by the urllib web session fallback."
        )

    def wait_for_download_after_keypress(
        self,
        key: str,
        *,
        timeout_ms: int = 30_000,
    ) -> str:
        del key, timeout_ms
        raise NotImplementedError(
            "Download capture is not supported by the urllib web session fallback."
        )

    def wait_for_download_after_click(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> str:
        del selector, has_text, index, timeout_ms
        raise NotImplementedError(
            "Download capture is not supported by the urllib web session fallback."
        )

    def screenshot(self, path: str) -> None:
        del path
        return None


class UrllibWebAppRuntime(AbstractContextManager[UrllibWebAppSession]):
    def __enter__(self) -> UrllibWebAppSession:
        return UrllibWebAppSession()

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        return None
