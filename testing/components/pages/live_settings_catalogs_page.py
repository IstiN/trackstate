from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class CatalogEditorPresentationObservation:
    title: str
    body_text: str
    viewport_width: float
    viewport_height: float
    input_x: float
    input_y: float
    input_width: float
    input_height: float


@dataclass(frozen=True)
class CatalogEditorObservation:
    title: str
    body_text: str
    id_value: str
    name_value: str
    presentation: CatalogEditorPresentationObservation


class LiveSettingsCatalogsPage:
    _button_selector = 'flt-semantics[role="button"]'
    _tab_selector = 'flt-semantics[role="tab"]'
    _settings_admin_heading = "Project settings administration"

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._issue_page = LiveIssueDetailCollaborationPage(tracker_page)

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> None:
        self._issue_page.ensure_connected(
            token=token,
            repository=repository,
            user_login=user_login,
        )

    def dismiss_connection_banner(self) -> None:
        self._issue_page.dismiss_connection_banner()

    def open_settings_admin(self) -> str:
        if self._settings_admin_heading in self.current_body_text():
            return self.current_body_text()
        self._session.click(
            self._button_selector,
            has_text="Settings",
            timeout_ms=30_000,
        )
        return self._session.wait_for_text(
            self._settings_admin_heading,
            timeout_ms=60_000,
        )

    def open_catalog_tab(self, *, label: str, add_label: str) -> str:
        selector = self._tab_selector_for(label)
        self._scroll_into_view(selector)
        rect = self._session.bounding_box(selector, timeout_ms=30_000)
        self._session.mouse_click(rect.x + (rect.width / 2), rect.y + (rect.height / 2))
        self._session.wait_for_function(
            """
            ({ tabSelector, addLabel }) => {
              const tab = document.querySelector(tabSelector);
              const hasAddAction = Array.from(
                document.querySelectorAll('flt-semantics[aria-label]'),
              ).some(
                (candidate) => (candidate.getAttribute('aria-label') ?? '').trim() === addLabel,
              );
              return !!tab
                && tab.getAttribute('aria-selected') === 'true'
                && hasAddAction;
            }
            """,
            arg={"tabSelector": selector, "addLabel": add_label},
            timeout_ms=30_000,
        )
        return self.current_body_text()

    def open_editor(self, *, button_label: str, title: str) -> CatalogEditorObservation:
        self._click_button_by_aria_label(button_label)
        self._wait_for_editor(title)
        return self.read_editor_observation(title)

    def fill_editor_input(self, label: str, value: str) -> None:
        selector = self._editor_input_selector(label)
        self._session.focus(selector, timeout_ms=30_000)
        self._session.fill(selector, value, timeout_ms=30_000)
        self._session.wait_for_input_value(selector, value, timeout_ms=30_000)
        self._session.press(selector, "Tab", timeout_ms=30_000)

    def read_editor_observation(self, title: str) -> CatalogEditorObservation:
        payload = self._session.evaluate(
            """
            (expectedTitle) => {
              const readInput = (label) => {
                const input = document.querySelector(`input[aria-label="${label}"]`);
                return input ? String(input.value ?? '') : '';
              };
              const idInput = document.querySelector('input[aria-label="ID"]');
              const rect = idInput?.getBoundingClientRect();
              return {
                bodyText: document.body?.innerText ?? '',
                title: expectedTitle,
                idValue: readInput('ID'),
                nameValue: readInput('Name'),
                viewportWidth: window.innerWidth,
                viewportHeight: window.innerHeight,
                inputX: rect?.x ?? 0,
                inputY: rect?.y ?? 0,
                inputWidth: rect?.width ?? 0,
                inputHeight: rect?.height ?? 0,
              };
            }
            """,
            arg=title,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                f'The "{title}" editor did not expose a readable DOM snapshot.\n'
                f"Observed body text:\n{self.current_body_text()}",
            )
        presentation = CatalogEditorPresentationObservation(
            title=str(payload["title"]),
            body_text=str(payload["bodyText"]),
            viewport_width=float(payload["viewportWidth"]),
            viewport_height=float(payload["viewportHeight"]),
            input_x=float(payload["inputX"]),
            input_y=float(payload["inputY"]),
            input_width=float(payload["inputWidth"]),
            input_height=float(payload["inputHeight"]),
        )
        return CatalogEditorObservation(
            title=str(payload["title"]),
            body_text=str(payload["bodyText"]),
            id_value=str(payload["idValue"]),
            name_value=str(payload["nameValue"]),
            presentation=presentation,
        )

    def save_editor(self, title: str) -> None:
        self._session.click(self._button_selector, has_text="Save", timeout_ms=30_000)
        self._session.wait_for_function(
            """
            (expectedTitle) => !(document.body?.innerText ?? '').includes(expectedTitle)
            """,
            arg=title,
            timeout_ms=30_000,
        )

    def delete_entry(self, delete_label: str, *, removed_text: str) -> None:
        self._click_button_by_aria_label(delete_label)
        self._session.wait_for_function(
            """
            (label) => !Array.from(document.querySelectorAll('flt-semantics[aria-label]')).some(
              (candidate) => (candidate.getAttribute('aria-label') ?? '').trim() === label,
            )
            """,
            arg=delete_label,
            timeout_ms=30_000,
        )
        if removed_text in self.current_body_text():
            raise AssertionError(
                f'The deleted entry text "{removed_text}" remained visible after using '
                f'"{delete_label}".\nObserved body text:\n{self.current_body_text()}',
            )

    def save_settings(self) -> None:
        self._click_button_by_aria_label("Save settings")
        self._session.wait_for_function(
            """
            () => Array.from(document.querySelectorAll('flt-semantics[aria-label]')).some(
              (candidate) => (candidate.getAttribute('aria-label') ?? '').trim() === 'Save settings',
            )
            """,
            timeout_ms=30_000,
        )

    def action_label_exists(self, label: str) -> bool:
        return self._session.count(self._button_by_aria_label(label)) > 0

    def aria_label_exists(self, label: str) -> bool:
        return self._session.count(
            f'flt-semantics[aria-label="{self._escape(label)}"]',
        ) > 0

    def aria_labels(self) -> list[str]:
        payload = self._session.evaluate(
            """
            () => Array.from(document.querySelectorAll('flt-semantics[aria-label]'))
              .map((candidate) => (candidate.getAttribute('aria-label') ?? '').trim())
              .filter((label) => label.length > 0)
            """,
        )
        if not isinstance(payload, list):
            raise AssertionError(
                "The live settings page did not expose readable aria-labels.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return [str(item) for item in payload]

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def _wait_for_editor(self, title: str) -> None:
        self._session.wait_for_function(
            """
            (expectedTitle) => {
              const bodyText = document.body?.innerText ?? '';
              return bodyText.includes(expectedTitle)
                && document.querySelectorAll('input[aria-label="ID"]').length > 0
                && document.querySelectorAll('input[aria-label="Name"]').length > 0;
            }
            """,
            arg=title,
            timeout_ms=30_000,
        )

    def _click_button_by_aria_label(self, label: str) -> None:
        selector = self._nested_button_by_aria_label(label)
        self._scroll_into_view(selector)
        self._session.click(selector, timeout_ms=30_000)

    def _tab_selector_for(self, label: str) -> str:
        return f'{self._tab_selector}[aria-label="{self._escape(label)}"]'

    def _button_by_aria_label(self, label: str) -> str:
        return f'{self._button_selector}[aria-label="{self._escape(label)}"]'

    def _nested_button_by_aria_label(self, label: str) -> str:
        return f'{self._button_by_aria_label(label)} > {self._button_selector}'

    def _editor_input_selector(self, label: str) -> str:
        return f'input[aria-label="{self._escape(label)}"]'

    def _scroll_into_view(self, selector: str) -> None:
        self._session.evaluate(
            """
            (value) => {
              document.querySelector(value)?.scrollIntoView({ block: 'center' });
            }
            """,
            arg=selector,
        )

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
