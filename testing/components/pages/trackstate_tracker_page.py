from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from testing.components.pages.trackstate_live_app_page import TrackStateLiveAppPage
from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError


@dataclass(frozen=True)
class RuntimeObservation:
    kind: str
    body_text: str


@dataclass(frozen=True)
class ConnectionObservation:
    dialog_text: str
    body_text: str


@dataclass(frozen=True)
class CreateIssueObservation:
    board_text_before: str
    dialog_text: str
    detail_text: str
    board_text_after: str
    created_issue_key: str | None


class TrackStateTrackerPage:
    LOAD_ERROR_TEXT = TrackStateLiveAppPage.LOAD_ERROR_TEXT
    LOAD_ERROR_TEXT_VARIANTS = TrackStateLiveAppPage.LOAD_ERROR_TEXT_VARIANTS
    BOARD_LABEL = "Board"
    BOARD_HINT = "Drag-ready workflow columns backed by Git files"
    CREATE_ISSUE_LABEL = "Create issue"
    SUMMARY_LABEL = "Summary"
    DESCRIPTION_LABEL = "Description"
    SAVE_LABEL = "Save"
    CANCEL_LABEL = "Cancel"
    BACK_TO_BOARD_LABEL = "Back to Board"
    CONNECTED_BANNER_TEMPLATE = (
        "Connected as {user_login} to {repository}. Drag cards to commit status changes."
    )
    SAVE_FAILED_PREFIX = "Save failed:"
    BUTTON_SELECTOR = 'flt-semantics[role="button"]'
    CONNECT_BUTTON_SELECTOR = 'flt-semantics[role="button"][aria-label="Connect GitHub"]'

    def __init__(self, session: WebAppSession, app_url: str) -> None:
        self.session = session
        self.app_url = app_url
        self._live_page = TrackStateLiveAppPage(session, app_url)

    def open(self) -> RuntimeObservation:
        self._live_page.open()
        try:
            wait_match = self.session.wait_for_any_text(
                [*self.LOAD_ERROR_TEXT_VARIANTS, "Connect GitHub", self.BOARD_LABEL],
                timeout_ms=120_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 1 failed: the deployed app never reached an interactive state. "
                f"Visible body text: {self.body_text()}",
            ) from error
        if wait_match.matched_text in self.LOAD_ERROR_TEXT_VARIANTS:
            return RuntimeObservation(
                kind="data-load-failed",
                body_text=wait_match.body_text,
            )
        return RuntimeObservation(kind="ready", body_text=wait_match.body_text)

    def connect_with_token(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> ConnectionObservation:
        if self.session.count(self.CONNECT_BUTTON_SELECTOR) == 0:
            return ConnectionObservation(
                dialog_text="",
                body_text=self.body_text(),
            )

        self._live_page.open_connect_dialog()
        dialog_state = self._live_page.read_connect_dialog_state()
        dialog_text = dialog_state.body_text
        for expected_text in (
            "Connect GitHub",
            "Connect token",
            repository,
        ):
            if expected_text not in dialog_text:
                raise AssertionError(
                    f'Step 2 failed: the connect dialog did not show "{expected_text}". '
                    f"Observed dialog text: {dialog_text}",
                )
        if dialog_state.fine_grained_token_input_count != 1:
            raise AssertionError(
                "Step 2 failed: the connect dialog did not expose exactly one "
                "Fine-grained token field.",
            )

        self._live_page.fill_fine_grained_token(token)
        self.session.press(
            TrackStateLiveAppPage.TOKEN_INPUT_SELECTOR,
            "Tab",
            timeout_ms=30_000,
        )
        self._live_page.submit_connect_token()

        connected_banner = self.CONNECTED_BANNER_TEMPLATE.format(
            user_login=user_login,
            repository=repository,
        )
        wait_match = self.session.wait_for_any_text(
            [connected_banner, "GitHub connection failed:"],
            timeout_ms=120_000,
        )
        if wait_match.matched_text != connected_banner:
            raise AssertionError(
                "Step 2 failed: the token connect flow did not reach the connected state. "
                f"Observed body text: {wait_match.body_text}",
            )
        return ConnectionObservation(
            dialog_text=dialog_text,
            body_text=wait_match.body_text,
        )

    def create_issue_from_board(
        self,
        *,
        summary: str,
        description: str,
    ) -> CreateIssueObservation:
        board_text_before = self.open_board()
        if summary in board_text_before:
            raise AssertionError(
                "Precondition failed: the unique TS-305 issue summary was already visible "
                f"before creation. Summary: {summary}",
            )
        if self.session.count(self.BUTTON_SELECTOR, has_text=summary) != 0:
            raise AssertionError(
                "Precondition failed: a board card containing the unique TS-305 summary "
                f"already existed before creation. Summary: {summary}",
            )

        self.session.click(self.BUTTON_SELECTOR, has_text=self.CREATE_ISSUE_LABEL)
        self._wait_for_labeled_field(self.SUMMARY_LABEL)
        self._wait_for_labeled_field(self.DESCRIPTION_LABEL)
        dialog_text = self.body_text()
        for expected_text in (
            self.CREATE_ISSUE_LABEL,
            self.SUMMARY_LABEL,
            self.DESCRIPTION_LABEL,
            self.SAVE_LABEL,
            self.CANCEL_LABEL,
        ):
            if expected_text not in dialog_text:
                raise AssertionError(
                    f'Step 2 failed: the create issue dialog did not show "{expected_text}". '
                    f"Observed dialog text: {dialog_text}",
                )

        self._fill_labeled_field(self.SUMMARY_LABEL, summary)
        self._fill_labeled_field(self.DESCRIPTION_LABEL, description)
        self.session.click(self.BUTTON_SELECTOR, has_text=self.SAVE_LABEL)

        wait_match = self.session.wait_for_any_text(
            [self.BACK_TO_BOARD_LABEL, self.SAVE_FAILED_PREFIX],
            timeout_ms=180_000,
        )
        if wait_match.matched_text == self.SAVE_FAILED_PREFIX:
            raise AssertionError(
                "Step 3 failed: saving the new issue showed a visible save error instead "
                f"of opening the new issue detail. Observed body text: {wait_match.body_text}",
            )

        detail_text = self.body_text()
        if summary not in detail_text:
            raise AssertionError(
                "Step 4 failed: the issue detail did not render the newly created summary. "
                f"Expected summary: {summary}. Observed detail text: {detail_text}",
            )
        if self.BACK_TO_BOARD_LABEL not in detail_text:
            raise AssertionError(
                "Step 4 failed: the issue detail did not expose the Back to Board action. "
                f"Observed detail text: {detail_text}",
            )

        self.session.click(self.BUTTON_SELECTOR, has_text=self.BACK_TO_BOARD_LABEL)
        self.session.wait_for_text(self.BOARD_HINT, timeout_ms=60_000)
        self.session.wait_for_selector(
            self.BUTTON_SELECTOR,
            has_text=summary,
            timeout_ms=120_000,
        )
        board_text_after = self.body_text()
        if summary not in board_text_after:
            raise AssertionError(
                "Step 5 failed: the Board view did not show the newly created issue after "
                f"returning from the detail view. Expected summary: {summary}. "
                f"Observed Board text: {board_text_after}",
            )
        if self.BACK_TO_BOARD_LABEL in board_text_after:
            raise AssertionError(
                "Step 5 failed: the issue detail remained open after using Back to Board. "
                f"Observed Board text: {board_text_after}",
            )

        return CreateIssueObservation(
            board_text_before=board_text_before,
            dialog_text=dialog_text,
            detail_text=detail_text,
            board_text_after=board_text_after,
            created_issue_key=self.extract_issue_key(summary, detail_text),
        )

    def open_board(self) -> str:
        navigation_errors: list[str] = []
        for navigate in (
            lambda: self.session.press("body", "2", timeout_ms=10_000),
            lambda: self.session.click(
                self.BUTTON_SELECTOR,
                has_text=self.BOARD_LABEL,
                index=1,
                timeout_ms=10_000,
            ),
            lambda: self.session.click(
                self.BUTTON_SELECTOR,
                has_text=self.BOARD_LABEL,
                index=0,
                timeout_ms=10_000,
            ),
        ):
            try:
                navigate()
                board_text = self.session.wait_for_text(
                    self.BOARD_HINT,
                    timeout_ms=15_000,
                )
                return board_text
            except (AssertionError, WebAppTimeoutError) as error:
                navigation_errors.append(str(error))
        raise AssertionError(
            "Step 1 failed: the test could not switch from Dashboard to Board using the "
            f"live navigation controls. Visible body text: {self.body_text()}. "
            f"Navigation attempts: {navigation_errors}",
        )

    def body_text(self) -> str:
        return self.session.body_text()

    def screenshot(self, path: str) -> None:
        self.session.screenshot(path)

    def observe_interactive_shell(
        self,
        required_navigation_labels: Sequence[str],
        *,
        timeout_ms: int = 120_000,
    ) -> dict[str, object]:
        try:
            payload = self.session.wait_for_function(
                """
                (requiredNavigationLabels) => {
                  const bodyText = document.body?.innerText ?? '';
                  const visibleNavigationLabels = requiredNavigationLabels.filter(
                    (label) => bodyText.includes(label),
                  );
                  const fatalBannerVisible = bodyText.includes('TrackState data was not found');
                  const connectGitHubVisible = bodyText.includes('Connect GitHub');
                  const shellReady = visibleNavigationLabels.length === requiredNavigationLabels.length;
                  return shellReady || fatalBannerVisible || connectGitHubVisible
                    ? {
                        bodyText,
                        visibleNavigationLabels,
                        fatalBannerVisible,
                        connectGitHubVisible,
                        shellReady,
                      }
                    : null;
                }
                """,
                arg=list(required_navigation_labels),
                timeout_ms=timeout_ms,
            )
        except Exception:
            return self._interactive_shell_fallback()
        if not isinstance(payload, dict):
            return self._interactive_shell_fallback()
        return {
            "body_text": str(payload.get("bodyText", "")),
            "visible_navigation_labels": [
                str(label) for label in payload.get("visibleNavigationLabels", [])
            ],
            "fatal_banner_visible": bool(payload.get("fatalBannerVisible")),
            "connect_github_visible": bool(payload.get("connectGitHubVisible")),
            "shell_ready": bool(payload.get("shellReady")),
        }

    def snapshot_local_storage(
        self,
        keys: Sequence[str],
    ) -> dict[str, str | None]:
        payload = self.session.evaluate(
            """
            (keys) => {
              const snapshot = {};
              for (const key of keys) {
                snapshot[key] = window.localStorage.getItem(key);
              }
              return snapshot;
            }
            """,
            arg=list(keys),
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                f"Expected a workspace storage snapshot map, got: {payload!r}",
            )
        return {
            str(key): (None if value is None else str(value))
            for key, value in payload.items()
        }

    @staticmethod
    def extract_issue_key(summary: str, body_text: str) -> str | None:
        pattern = re.compile(
            rf"\b([A-Z][A-Z0-9]+-\d+)\b[\s\u00b7]+{re.escape(summary)}\b",
        )
        match = pattern.search(body_text)
        if match is None:
            return None
        return match.group(1)

    def _wait_for_labeled_field(self, label: str) -> str:
        errors: list[str] = []
        for selector in self._candidate_field_selectors(label):
            try:
                self.session.wait_for_selector(selector, timeout_ms=10_000)
                return selector
            except WebAppTimeoutError as error:
                errors.append(str(error))
        raise AssertionError(
            f'Step 2 failed: no visible "{label}" field was found in the create issue dialog. '
            f"Visible body text: {self.body_text()}. Selector attempts: {errors}",
        )

    def _fill_labeled_field(self, label: str, value: str) -> None:
        selector = self._wait_for_labeled_field(label)
        self.session.fill(selector, value, timeout_ms=30_000)

    @staticmethod
    def _candidate_field_selectors(label: str) -> tuple[str, ...]:
        return (
            f'input[aria-label="{label}"]',
            f'textarea[aria-label="{label}"]',
            f'[role="textbox"][aria-label="{label}"]',
        )

    def _interactive_shell_fallback(self) -> dict[str, object]:
        body_text = self.body_text()
        return {
            "body_text": body_text,
            "visible_navigation_labels": [],
            "fatal_banner_visible": "TrackState data was not found" in body_text,
            "connect_github_visible": "Connect GitHub" in body_text,
            "shell_ready": False,
        }
