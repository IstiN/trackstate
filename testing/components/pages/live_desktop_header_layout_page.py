from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
)
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
    search: HeaderControlObservation
    create: HeaderControlObservation
    access: HeaderControlObservation
    theme: HeaderControlObservation
    profile: HeaderControlObservation
    active_element: HeaderActiveElementObservation


class LiveDesktopHeaderLayoutPage:
    _button_selector = 'flt-semantics[role="button"]'
    _create_issue_selector = 'flt-semantics[role="button"][aria-label="Create issue"]'
    _access_state_selector = (
        'flt-semantics[role="button"][aria-label="Attachments limited"]'
    )
    _search_input_selector = 'input[aria-label="Search issues"]'
    def __init__(self, tracker_page: TrackStateTrackerPage, *, user_login: str) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._user_login = user_login
        self._collaboration_page = LiveIssueDetailCollaborationPage(tracker_page)

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> None:
        self._collaboration_page.ensure_connected(
            token=token,
            repository=repository,
            user_login=user_login,
        )

    def dismiss_connection_banner(self) -> None:
        self._collaboration_page.dismiss_connection_banner()

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
            ({ userLogin, createLabel, accessLabel, searchLabel }) => {
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
              const visibleElements = (selector) => Array.from(document.querySelectorAll(selector))
                .filter((candidate) => isVisible(candidate));
              const buttonLabel = (element) =>
                normalize(element.getAttribute('aria-label') || element.innerText || '');
              const rectPayload = (element, label) => {
                const rect = element.getBoundingClientRect();
                return {
                  label,
                  left: rect.left,
                  top: rect.top,
                  width: rect.width,
                  height: rect.height,
                  centerY: rect.top + (rect.height / 2),
                };
              };
              const findButton = (label) => visibleElements('flt-semantics[role="button"]')
                .find((candidate) => buttonLabel(candidate) === label);
              const findThemeButton = () => visibleElements('flt-semantics[role="button"]')
                .find((candidate) => ['Dark theme', 'Light theme'].includes(buttonLabel(candidate)));
              const findSearchInput = () => visibleElements(`input[aria-label="${searchLabel}"]`)[0] ?? null;
              const findSync = () => visibleElements('flt-semantics')
                .find((candidate) => {
                  const text = normalize(candidate.innerText || '');
                  const rect = candidate.getBoundingClientRect();
                  return rect.top < 120
                    && text.includes('Synced with Git')
                    && text.length < 80;
                });
              const findProfile = () => visibleElements('flt-semantics')
                .find((candidate) => {
                  const text = normalize(candidate.innerText || '');
                  const rect = candidate.getBoundingClientRect();
                  return rect.top < 120 && text === userLogin;
                });
              const bodyText = document.body?.innerText ?? '';
              const create = findButton(createLabel);
              const access = findButton(accessLabel);
              const theme = findThemeButton();
              const search = findSearchInput();
              const sync = findSync();
              const profile = findProfile();
              if (!create || !access || !theme || !search || !sync || !profile) {
                return null;
              }
              const active = document.activeElement;
              return {
                viewportWidth: window.innerWidth,
                viewportHeight: window.innerHeight,
                bodyText,
                themeLabel: buttonLabel(theme),
                sync: rectPayload(sync, normalize(sync.innerText || '')),
                search: rectPayload(search, searchLabel),
                create: rectPayload(create, createLabel),
                access: rectPayload(access, accessLabel),
                theme: rectPayload(theme, buttonLabel(theme)),
                profile: rectPayload(profile, userLogin),
                activeElement: {
                  tagName: active?.tagName ?? '',
                  accessibleName: active?.getAttribute('aria-label') ?? null,
                  text: normalize(active?.innerText || ''),
                },
              };
            }
            """,
            arg={
                "userLogin": self._user_login,
                "createLabel": "Create issue",
                "accessLabel": "Attachments limited",
                "searchLabel": "Search issues",
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
            search=self._control_from_payload(payload["search"]),
            create=self._control_from_payload(payload["create"]),
            access=self._control_from_payload(payload["access"]),
            theme=self._control_from_payload(payload["theme"]),
            profile=self._control_from_payload(payload["profile"]),
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

    def focus_search_field(self, *, timeout_ms: int = 30_000) -> None:
        self._session.focus(self._search_input_selector, timeout_ms=timeout_ms)
        active = self._session.active_element()
        if active.accessible_name != "Search issues":
            raise AssertionError(
                "Focusing the visible desktop search field did not leave keyboard focus "
                "in the Search issues input.\n"
                f"Observed active element: {active}",
            )

    def toggle_theme(self, *, timeout_ms: int = 30_000) -> str:
        return self._collaboration_page.toggle_theme(timeout_ms=timeout_ms)

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
