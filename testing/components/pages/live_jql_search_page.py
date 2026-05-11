from __future__ import annotations

from dataclasses import dataclass
import re
import time

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class LiveJqlSearchObservation:
    query: str
    visible_query: str
    body_text: str
    count_summary: str | None
    issue_result_count: int
    issue_labels: tuple[str, ...]


class LiveJqlSearchPage:
    _button_selector = 'flt-semantics[role="button"]'
    _active_button_selector = 'flt-semantics[role="button"][aria-current="true"]'
    _issue_button_selector = 'flt-semantics[role="button"][aria-label*="Open DEMO-"]'
    _search_field_candidates = (
        'input[data-semantics-role="text-field"]:not([disabled]):not([aria-label])',
        'textarea[data-semantics-role="text-field"]:not([disabled]):not([aria-label])',
        'input[aria-label="Search issues"]',
        'textarea[aria-label="Search issues"]',
        '[role="textbox"][aria-label="Search issues"]',
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
        field_selector = self._submit_query(query)
        self._wait_for_count_summary(expected_count_summaries=expected_count_summaries)
        return self._observe(query=query, field_selector=field_selector)

    def search_with_verified_result_change(
        self,
        *,
        query: str,
        expected_count_summaries: tuple[str, ...] | None = None,
    ) -> LiveJqlSearchObservation:
        self.open()
        field_selector = self._wait_for_search_field()
        initial_observation = self._observe(query="", field_selector=field_selector)
        self._session.fill(field_selector, query, timeout_ms=30_000)
        self._session.press(field_selector, "Enter", timeout_ms=30_000)
        return self._wait_for_result_change(
            query=query,
            field_selector=field_selector,
            initial_observation=initial_observation,
            expected_count_summaries=expected_count_summaries,
        )

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def _submit_query(self, query: str) -> str:
        self.open()
        field_selector = self._wait_for_search_field()
        self._session.fill(field_selector, query, timeout_ms=30_000)
        self._session.press(field_selector, "Enter", timeout_ms=30_000)
        return field_selector

    def _observe(
        self,
        *,
        query: str,
        field_selector: str,
    ) -> LiveJqlSearchObservation:
        body_text = self.current_body_text()
        issue_labels = self._visible_issue_labels()
        return LiveJqlSearchObservation(
            query=query,
            visible_query=self._session.read_value(field_selector, timeout_ms=30_000),
            body_text=body_text,
            count_summary=self._count_summary(body_text),
            issue_result_count=len(issue_labels),
            issue_labels=issue_labels,
        )

    def _wait_for_search_field(self) -> str:
        errors: list[str] = []
        for selector in self._search_field_candidates:
            try:
                self._session.wait_for_selector(selector, timeout_ms=10_000)
                return selector
            except WebAppTimeoutError as error:
                errors.append(str(error))
        raise AssertionError(
            "Step 3 failed: the live app did not expose the visible JQL Search text "
            "field.\n"
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

    def _wait_for_result_change(
        self,
        *,
        query: str,
        field_selector: str,
        initial_observation: LiveJqlSearchObservation,
        expected_count_summaries: tuple[str, ...] | None = None,
    ) -> LiveJqlSearchObservation:
        deadline = time.monotonic() + 60.0
        latest_observation = self._observe(query=query, field_selector=field_selector)
        while True:
            if (
                latest_observation.visible_query == query
                and (
                    expected_count_summaries is None
                    or latest_observation.count_summary in expected_count_summaries
                )
                and (
                    latest_observation.count_summary != initial_observation.count_summary
                    or latest_observation.issue_labels != initial_observation.issue_labels
                )
            ):
                return latest_observation
            if time.monotonic() >= deadline:
                raise AssertionError(
                    "Step 4 failed: the live JQL Search panel never showed a post-submit "
                    "state that was different from the initial visible results.\n"
                    f"Submitted query: {query}\n"
                    f"Expected summaries after submit: {expected_count_summaries}\n"
                    f"Initial count summary: {initial_observation.count_summary}\n"
                    f"Initial visible issue labels: {list(initial_observation.issue_labels)}\n"
                    f"Latest count summary: {latest_observation.count_summary}\n"
                    f"Latest visible issue labels: {list(latest_observation.issue_labels)}\n"
                    f"Latest body text:\n{latest_observation.body_text}",
                )
            time.sleep(0.25)
            latest_observation = self._observe(query=query, field_selector=field_selector)

    @staticmethod
    def _count_summary(body_text: str) -> str | None:
        match = re.search(r"\b(?:No issues|\d+ issues?)\b", body_text)
        if match is None:
            return None
        return match.group(0)

    def _visible_issue_labels(self) -> tuple[str, ...]:
        payload = self._session.evaluate(
            """
            (selector) => Array.from(document.querySelectorAll(selector))
                .map((element) => (element.getAttribute('aria-label') || '').trim())
                .filter((label) => label.length > 0)
            """,
            arg=self._issue_button_selector,
        )
        if not isinstance(payload, list):
            return ()
        return tuple(str(label) for label in payload if str(label).strip())
