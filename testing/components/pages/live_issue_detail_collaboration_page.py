from __future__ import annotations

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


class LiveIssueDetailCollaborationPage:
    _button_selector = 'flt-semantics[role="button"]'
    _connect_button_selector = 'flt-semantics[aria-label="Connect GitHub"]'
    _connected_button_selector = 'flt-semantics[aria-label="Connected"]'
    _token_input_selector = 'input[aria-label="Fine-grained token"]'
    _selected_button_selector = 'flt-semantics[role="button"][aria-current="true"]'

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
        connected_banner = TrackStateTrackerPage.CONNECTED_BANNER_TEMPLATE.format(
            user_login=user_login,
            repository=repository,
        )
        if self._is_connected(connected_banner):
            return
        if self._session.count(self._connect_button_selector) == 0:
            raise AssertionError(
                "Step 1 failed: the hosted session did not expose either the connected "
                "state or the Connect GitHub action needed to prove the authentication "
                "precondition for TS-311.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )

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
                connected_banner,
                "GitHub connection failed:",
            ],
            timeout_ms=120_000,
        )
        if wait_match.matched_text != connected_banner:
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
        labeled_tab_count = self._session.count(self._tab_selector(label))
        if labeled_tab_count > 0:
            return labeled_tab_count
        return self._session.count(self._button_selector, has_text=label)

    def selected_tab_count(self, label: str) -> int:
        return self._session.count(self._selected_button_selector, has_text=label)

    def open_collaboration_tab(self, label: str) -> None:
        selector = self._tab_selector(label)
        if self._session.count(selector) > 0:
            self._session.wait_for_selector(selector, timeout_ms=30_000)
            self._session.click(selector, timeout_ms=30_000)
        else:
            self._session.wait_for_selector(
                self._button_selector,
                has_text=label,
                timeout_ms=30_000,
            )
            self._session.click(self._button_selector, has_text=label, timeout_ms=30_000)

    def wait_for_selected_tab(self, label: str, *, timeout_ms: int = 30_000) -> None:
        self._session.wait_for_selector(
            self._selected_button_selector,
            has_text=label,
            timeout_ms=timeout_ms,
        )

    def wait_for_text(self, text: str, *, timeout_ms: int = 60_000) -> str:
        return self._session.wait_for_text(text, timeout_ms=timeout_ms)

    def text_fragment_count(self, fragment: str) -> int:
        labeled_fragment_count = self._session.count(
            f'flt-semantics[aria-label*="{self._escape(fragment)}"]',
        )
        if labeled_fragment_count > 0:
            return labeled_fragment_count
        return 1 if fragment in self.current_body_text() else 0

    def button_label_fragment_count(self, fragment: str) -> int:
        labeled_button_count = self._session.count(
            f'flt-semantics[role="button"][aria-label*="{self._escape(fragment)}"]',
        )
        if labeled_button_count > 0:
            return labeled_button_count
        return self._session.count(self._button_selector, has_text=fragment)

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def _is_connected(self, connected_banner: str) -> bool:
        return (
            self._session.count(self._connected_button_selector) > 0
            or connected_banner in self.current_body_text()
        )

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
    def _tab_selector(label: str) -> str:
        return (
            'flt-semantics[role="button"]'
            f'[aria-label="{LiveIssueDetailCollaborationPage._escape(label)}"]'
        )

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
