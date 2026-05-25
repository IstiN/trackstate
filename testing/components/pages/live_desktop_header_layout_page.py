from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_dashboard_page import LiveDashboardObservation, LiveDashboardPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class HeaderControlObservation:
    label: str
    left: float
    top: float
    width: float
    height: float
    center_y: float

    @property
    def right(self) -> float:
        return self.left + self.width


@dataclass(frozen=True)
class HeaderActiveElementObservation:
    tag_name: str
    accessible_name: str | None
    text: str


@dataclass(frozen=True)
class DesktopHeaderObservation:
    viewport_width: float
    viewport_height: float
    body_text: str
    theme_label: str
    sync: HeaderControlObservation
    create: HeaderControlObservation
    workspace: HeaderControlObservation
    search: HeaderControlObservation
    search_input: HeaderControlObservation
    theme: HeaderControlObservation
    active_element: HeaderActiveElementObservation


class LiveDesktopHeaderLayoutPage:
    _button_selector = 'flt-semantics[role="button"]'
    _dashboard_nav_selector = (
        'flt-semantics[flt-semantics-identifier="trackstate-desktop-nav-dashboard"]'
    )
    _create_issue_selector = (
        'flt-semantics[flt-semantics-identifier="trackstate-desktop-create-issue"]'
    )
    _search_input_selector = 'input[aria-label="Search issues"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._dashboard_page = LiveDashboardPage(tracker_page)

    def open_dashboard(self) -> LiveDashboardObservation:
        observation = self._dashboard_page.observe()
        if (
            observation.active_dashboard_visible
            and observation.open_issues_visible
            and observation.team_velocity_visible
        ):
            return observation
        self._session.click(self._dashboard_nav_selector, timeout_ms=30_000)
        self._session.wait_for_any_text(
            ["Open Issues", "Team Velocity"],
            timeout_ms=60_000,
        )
        return self._dashboard_page.observe()

    def set_viewport(self, *, width: int, height: int, timeout_ms: int = 15_000) -> None:
        self._session.set_viewport_size(width=width, height=height)
        try:
            self._session.wait_for_function(
                """
                ({ expectedWidth, expectedHeight }) =>
                  window.innerWidth === expectedWidth && window.innerHeight === expectedHeight
                """,
                arg={"expectedWidth": width, "expectedHeight": height},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f"Resizing the hosted browser to {width}x{height} did not settle to the "
                "requested viewport.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        self._session.mouse_move(1, 1)

    def observe_header(self, *, timeout_ms: int = 30_000) -> DesktopHeaderObservation:
        payload = self._session.wait_for_function(
            """
            ({ createLabel, searchLabels, syncLabelFragments }) => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && rect.y < 120
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const area = (element) => {
                const rect = element.getBoundingClientRect();
                return rect.width * rect.height;
              };
              const smallest = (elements) =>
                [...elements].sort((left, right) => area(left) - area(right))[0] ?? null;
              const labelFor = (element) =>
                normalize(
                  element?.getAttribute('aria-label')
                  || element?.innerText
                  || element?.textContent,
                );
              const describe = (element, labelOverride = null) => {
                const rect = element.getBoundingClientRect();
                return {
                  label: labelOverride ?? labelFor(element),
                  left: rect.left,
                  top: rect.top,
                  width: rect.width,
                  height: rect.height,
                  centerY: rect.top + (rect.height / 2),
                };
              };
              const searchInput = Array.from(document.querySelectorAll('input[aria-label]')).find(
                (element) => isVisible(element) && searchLabels.includes(labelFor(element)),
              ) ?? null;
              const searchWrapper = searchInput
                ? smallest(
                    Array.from(document.querySelectorAll('flt-semantics')).filter(
                      (element) => isVisible(element) && element.contains(searchInput),
                    ),
                  )
                : null;
              const create = smallest(
                Array.from(document.querySelectorAll('flt-semantics[role="button"]')).filter(
                  (element) =>
                    isVisible(element)
                    && (
                      element.getAttribute('flt-semantics-identifier') === 'trackstate-desktop-create-issue'
                      || labelFor(element) === createLabel
                    ),
                ),
              );
              const workspace = Array.from(
                document.querySelectorAll(
                  'button[aria-label], [data-trackstate-browser-focus-id="trackstate-desktop-workspace-switcher-trigger"]',
                ),
              ).find(
                (element) =>
                  isVisible(element)
                  && labelFor(element).startsWith('Workspace switcher:'),
              ) ?? null;
              const sync = smallest(
                Array.from(document.querySelectorAll('flt-semantics[role="button"]')).filter(
                  (element) =>
                    isVisible(element)
                    && syncLabelFragments.some((fragment) => labelFor(element).includes(fragment)),
                ),
              );
              const theme = smallest(
                Array.from(document.querySelectorAll('flt-semantics[role="button"]')).filter(
                  (element) => isVisible(element) && labelFor(element).toLowerCase().includes('theme'),
                ),
              );
              if (!sync || !create || !workspace || !searchWrapper || !searchInput || !theme) {
                return null;
              }
              const active = document.activeElement;
              return {
                viewportWidth: window.innerWidth,
                viewportHeight: window.innerHeight,
                bodyText: document.body?.innerText ?? '',
                themeLabel: labelFor(theme),
                sync: describe(sync),
                create: describe(create),
                workspace: describe(workspace),
                search: describe(searchWrapper, labelFor(searchInput)),
                searchInput: describe(searchInput),
                theme: describe(theme),
                activeElement: {
                  tagName: active?.tagName ?? '',
                  accessibleName: active?.getAttribute('aria-label') ?? null,
                  text: normalize(active?.innerText || active?.textContent),
                },
              };
            }
            """,
            arg={
                "createLabel": "Create issue",
                "searchLabels": ["Search issues", "Search", "JQL Search"],
                "syncLabelFragments": ["Sync error", "Synced with Git", "Syncing"],
            },
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The hosted desktop header did not expose the visible controls required "
                "for the layout audit.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return DesktopHeaderObservation(
            viewport_width=float(payload["viewportWidth"]),
            viewport_height=float(payload["viewportHeight"]),
            body_text=str(payload["bodyText"]),
            theme_label=str(payload["themeLabel"]),
            sync=self._control_from_payload(payload["sync"]),
            create=self._control_from_payload(payload["create"]),
            workspace=self._control_from_payload(payload["workspace"]),
            search=self._control_from_payload(payload["search"]),
            search_input=self._control_from_payload(payload["searchInput"]),
            theme=self._control_from_payload(payload["theme"]),
            active_element=HeaderActiveElementObservation(
                tag_name=str(payload["activeElement"]["tagName"]),
                accessible_name=(
                    str(payload["activeElement"]["accessibleName"])
                    if payload["activeElement"]["accessibleName"] is not None
                    else None
                ),
                text=str(payload["activeElement"]["text"]),
            ),
        )

    def hover_create_issue(self) -> None:
        rect = self._session.bounding_box(self._create_issue_selector, timeout_ms=30_000)
        self._session.mouse_move(rect.x + (rect.width / 2), rect.y + (rect.height / 2))

    def click_create_issue(self, *, timeout_ms: int = 30_000) -> None:
        self._session.click(self._create_issue_selector, timeout_ms=timeout_ms)
        self._session.wait_for_selector(self._create_issue_selector, timeout_ms=timeout_ms)

    def dismiss_create_issue_dialog(self, *, timeout_ms: int = 5_000) -> None:
        for label in ("Cancel", "Close"):
            if self._session.count(self._button_selector, has_text=label) == 0:
                continue
            self._session.click(self._button_selector, has_text=label, timeout_ms=timeout_ms)
            return

    def focus_search_field(self, *, timeout_ms: int = 30_000) -> None:
        self._session.focus(self._search_input_selector, timeout_ms=timeout_ms)
        active = self._session.active_element()
        if active.accessible_name not in {"Search issues", "Search", "JQL Search"}:
            raise AssertionError(
                "Focusing the visible desktop search field did not leave keyboard focus "
                "in the search input.\n"
                f"Observed active element: {active}",
            )

    def toggle_theme(self, *, timeout_ms: int = 30_000) -> str:
        current = self.observe_header(timeout_ms=timeout_ms).theme_label
        target = "Light theme" if current == "Dark theme" else "Dark theme"
        self._session.click(
            self._button_selector,
            has_text=current,
            timeout_ms=timeout_ms,
        )
        self._session.wait_for_function(
            """
            expectedLabel => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && rect.y < 120
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              return Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                .some(
                  (candidate) =>
                    isVisible(candidate)
                    && normalize(candidate.getAttribute('aria-label') || candidate.innerText) === expectedLabel,
                )
                ? expectedLabel
                : null;
            }
            """,
            arg=target,
            timeout_ms=timeout_ms,
        )
        return target

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    @staticmethod
    def _control_from_payload(payload: object) -> HeaderControlObservation:
        if not isinstance(payload, dict):
            raise AssertionError(f"Unexpected header-control payload: {payload!r}")
        return HeaderControlObservation(
            label=str(payload["label"]),
            left=float(payload["left"]),
            top=float(payload["top"]),
            width=float(payload["width"]),
            height=float(payload["height"]),
            center_y=float(payload["centerY"]),
        )
