from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, Sequence


WaitState = Literal["attached", "detached", "hidden", "visible"]


class WebAppTimeoutError(Exception):
    """Raised when the UI does not reach the expected state before timeout."""


@dataclass(frozen=True)
class WaitMatch:
    matched_text: str
    body_text: str


@dataclass(frozen=True)
class ElementBoundingBox:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class FocusedElementObservation:
    tag_name: str
    role: str | None
    accessible_name: str | None
    text: str
    tabindex: str | None
    outer_html: str


@dataclass(frozen=True)
class NewPageObservation:
    url: str
    page_count_before: int
    page_count_after: int


class WebAppSession(Protocol):
    def set_viewport_size(self, *, width: int, height: int) -> None: ...

    def goto(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 120_000,
    ) -> None: ...

    def activate_accessibility(self) -> None: ...

    def wait_for_selector(
        self,
        selector: str,
        *,
        state: WaitState = "visible",
        timeout_ms: int = 30_000,
        has_text: str | None = None,
        index: int = 0,
    ) -> None: ...

    def click(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None: ...

    def fill(
        self,
        selector: str,
        value: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None: ...

    def type_text(
        self,
        selector: str,
        value: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
        delay_ms: int = 50,
    ) -> None: ...

    def press(
        self,
        selector: str,
        key: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None: ...

    def press_key(
        self,
        key: str,
        *,
        timeout_ms: int = 30_000,
    ) -> None: ...

    def click_and_set_files(
        self,
        selector: str,
        files: Sequence[str],
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None: ...

    def count(
        self,
        selector: str,
        *,
        has_text: str | None = None,
    ) -> int: ...

    def focus(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None: ...

    def wait_for_count(
        self,
        selector: str,
        expected_count: int,
        *,
        timeout_ms: int = 30_000,
    ) -> None: ...

    def click_and_choose_file(
        self,
        selector: str,
        file_paths: Sequence[str],
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None: ...

    def read_value(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> str: ...

    def read_text(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> str: ...

    def wait_for_input_value(
        self,
        selector: str,
        expected_value: str,
        *,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> str: ...

    def body_text(self) -> str: ...

    def wait_for_text(
        self,
        text: str,
        *,
        timeout_ms: int = 60_000,
    ) -> str: ...

    def wait_for_text_absence(
        self,
        text: str,
        *,
        timeout_ms: int = 60_000,
    ) -> str: ...

    def wait_for_any_text(
        self,
        texts: Sequence[str],
        *,
        timeout_ms: int = 90_000,
    ) -> WaitMatch: ...

    def evaluate(
        self,
        expression: str,
        *,
        arg: object | None = None,
    ) -> object: ...

    def wait_for_function(
        self,
        expression: str,
        *,
        arg: object | None = None,
        timeout_ms: int = 30_000,
    ) -> object: ...

    def active_element(self) -> FocusedElementObservation: ...

    def wait_for_download_after_keypress(
        self,
        key: str,
        *,
        timeout_ms: int = 30_000,
    ) -> str: ...

    def wait_for_download_after_click(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> str: ...

    def wait_for_new_page_after_keypress(
        self,
        key: str,
        *,
        timeout_ms: int = 30_000,
    ) -> NewPageObservation: ...

    def wait_for_new_page_after_active_element_click(
        self,
        *,
        timeout_ms: int = 30_000,
    ) -> NewPageObservation: ...

    def select_files_after_click(
        self,
        trigger_selector: str,
        files: Sequence[str],
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> None: ...

    def screenshot(self, path: str) -> None: ...

    def bounding_box(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> ElementBoundingBox: ...

    def mouse_move(self, x: float, y: float) -> None: ...

    def mouse_click(self, x: float, y: float, *, delay_ms: int = 0) -> None: ...

    def wait_for_text_absent(
        self,
        text: str,
        *,
        timeout_ms: int = 60_000,
    ) -> str: ...
