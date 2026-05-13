from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_live_app_page import TrackStateLiveAppPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class HeaderControlObservation:
    label: str
    role: str | None
    x: float
    y: float
    width: float
    height: float
    center_y: float


@dataclass(frozen=True)
class DesktopHeaderObservation:
    body_text: str
    sync_pill: HeaderControlObservation
    search_field: HeaderControlObservation
    search_input: HeaderControlObservation
    create_issue: HeaderControlObservation
    repository_access: HeaderControlObservation
    theme_toggle: HeaderControlObservation


class LiveTrackerHeaderPage:
    _button_selector = 'flt-semantics[role="button"]'
    _close_selector = 'flt-semantics[aria-label="Close"]'
    _token_input_selector = 'input[aria-label="Fine-grained token"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._live_page = TrackStateLiveAppPage(self._session, tracker_page.app_url)

    def ensure_attachments_limited_state(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
        timeout_ms: int = 120_000,
    ) -> str:
        connected_banner = TrackStateTrackerPage.CONNECTED_BANNER_TEMPLATE.format(
            user_login=user_login,
            repository=repository,
        )
        current_body = self.body_text()
        if connected_banner in current_body and "Attachments limited" in current_body:
            return current_body

        if self._session.count('flt-semantics[aria-label="Connect GitHub"]') == 0:
            raise AssertionError(
                "The desktop header did not expose the Connect GitHub action needed "
                "to trigger the hosted `Attachments limited` state.\n"
                f"Observed body text:\n{current_body}",
            )

        self._live_page.open_connect_dialog()
        self._session.wait_for_selector(self._token_input_selector, timeout_ms=30_000)
        self._session.fill(self._token_input_selector, token, timeout_ms=30_000)
        self._session.press(self._token_input_selector, "Tab", timeout_ms=30_000)
        self._live_page.submit_connect_token()

        try:
            wait_match = self._session.wait_for_any_text(
                [connected_banner, "Attachments limited", "GitHub connection failed:"],
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Submitting the fine-grained token never reached the hosted "
                "`Attachments limited` state.\n"
                f"Observed body text:\n{self.body_text()}",
            ) from error

        if wait_match.matched_text == "GitHub connection failed:":
            raise AssertionError(
                "Submitting the fine-grained token did not connect the hosted app.\n"
                f"Observed body text:\n{wait_match.body_text}",
            )

        body_text = self.body_text()
        if "Attachments limited" not in body_text:
            raise AssertionError(
                "The hosted session connected, but the desktop header never exposed "
                "the `Attachments limited` repository access state.\n"
                f"Observed body text:\n{body_text}",
            )
        return body_text

    def dismiss_connection_banner(self) -> None:
        if self._session.count(self._close_selector) == 0:
            return
        self._session.click(self._close_selector, timeout_ms=30_000)

    def observe_desktop_header(self, *, timeout_ms: int = 60_000) -> DesktopHeaderObservation:
        payload = self._session.wait_for_function(
            """
            ({ syncLabel, searchLabel, createLabel, repositoryAccessLabel, themeLabels }) => {
              const visible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return (
                  rect.width > 0
                  && rect.height > 0
                  && style.display !== 'none'
                  && style.visibility !== 'hidden'
                );
              };
              const topBarCandidates = Array.from(
                document.querySelectorAll('flt-semantics, input'),
              )
                .filter(visible)
                .filter((element) => {
                  const rect = element.getBoundingClientRect();
                  return rect.y < 90 && rect.x > 250;
                });
              const matchesLabel = (element, label) => {
                const text = (element.innerText || element.textContent || '').trim();
                const ariaLabel = element.getAttribute('aria-label') || '';
                return text === label || ariaLabel === label;
              };
              const toPayload = (element, label) => {
                const rect = element.getBoundingClientRect();
                return {
                  label,
                  role: element.getAttribute('role'),
                  x: rect.x,
                  y: rect.y,
                  width: rect.width,
                  height: rect.height,
                  centerY: rect.y + (rect.height / 2),
                };
              };

              const syncPill = topBarCandidates.find((element) => {
                const text = (element.innerText || element.textContent || '').trim();
                return text.includes(syncLabel);
              });
              const searchField = topBarCandidates.find(
                (element) => element.tagName === 'INPUT' && element.getAttribute('aria-label') === searchLabel,
              );
              const searchInput = topBarCandidates.find((element) => {
                if (element.tagName !== 'INPUT' || element.getAttribute('aria-label')) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                return rect.height >= 28 && rect.height <= 36 && rect.width >= 150;
              });
              const createIssue = topBarCandidates.find((element) => matchesLabel(element, createLabel));
              const repositoryAccess = topBarCandidates.find((element) => {
                return matchesLabel(element, repositoryAccessLabel);
              });
              const themeToggle = topBarCandidates.find((element) => {
                return themeLabels.some((label) => matchesLabel(element, label));
              });
              const bodyText = document.body?.innerText ?? '';

              if (
                !syncPill
                || !searchField
                || !searchInput
                || !createIssue
                || !repositoryAccess
                || !themeToggle
              ) {
                return null;
              }

              return {
                bodyText,
                syncPill: toPayload(syncPill, syncLabel),
                searchField: toPayload(searchField, searchLabel),
                searchInput: toPayload(searchInput, searchLabel),
                createIssue: toPayload(createIssue, createLabel),
                repositoryAccess: toPayload(repositoryAccess, repositoryAccessLabel),
                themeToggle: toPayload(
                  themeToggle,
                  themeLabels.find((label) => matchesLabel(themeToggle, label)) ?? '',
                ),
              };
            }
            """,
            arg={
                "syncLabel": "Synced with Git",
                "searchLabel": "Search issues",
                "createLabel": "Create issue",
                "repositoryAccessLabel": "Attachments limited",
                "themeLabels": ["Dark theme", "Light theme"],
            },
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The live desktop top bar did not expose the expected header controls.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return DesktopHeaderObservation(
            body_text=str(payload.get("bodyText", "")),
            sync_pill=self._control_observation(payload.get("syncPill")),
            search_field=self._control_observation(payload.get("searchField")),
            search_input=self._control_observation(payload.get("searchInput")),
            create_issue=self._control_observation(payload.get("createIssue")),
            repository_access=self._control_observation(payload.get("repositoryAccess")),
            theme_toggle=self._control_observation(payload.get("themeToggle")),
        )

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def body_text(self) -> str:
        return self._tracker_page.body_text()

    @staticmethod
    def _control_observation(payload: object) -> HeaderControlObservation:
        if not isinstance(payload, dict):
            raise AssertionError(
                "The live desktop top bar did not expose a readable control payload.",
            )
        return HeaderControlObservation(
            label=str(payload.get("label", "")).strip(),
            role=str(payload.get("role")) if payload.get("role") is not None else None,
            x=float(payload.get("x", 0)),
            y=float(payload.get("y", 0)),
            width=float(payload.get("width", 0)),
            height=float(payload.get("height", 0)),
            center_y=float(payload.get("centerY", 0)),
        )
