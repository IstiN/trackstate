from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _HtmlControl:
    tag: str
    attrs: dict[str, str]
    value: str


class _FormControlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._controls: list[_HtmlControl] = []
        self._active_textarea_attrs: dict[str, str] | None = None
        self._active_textarea_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered_tag = tag.lower()
        normalized_attrs = {
            str(name).lower(): value
            for name, value in attrs
            if isinstance(name, str) and isinstance(value, str)
        }
        if lowered_tag == "input":
            self._controls.append(
                _HtmlControl(
                    tag=lowered_tag,
                    attrs=normalized_attrs,
                    value=normalized_attrs.get("value", ""),
                )
            )
            return
        if lowered_tag == "textarea":
            self._active_textarea_attrs = normalized_attrs
            self._active_textarea_parts = []

    def handle_data(self, data: str) -> None:
        if self._active_textarea_attrs is not None:
            self._active_textarea_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "textarea" or self._active_textarea_attrs is None:
            return
        self._controls.append(
            _HtmlControl(
                tag="textarea",
                attrs=self._active_textarea_attrs,
                value=unescape("".join(self._active_textarea_parts)),
            )
        )
        self._active_textarea_attrs = None
        self._active_textarea_parts = []

    def controls(self) -> tuple[_HtmlControl, ...]:
        return tuple(self._controls)


class UrllibWebAppSession(WebAppSession):
    def __init__(self) -> None:
        self._body_text = ""
        self._controls: tuple[_HtmlControl, ...] = ()

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
        control_parser = _FormControlParser()
        control_parser.feed(html)
        self._controls = control_parser.controls()

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
        del has_text, timeout_ms
        matches = [
            control
            for control in self._controls
            if _control_matches_selector(control, selector)
        ]
        if index >= len(matches):
            raise WebAppTimeoutError(
                f'Timed out reading the value for selector "{selector}".'
            )
        return matches[index].value

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

    def wait_for_active_element_change(
        self,
        previous_outer_html: str,
        *,
        timeout_ms: int = 2_000,
    ) -> FocusedElementObservation:
        del previous_outer_html, timeout_ms
        raise NotImplementedError(
            "Active-element change waits are not supported by the urllib web session fallback."
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

    def start_network_recording(self, *, name: str, url_fragment: str) -> None:
        del name, url_fragment
        return None

    def read_network_log(self, *, name: str) -> list[dict[str, object]]:
        del name
        return []

    def screenshot(self, path: str, *, full_page: bool = True) -> None:
        del path, full_page
        return None


class UrllibWebAppRuntime(AbstractContextManager[UrllibWebAppSession]):
    def __enter__(self) -> UrllibWebAppSession:
        return UrllibWebAppSession()

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        return None


def _parse_selector_rules(
    selector: str,
) -> tuple[str | None, str | None, tuple[tuple[str, str, str], ...]]:
    normalized_selector = selector.strip()
    tag_match = re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*", normalized_selector)
    tag = tag_match.group(0).lower() if tag_match is not None else None
    id_match = re.search(r"#([a-zA-Z_][a-zA-Z0-9_-]*)", normalized_selector)
    identifier = id_match.group(1).lower() if id_match is not None else None
    attr_rules = tuple(
        (
            match.group(1).strip().lower(),
            match.group(2),
            match.group(4),
        )
        for match in re.finditer(
            r"""\[([^\]=*]+)(\*=|=)(["'])(.*?)\3\]""",
            normalized_selector,
        )
    )
    return tag, identifier, attr_rules


def _matches_attr_rule(
    attrs: dict[str, str],
    rule: tuple[str, str, str],
) -> bool:
    attr_name, operator, expected_value = rule
    actual_value = attrs.get(attr_name)
    if actual_value is None:
        return False
    normalized_actual = actual_value.lower()
    normalized_expected = expected_value.lower()
    if operator == "=":
        return normalized_actual == normalized_expected
    if operator == "*=":
        return normalized_expected in normalized_actual
    return False


def _control_matches_selector(control: _HtmlControl, selector: str) -> bool:
    tag, identifier, attr_rules = _parse_selector_rules(selector)
    if tag is not None and control.tag != tag:
        return False
    if identifier is not None and control.attrs.get("id", "").lower() != identifier:
        return False
    return all(_matches_attr_rule(control.attrs, rule) for rule in attr_rules)
