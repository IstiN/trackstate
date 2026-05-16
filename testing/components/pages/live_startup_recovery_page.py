from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class StartupRecoveryShellObservation:
    body_text: str
    location_href: str
    location_hash: str
    location_pathname: str
    selected_button_labels: tuple[str, ...]
    visible_navigation_labels: tuple[str, ...]
    visible_button_labels: tuple[str, ...]
    retry_visible: bool
    connect_github_visible: bool
    topbar_title_visible: bool
    settings_heading_visible: bool

    @property
    def settings_selected(self) -> bool:
        return "Settings" in self.selected_button_labels


class LiveStartupRecoveryPage:
    _required_navigation_labels = (
        "Dashboard",
        "Board",
        "JQL Search",
        "Hierarchy",
        "Settings",
    )
    _settings_heading = "Project settings administration"
    _topbar_title = "Project Settings"
    _button_selector = 'flt-semantics[role="button"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def open(self) -> None:
        self._tracker_page.open_entrypoint()

    def open_route(self, route: str) -> str:
        return self._tracker_page.open_route(route)

    def wait_for_shell_routed_to_settings(
        self,
        *,
        timeout_ms: int = 120_000,
        require_retry_action: bool = True,
        required_body_fragments: tuple[str, ...] = (),
    ) -> StartupRecoveryShellObservation:
        self._session.wait_for_function(
            r"""
            ({
              requiredNavigationLabels,
              settingsHeading,
              topbarTitle,
              requireRetryAction,
              requiredBodyFragments,
            }) => {
              const normalize = (value) => (value ?? '').replace(/\s+/g, ' ').trim();
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
              const bodyText = document.body?.innerText ?? '';
              const selectedLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"][aria-current="true"]'),
              )
                .map((candidate) => normalize(candidate.innerText))
                .filter((label) => label.length > 0);
              const visibleButtonLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter(isVisible)
                .map((candidate) => normalize(candidate.innerText))
                .filter((label) => label.length > 0);
              return requiredNavigationLabels.every((label) => bodyText.includes(label))
                && bodyText.includes(settingsHeading)
                && bodyText.includes(topbarTitle)
                && (!requireRetryAction || visibleButtonLabels.includes('Retry'))
                && requiredBodyFragments.every((fragment) => bodyText.includes(fragment))
                && selectedLabels.includes('Settings');
            }
            """,
            arg={
                "requiredNavigationLabels": list(self._required_navigation_labels),
                "settingsHeading": self._settings_heading,
                "topbarTitle": self._topbar_title,
                "requireRetryAction": require_retry_action,
                "requiredBodyFragments": list(required_body_fragments),
            },
            timeout_ms=timeout_ms,
        )
        return self.observe_shell()

    def observe_shell(self) -> StartupRecoveryShellObservation:
        payload = self._session.evaluate(
            r"""
            (requiredNavigationLabels) => {
              const normalize = (value) => (value ?? '').replace(/\s+/g, ' ').trim();
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
              const bodyText = document.body?.innerText ?? '';
              const selectedButtonLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"][aria-current="true"]'),
              )
                .map((candidate) => normalize(candidate.innerText))
                .filter((label) => label.length > 0);
              const visibleButtonLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter(isVisible)
                .map((candidate) => normalize(candidate.innerText))
                .filter((label) => label.length > 0);
              return {
                 bodyText,
                 locationHref: window.location.href,
                 locationHash: window.location.hash,
                 locationPathname: window.location.pathname,
                 selectedButtonLabels,
                 visibleNavigationLabels: requiredNavigationLabels.filter(
                   (label) => bodyText.includes(label),
                ),
                visibleButtonLabels,
                retryVisible: visibleButtonLabels.includes('Retry'),
                connectGitHubVisible: bodyText.includes('Connect GitHub'),
                topbarTitleVisible: bodyText.includes('Project Settings'),
                settingsHeadingVisible: bodyText.includes(
                  'Project settings administration',
                ),
              };
            }
            """,
            arg=list(self._required_navigation_labels),
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The startup recovery page did not expose a readable DOM snapshot.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return StartupRecoveryShellObservation(
            body_text=str(payload["bodyText"]),
            location_href=str(payload["locationHref"]),
            location_hash=str(payload["locationHash"]),
            location_pathname=str(payload["locationPathname"]),
            selected_button_labels=tuple(str(item) for item in payload["selectedButtonLabels"]),
            visible_navigation_labels=tuple(
                str(item) for item in payload["visibleNavigationLabels"]
            ),
            visible_button_labels=tuple(str(item) for item in payload["visibleButtonLabels"]),
            retry_visible=bool(payload["retryVisible"]),
            connect_github_visible=bool(payload["connectGitHubVisible"]),
            topbar_title_visible=bool(payload["topbarTitleVisible"]),
            settings_heading_visible=bool(payload["settingsHeadingVisible"]),
        )

    def click_retry(self, *, timeout_ms: int = 30_000) -> None:
        self._session.click(
            self._button_selector,
            has_text="Retry",
            timeout_ms=timeout_ms,
        )

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def tap_retry(self) -> None:
        self._session.click(self._button_selector, has_text="Retry", timeout_ms=30_000)

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)
