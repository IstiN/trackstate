from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class StartupRecoveryShellObservation:
    body_text: str
    selected_button_labels: tuple[str, ...]
    visible_navigation_labels: tuple[str, ...]
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

    def wait_for_shell_routed_to_settings(
        self,
        *,
        timeout_ms: int = 120_000,
    ) -> StartupRecoveryShellObservation:
        self._session.wait_for_function(
            """
            ({ requiredNavigationLabels, settingsHeading, topbarTitle }) => {
              const bodyText = document.body?.innerText ?? '';
              const selectedLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"][aria-current="true"]'),
              ).map((candidate) => (candidate.innerText ?? '').trim());
              return requiredNavigationLabels.every((label) => bodyText.includes(label))
                && bodyText.includes(settingsHeading)
                && bodyText.includes(topbarTitle)
                && bodyText.includes('Retry')
                && selectedLabels.includes('Settings');
            }
            """,
            arg={
                "requiredNavigationLabels": list(self._required_navigation_labels),
                "settingsHeading": self._settings_heading,
                "topbarTitle": self._topbar_title,
            },
            timeout_ms=timeout_ms,
        )
        return self.observe_shell()

    def observe_shell(self) -> StartupRecoveryShellObservation:
        payload = self._session.evaluate(
            """
            (requiredNavigationLabels) => {
              const bodyText = document.body?.innerText ?? '';
              const selectedButtonLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"][aria-current="true"]'),
              )
                .map((candidate) => (candidate.innerText ?? '').trim())
                .filter((label) => label.length > 0);
              return {
                bodyText,
                selectedButtonLabels,
                visibleNavigationLabels: requiredNavigationLabels.filter(
                  (label) => bodyText.includes(label),
                ),
                retryVisible: bodyText.includes('Retry'),
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
            selected_button_labels=tuple(str(item) for item in payload["selectedButtonLabels"]),
            visible_navigation_labels=tuple(
                str(item) for item in payload["visibleNavigationLabels"]
            ),
            retry_visible=bool(payload["retryVisible"]),
            connect_github_visible=bool(payload["connectGitHubVisible"]),
            topbar_title_visible=bool(payload["topbarTitleVisible"]),
            settings_heading_visible=bool(payload["settingsHeadingVisible"]),
        )

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)
