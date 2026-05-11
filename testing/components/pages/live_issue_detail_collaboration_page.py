from __future__ import annotations

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


class LiveIssueDetailCollaborationPage:
    _button_selector = 'flt-semantics[role="button"]'
    _connect_button_selector = 'flt-semantics[aria-label="Connect GitHub"]'
    _connected_button_selector = 'flt-semantics[aria-label="Connected"]'
    _token_input_selector = 'input[aria-label="Fine-grained token"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> None:
        if self._session.count(self._connected_button_selector) > 0:
            return
        if self._session.count(self._connect_button_selector) == 0:
            return

        self._session.click(self._connect_button_selector, timeout_ms=30_000)
        self._session.wait_for_selector(self._token_input_selector, timeout_ms=30_000)
        self._session.fill(self._token_input_selector, token, timeout_ms=30_000)
        self._session.press(self._token_input_selector, "Tab", timeout_ms=30_000)
        self._session.click(
            self._button_selector,
            has_text="Connect token",
            timeout_ms=30_000,
        )
        wait_match = self._session.wait_for_any_text(
            [
                f"Connected as {user_login} to {repository}.",
                "GitHub connection failed:",
            ],
            timeout_ms=120_000,
        )
        if wait_match.matched_text.startswith("GitHub connection failed:"):
            raise AssertionError(
                "Step 1 failed: the hosted GitHub connection flow did not reach the "
                "connected state required for TS-311.\n"
                f"Observed body text:\n{wait_match.body_text}",
            )

    def open_jql_search(self) -> None:
        self._session.click(self._button_selector, has_text="JQL Search", timeout_ms=30_000)
        self._session.wait_for_selector(
            'flt-semantics[role="button"][aria-label*="Open DEMO-"]',
            timeout_ms=60_000,
        )

    def open_issue(self, *, issue_key: str, issue_summary: str) -> None:
        self.open_jql_search()
        self._session.click(
            self._open_issue_selector(issue_key=issue_key, issue_summary=issue_summary),
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(
            self._issue_detail_selector(issue_key),
            timeout_ms=60_000,
        )

    def issue_detail_count(self, issue_key: str) -> int:
        return self._session.count(self._issue_detail_selector(issue_key))

    def tab_button_count(self, label: str) -> int:
        return self._session.count(
            f'flt-semantics[role="button"][aria-label="{self._escape(label)}"]',
        )

    def text_fragment_count(self, fragment: str) -> int:
        return self._session.count(
            f'flt-semantics[aria-label*="{self._escape(fragment)}"]',
        )

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    @staticmethod
    def _open_issue_selector(*, issue_key: str, issue_summary: str) -> str:
        escaped_key = LiveIssueDetailCollaborationPage._escape(issue_key)
        escaped_summary = LiveIssueDetailCollaborationPage._escape(issue_summary)
        return (
            'flt-semantics[role="button"]'
            f'[aria-label*="Open {escaped_key} {escaped_summary}"]'
        )

    @staticmethod
    def _issue_detail_selector(issue_key: str) -> str:
        return f'flt-semantics[aria-label*="Issue detail {LiveIssueDetailCollaborationPage._escape(issue_key)}"]'

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
