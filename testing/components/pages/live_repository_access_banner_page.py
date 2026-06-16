from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_multi_view_refresh_page import LiveMultiViewRefreshPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class RepositoryAccessBannerExpectation:
    mode_label: str
    title: str
    message: str
    action_label: str


@dataclass(frozen=True)
class RepositoryAccessBannerObservation:
    location: str
    body_text: str
    topbar_label_visible: bool
    banner_text: str | None
    action_button_count: int
    navigation_error: str | None = None


@dataclass(frozen=True)
class ConnectDialogObservation:
    body_text: str
    token_field_count: int
    connect_token_button_count: int


@dataclass(frozen=True)
class ConnectResultObservation:
    body_text: str
    dialog_text: str


class LiveRepositoryAccessBannerPage:
    _button_selector = 'flt-semantics[role="button"]'
    _token_input_selector = 'input[aria-label="Fine-grained token"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._multi_view_page = LiveMultiViewRefreshPage(tracker_page)

    def open(self):
        return self._tracker_page.open()

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def observe_banner_across_issue_flows(
        self,
        *,
        expectation: RepositoryAccessBannerExpectation,
        issue_key: str,
        issue_summary: str,
    ) -> list[RepositoryAccessBannerObservation]:
        observations = [
            self._observe_section("Dashboard", expectation=expectation),
            self._observe_section("Board", expectation=expectation),
            self._observe_section("JQL Search", expectation=expectation),
            self._observe_section("Hierarchy", expectation=expectation),
        ]
        observations.append(
            self._observe_issue_detail(
                expectation=expectation,
                issue_key=issue_key,
                issue_summary=issue_summary,
            ),
        )
        return observations

    def open_connect_dialog_from_banner(
        self,
        *,
        title: str,
        action_label: str,
    ) -> ConnectDialogObservation:
        self._click_banner_action(title=title, action_label=action_label)
        self._session.wait_for_selector(self._token_input_selector, timeout_ms=30_000)
        return ConnectDialogObservation(
            body_text=self.current_body_text(),
            token_field_count=self._session.count(self._token_input_selector),
            connect_token_button_count=self._session.count(
                self._button_selector,
                has_text="Connect token",
            ),
        )

    def connect_with_read_only_token(
        self,
        *,
        token: str,
        read_only_title: str,
    ) -> ConnectResultObservation:
        dialog_text = self.current_body_text()
        self._session.fill(self._token_input_selector, token, timeout_ms=30_000)
        self._session.press(self._token_input_selector, "Tab", timeout_ms=30_000)
        self._session.click(
            self._button_selector,
            has_text="Connect token",
            timeout_ms=30_000,
        )
        wait_match = self._session.wait_for_any_text(
            [read_only_title, "GitHub connection failed:"],
            timeout_ms=120_000,
        )
        if wait_match.matched_text != read_only_title:
            raise AssertionError(
                "Submitting the PAT did not reach the read-only hosted session state.\n"
                f"Observed body text:\n{wait_match.body_text}",
            )
        return ConnectResultObservation(
            body_text=wait_match.body_text,
            dialog_text=dialog_text,
        )

    def click_recovery_action(
        self,
        *,
        title: str,
        action_label: str,
    ) -> str:
        self._click_banner_action(title=title, action_label=action_label)
        wait_match = self._session.wait_for_any_text(
            ["Project Settings", "Manage GitHub access", "Repository access"],
            timeout_ms=60_000,
        )
        return wait_match.body_text

    def _observe_section(
        self,
        section: str,
        *,
        expectation: RepositoryAccessBannerExpectation,
    ) -> RepositoryAccessBannerObservation:
        try:
            self._multi_view_page.navigate_to_section(section)
            return self._observe_current_location(
                location=section,
                expectation=expectation,
            )
        except Exception as error:
            return RepositoryAccessBannerObservation(
                location=section,
                body_text=self.current_body_text(),
                topbar_label_visible=False,
                banner_text=None,
                action_button_count=0,
                navigation_error=str(error),
            )

    def _observe_issue_detail(
        self,
        *,
        expectation: RepositoryAccessBannerExpectation,
        issue_key: str,
        issue_summary: str,
    ) -> RepositoryAccessBannerObservation:
        try:
            self._multi_view_page.navigate_to_section("Hierarchy")
            self._multi_view_page.open_issue_from_current_section(
                issue_key=issue_key,
                issue_summary=issue_summary,
            )
            return self._observe_current_location(
                location=f"issue detail for {issue_key}",
                expectation=expectation,
            )
        except Exception as error:
            return RepositoryAccessBannerObservation(
                location=f"issue detail for {issue_key}",
                body_text=self.current_body_text(),
                topbar_label_visible=False,
                banner_text=None,
                action_button_count=0,
                navigation_error=str(error),
            )

    def _observe_current_location(
        self,
        *,
        location: str,
        expectation: RepositoryAccessBannerExpectation,
    ) -> RepositoryAccessBannerObservation:
        body_text = self.current_body_text()
        payload = self._session.evaluate(
            self._banner_lookup_script(),
            arg={
                "title": expectation.title,
                "message": expectation.message,
                "actionLabel": expectation.action_label,
            },
        )
        banner_text = None
        action_button_count = 0
        if isinstance(payload, dict):
            banner_text = str(payload.get("text", "")).strip() or None
            action_button_count = int(payload.get("actionButtonCount", 0))
        return RepositoryAccessBannerObservation(
            location=location,
            body_text=body_text,
            topbar_label_visible=expectation.mode_label in body_text,
            banner_text=banner_text,
            action_button_count=action_button_count,
        )

    def _click_banner_action(self, *, title: str, action_label: str) -> None:
        payload = self._session.evaluate(
            self._banner_action_script(),
            arg={"title": title, "actionLabel": action_label},
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                f'Could not locate the visible "{action_label}" action inside the '
                f'"{title}" repository-access banner.\n'
                f"Observed body text:\n{self.current_body_text()}",
            )
        x = payload.get("x")
        y = payload.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise AssertionError(
                f'The visible "{action_label}" action inside the "{title}" '
                "repository-access banner did not expose a clickable region.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        self._session.mouse_click(float(x), float(y))

    @staticmethod
    def _banner_lookup_script() -> str:
        return """
        ({ title, message, actionLabel }) => {
          const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
          const isVisible = (element) => {
            if (!element) {
              return false;
            }
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            return rect.width > 0
              && rect.height > 0
              && style.visibility !== 'hidden'
              && style.display !== 'none';
          };
          const containers = Array.from(document.querySelectorAll('flt-semantics'))
            .filter((element) => isVisible(element))
            .map((element) => {
              const rect = element.getBoundingClientRect();
              return {
                element,
                text: normalize(element.innerText || element.textContent || ''),
                top: rect.top,
                area: rect.width * rect.height,
              };
            })
            .filter((candidate) =>
              candidate.text.includes(title)
              && candidate.text.includes(message)
              && candidate.text.includes(actionLabel),
            )
            .sort((left, right) => {
              if (left.top !== right.top) {
                return left.top - right.top;
              }
              return left.area - right.area;
            });
          const container = containers[0];
          if (!container) {
            return null;
          }
          const actionButtonCount = Array.from(
            container.element.querySelectorAll('flt-semantics[role="button"]'),
          )
            .filter((element) => isVisible(element))
            .map((element) => normalize(element.innerText || element.textContent || ''))
            .filter((text) => text.includes(actionLabel))
            .length;
          return {
            text: container.text,
            actionButtonCount,
          };
        }
        """

    @staticmethod
    def _banner_action_script() -> str:
        return """
        ({ title, actionLabel }) => {
          const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
          const isVisible = (element) => {
            if (!element) {
              return false;
            }
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            return rect.width > 0
              && rect.height > 0
              && style.visibility !== 'hidden'
              && style.display !== 'none';
          };
          const containers = Array.from(document.querySelectorAll('flt-semantics'))
            .filter((element) => isVisible(element))
            .map((element) => {
              const rect = element.getBoundingClientRect();
              return {
                element,
                text: normalize(element.innerText || element.textContent || ''),
                top: rect.top,
                area: rect.width * rect.height,
              };
            })
            .filter((candidate) =>
              candidate.text.includes(title) && candidate.text.includes(actionLabel),
            )
            .sort((left, right) => {
              if (left.top !== right.top) {
                return left.top - right.top;
              }
              return left.area - right.area;
            });
          const container = containers[0];
          if (!container) {
            return null;
          }
          const action = Array.from(
            container.element.querySelectorAll('flt-semantics[role="button"]'),
          )
            .filter((element) => isVisible(element))
            .map((element) => {
              const rect = element.getBoundingClientRect();
              return {
                text: normalize(element.innerText || element.textContent || ''),
                x: rect.left + (rect.width / 2),
                y: rect.top + (rect.height / 2),
              };
            })
            .find((candidate) => candidate.text.includes(actionLabel));
          return action ?? null;
        }
        """
