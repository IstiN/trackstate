from __future__ import annotations

from dataclasses import dataclass
import re

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class LiveDashboardObservation:
    body_text: str
    active_dashboard_visible: bool
    active_epics_visible: bool
    recent_activity_visible: bool
    open_issues_visible: bool
    team_velocity_visible: bool
    visible_issue_labels: tuple[str, ...]


class LiveDashboardPage:
    _button_selector = 'flt-semantics[role="button"]'
    _active_button_selector = 'flt-semantics[role="button"][aria-current="true"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def open(self) -> LiveDashboardObservation:
        if not self._is_active():
            self._session.click(
                self._button_selector,
                has_text="Dashboard",
                timeout_ms=30_000,
            )
        try:
            self._session.wait_for_selector(
                self._active_button_selector,
                has_text="Dashboard",
                timeout_ms=30_000,
            )
            self._session.wait_for_any_text(
                ["Open Issues", "Team Velocity"],
                timeout_ms=60_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 5 failed: the hosted app did not expose the Dashboard surface "
                "after startup.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        return self.observe()

    def observe(self) -> LiveDashboardObservation:
        payload = self._session.evaluate(
            """
            () => {
              const labels = Array.from(document.querySelectorAll('flt-semantics[aria-label]'))
                .map((element) => (element.getAttribute('aria-label') ?? '').trim())
                .filter((label) => label.length > 0);
              const issueLabels = Array.from(
                new Set(
                  labels.filter((label) => /^[A-Z][A-Z0-9]+-\\d+ · .+/.test(label)),
                ),
              );
              const bodyText = document.body?.innerText ?? '';
              return {
                bodyText,
                activeDashboardVisible: Array.from(
                  document.querySelectorAll('flt-semantics[role="button"][aria-current="true"]'),
                ).some((element) => (element.innerText ?? '').trim() === 'Dashboard'),
                activeEpicsVisible: labels.includes('Active Epics'),
                recentActivityVisible: labels.includes('Recent Activity'),
                openIssuesVisible: bodyText.includes('Open Issues'),
                teamVelocityVisible: bodyText.includes('Team Velocity'),
                visibleIssueLabels: issueLabels,
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The Dashboard page did not expose a readable DOM snapshot.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        body_text = str(payload["bodyText"])
        aria_issue_labels = [
            str(item) for item in payload["visibleIssueLabels"] if str(item).strip()
        ]
        body_issue_labels = [
            match.group(1).strip()
            for match in re.finditer(
                r"([A-Z][A-Z0-9]+-\d+ · .*?)(?= \d+%|\n|$)",
                body_text,
            )
        ]
        visible_issue_labels = tuple(dict.fromkeys([*aria_issue_labels, *body_issue_labels]))
        return LiveDashboardObservation(
            body_text=body_text,
            active_dashboard_visible=bool(payload["activeDashboardVisible"]),
            active_epics_visible=bool(payload["activeEpicsVisible"]),
            recent_activity_visible=bool(payload["recentActivityVisible"]),
            open_issues_visible=bool(payload["openIssuesVisible"]),
            team_velocity_visible=bool(payload["teamVelocityVisible"]),
            visible_issue_labels=visible_issue_labels,
        )

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def _is_active(self) -> bool:
        return self._session.count(
            self._active_button_selector,
            has_text="Dashboard",
        ) > 0
