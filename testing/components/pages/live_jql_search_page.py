from __future__ import annotations

from dataclasses import dataclass
import re

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class LiveJqlSearchObservation:
    query: str
    visible_query: str
    body_text: str
    count_summary: str | None
    issue_result_count: int
    issue_result_labels: tuple[str, ...]


class LiveJqlSearchPage:
    _button_selector = 'flt-semantics[role="button"]'
    _active_button_selector = 'flt-semantics[role="button"][aria-current="true"]'
    _panel_selector = 'flt-semantics[role="group"][aria-label="JQL Search"]'
    _panel_search_field_selector = (
        f'{_panel_selector} input[data-semantics-role="text-field"]:not([disabled])'
    )
    _search_field_candidates = (
        _panel_search_field_selector,
        f'{_panel_selector} textarea[data-semantics-role="text-field"]:not([disabled])',
        f'{_panel_selector} [data-semantics-role="text-field"]:not([disabled])',
        f'{_panel_selector} input[aria-label^="Search issues"]',
        f'{_panel_selector} textarea[aria-label="Search issues"]',
        f'{_panel_selector} [role="textbox"][aria-label="Search issues"]',
    )
    _issue_button_selector = (
        f'{_panel_selector} flt-semantics[role="button"][aria-label^="Open DEMO-"]'
    )
    _no_results_text = "No results"

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def open(self) -> None:
        if not self._is_active():
            self._session.click(
                self._button_selector,
                has_text="JQL Search",
                timeout_ms=30_000,
            )
        try:
            self._session.wait_for_selector(
                self._active_button_selector,
                has_text="JQL Search",
                timeout_ms=30_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 3 failed: the live app did not switch the sidebar navigation "
                "into the JQL Search section.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        self._wait_for_search_field()

    def search_for_unique_issue(
        self,
        *,
        query: str,
    ) -> LiveJqlSearchObservation:
        return self.search(query=query)

    def search_for_no_results(
        self,
        *,
        query: str,
    ) -> LiveJqlSearchObservation:
        return self.search(query=query)

    def search(self, *, query: str) -> LiveJqlSearchObservation:
        return self.search_with_expected_counts(query=query)

    def search_with_expected_counts(
        self,
        *,
        query: str,
        expected_count_summaries: tuple[str, ...] | None = None,
    ) -> LiveJqlSearchObservation:
        field_selector, field_index = self._submit_query(query)
        self._wait_for_count_summary(expected_count_summaries=expected_count_summaries)
        return self._observe(
            query=query,
            field_selector=field_selector,
            field_index=field_index,
        )

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def _submit_query(self, query: str) -> tuple[str, int]:
        self.open()
        field_selector, field_index = self._wait_for_search_field()
        self._session.focus(
            field_selector,
            index=field_index,
            timeout_ms=30_000,
        )
        self._session.fill(
            field_selector,
            query,
            index=field_index,
            timeout_ms=30_000,
        )
        self._session.wait_for_input_value(
            field_selector,
            query,
            index=field_index,
            timeout_ms=30_000,
        )
        self._session.press(
            field_selector,
            "Enter",
            index=field_index,
            timeout_ms=30_000,
        )
        return field_selector, field_index

    def _observe(
        self,
        *,
        query: str,
        field_selector: str,
        field_index: int,
    ) -> LiveJqlSearchObservation:
        body_text = self.current_body_text()
        return LiveJqlSearchObservation(
            query=query,
            visible_query=self._session.read_value(
                field_selector,
                index=field_index,
                timeout_ms=30_000,
            ),
            body_text=body_text,
            count_summary=self._count_summary(body_text),
            issue_result_count=self._session.count(self._issue_button_selector),
            issue_result_labels=self._issue_result_labels(),
        )

    def _wait_for_search_field(self) -> tuple[str, int]:
        errors: list[str] = []
        for selector in self._search_field_candidates:
            try:
                self._session.wait_for_selector(selector, timeout_ms=10_000)
                return selector, 0
            except WebAppTimeoutError as error:
                errors.append(str(error))
        raise AssertionError(
            "Step 3 failed: the live app did not expose the visible JQL Search text "
            "field inside the JQL Search panel.\n"
            f"Observed body text:\n{self.current_body_text()}\n"
            f"Selector attempts: {errors}",
        )

    def _is_active(self) -> bool:
        return self._session.count(
            self._active_button_selector,
            has_text="JQL Search",
        ) > 0

    def _wait_for_count_summary(
        self,
        *,
        expected_count_summaries: tuple[str, ...] | None = None,
    ) -> None:
        count_summaries = expected_count_summaries or ("1 issue", "No issues")
        try:
            self._session.wait_for_any_text(
                list(count_summaries),
                timeout_ms=60_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 4 failed: the live JQL Search panel never rendered an updated "
                'issue-count summary after the query was submitted.\n'
                f"Expected summaries: {count_summaries}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    @staticmethod
    def _count_summary(body_text: str) -> str | None:
        match = re.search(r"\b(?:No issues|\d+ issues?)\b", body_text)
        if match is None:
            return None
        return match.group(0)

    def _issue_result_labels(self) -> tuple[str, ...]:
        payload = self._session.evaluate(
            """
            (selector) => Array.from(document.querySelectorAll(selector))
              .map((element) => element.getAttribute("aria-label") ?? "")
              .filter((label) => label.length > 0)
            """,
            arg=self._issue_button_selector,
        )
        if not isinstance(payload, list):
            return ()
        return tuple(str(label) for label in payload)
