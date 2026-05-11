from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class CreateIssueDialogObservation:
    board_text: str
    dialog_text: str
    summary_field_count: int
    assignee_field_count: int
    labels_field_count: int
    labels_helper_visible: bool


@dataclass(frozen=True)
class AssigneePickerObservation:
    query: str
    typed_value: str
    selected_value: str
    option_count: int
    matching_option_count: int
    listbox_count: int
    body_text: str


@dataclass(frozen=True)
class LabelTokenObservation:
    labels_value_after_enter: str
    labels_value_before_comma: str
    labels_value_after_comma: str
    frontend_token_count: int
    bug_token_count: int
    body_text: str


class LiveCreateIssueFormPage:
    _button_selector = 'flt-semantics[role="button"]'
    _generic_semantics_selector = "flt-semantics"
    _summary_selector = 'input[aria-label="Summary"]'
    _assignee_selector = 'input[aria-label="Assignee"]'
    _labels_selector = 'input[aria-label="Labels"]'
    _option_selector = '[role="option"]'
    _listbox_selector = '[role="listbox"]'
    _labels_helper_text = "Press comma or Enter to add a label."

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def open_create_issue_dialog(self) -> CreateIssueDialogObservation:
        board_text = self._tracker_page.open_board()
        create_issue_opened = False
        for selector, has_text in (
            (self._button_selector, TrackStateTrackerPage.CREATE_ISSUE_LABEL),
            (self._generic_semantics_selector, TrackStateTrackerPage.CREATE_ISSUE_LABEL),
            ('[aria-label="Create issue"]', None),
        ):
            if self._candidate_count(selector, has_text=has_text) == 0:
                continue
            try:
                self._session.click(
                    selector,
                    has_text=has_text,
                    timeout_ms=15_000,
                )
                create_issue_opened = True
                break
            except WebAppTimeoutError:
                continue

        if not create_issue_opened:
            raise AssertionError(
                "Step 1 failed: the live app did not expose any visible "
                '"Create issue" action, so the browser-native create form could not be '
                "opened.\n"
                f"Observed Board text:\n{board_text}\n\n"
                f"Observed page text:\n{self.current_body_text()}",
            )

        for selector in (
            self._summary_selector,
            self._assignee_selector,
            self._labels_selector,
        ):
            try:
                self._session.wait_for_selector(selector, timeout_ms=15_000)
            except WebAppTimeoutError as error:
                raise AssertionError(
                    "Step 1 failed: the create issue dialog opened incompletely and did "
                    f'not expose the expected field {selector!r}.\n'
                    f"Observed page text:\n{self.current_body_text()}",
                ) from error

        dialog_text = self.current_body_text()
        return CreateIssueDialogObservation(
            board_text=board_text,
            dialog_text=dialog_text,
            summary_field_count=self._session.count(self._summary_selector),
            assignee_field_count=self._session.count(self._assignee_selector),
            labels_field_count=self._session.count(self._labels_selector),
            labels_helper_visible=self._labels_helper_text in dialog_text,
        )

    def search_assignee(
        self,
        *,
        query: str,
        expected_suggestion: str,
    ) -> AssigneePickerObservation:
        self._session.click(self._assignee_selector, timeout_ms=15_000)
        self._session.fill(self._assignee_selector, query, timeout_ms=15_000)

        matching_option_count = self._wait_for_assignee_suggestion(expected_suggestion)
        typed_value = self._session.read_value(
            self._assignee_selector,
            timeout_ms=15_000,
        )
        selected_value = self._select_assignee_suggestion(expected_suggestion)
        body_text = self.current_body_text()
        return AssigneePickerObservation(
            query=query,
            typed_value=typed_value,
            selected_value=selected_value,
            option_count=self._session.count(self._option_selector),
            matching_option_count=matching_option_count,
            listbox_count=self._session.count(self._listbox_selector),
            body_text=body_text,
        )

    def commit_labels(self) -> LabelTokenObservation:
        self._session.click(self._labels_selector, timeout_ms=15_000)
        self._session.fill(self._labels_selector, "frontend", timeout_ms=15_000)
        self._session.press(self._labels_selector, "Enter", timeout_ms=15_000)
        labels_value_after_enter = self._session.wait_for_input_value(
            self._labels_selector,
            "",
            timeout_ms=15_000,
        )
        self._wait_for_token("frontend")

        self._session.fill(self._labels_selector, "bug", timeout_ms=15_000)
        labels_value_before_comma = self._session.read_value(
            self._labels_selector,
            timeout_ms=15_000,
        )
        self._session.press(self._labels_selector, ",", timeout_ms=15_000)
        labels_value_after_comma = self._session.wait_for_input_value(
            self._labels_selector,
            "",
            timeout_ms=15_000,
        )
        self._wait_for_token("bug")

        return LabelTokenObservation(
            labels_value_after_enter=labels_value_after_enter,
            labels_value_before_comma=labels_value_before_comma,
            labels_value_after_comma=labels_value_after_comma,
            frontend_token_count=self._token_count("frontend"),
            bug_token_count=self._token_count("bug"),
            body_text=self.current_body_text(),
        )

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def _wait_for_assignee_suggestion(self, expected_suggestion: str) -> int:
        candidates = (
            (self._option_selector, expected_suggestion),
            (self._button_selector, expected_suggestion),
            (self._listbox_selector, None),
        )
        for selector, has_text in candidates:
            try:
                self._session.wait_for_selector(
                    selector,
                    has_text=has_text,
                    timeout_ms=10_000,
                )
            except WebAppTimeoutError:
                continue
            return self._candidate_count(selector, has_text=has_text)
        return 0

    def _select_assignee_suggestion(self, expected_suggestion: str) -> str:
        selection_errors: list[str] = []
        for selector in (self._option_selector, self._button_selector):
            if self._candidate_count(selector, has_text=expected_suggestion) <= 0:
                continue
            try:
                self._session.click(
                    selector,
                    has_text=expected_suggestion,
                    timeout_ms=15_000,
                )
                return self._session.wait_for_input_value(
                    self._assignee_selector,
                    expected_suggestion,
                    timeout_ms=15_000,
                )
            except WebAppTimeoutError as error:
                selection_errors.append(str(error))

        if self._candidate_count(self._listbox_selector, has_text=None) > 0:
            try:
                self._session.press(
                    self._assignee_selector,
                    "ArrowDown",
                    timeout_ms=15_000,
                )
                self._session.press(
                    self._assignee_selector,
                    "Enter",
                    timeout_ms=15_000,
                )
                return self._session.wait_for_input_value(
                    self._assignee_selector,
                    expected_suggestion,
                    timeout_ms=15_000,
                )
            except WebAppTimeoutError as error:
                selection_errors.append(str(error))

        raise AssertionError(
            "Step 3 failed: the assignee picker appeared but the test could not select "
            f"the collaborator suggestion {expected_suggestion!r}.\n"
            f"Selection attempts: {selection_errors}\n"
            f"Observed page text:\n{self.current_body_text()}",
        )

    def _wait_for_token(self, token: str) -> None:
        try:
            self._session.wait_for_selector(
                self._generic_semantics_selector,
                has_text=token,
                timeout_ms=15_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Labels token "{token}" never became visible in the create issue form.\n'
                f"Observed page text:\n{self.current_body_text()}",
            ) from error

    def _token_count(self, token: str) -> int:
        return self._session.count(self._generic_semantics_selector, has_text=token)

    def _candidate_count(self, selector: str, *, has_text: str | None) -> int:
        return self._session.count(selector, has_text=has_text)
