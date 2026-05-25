from __future__ import annotations

from dataclasses import dataclass

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
    visible_text: str
    accessible_label: str | None
    client_width: float
    scroll_width: float

    @property
    def text_is_clipped(self) -> bool:
        return self.scroll_width > (self.client_width + 1.0)


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
    _button_selector = 'button, flt-semantics[role="button"]'
    _close_selector = 'button[aria-label="Close"], flt-semantics[aria-label="Close"]'
    _connect_selector = (
        'button[aria-label="Connect GitHub"], flt-semantics[aria-label="Connect GitHub"]'
    )
    _token_input_selector = 'input[aria-label="Fine-grained token"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def ensure_attachments_limited_state(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
        timeout_ms: int = 120_000,
    ) -> str:
        connected_marker = f"Connected as {user_login} to {repository}"
        current_body = self.body_text()
        if connected_marker in current_body and "Attachments limited" in current_body:
            return current_body

        try:
            early_wait = self._session.wait_for_any_text(
                [connected_marker, "Attachments limited", "GitHub connection failed:"],
                timeout_ms=20_000,
            )
        except WebAppTimeoutError:
            early_wait = None
        if early_wait is not None:
            current_body = self.body_text()
            if connected_marker in current_body and "Attachments limited" in current_body:
                return current_body

        if (
            self._session.count(self._token_input_selector) == 0
            and self._session.count(self._connect_selector) > 0
        ):
            self._session.click(self._connect_selector, timeout_ms=30_000)
            self._session.wait_for_selector(self._token_input_selector, timeout_ms=30_000)

        if self._session.count(self._token_input_selector) > 0:
            self._session.fill(self._token_input_selector, token, timeout_ms=30_000)
            self._session.press(self._token_input_selector, "Tab", timeout_ms=30_000)
            self._session.click(
                self._button_selector,
                has_text="Connect token",
                timeout_ms=30_000,
            )

        try:
            wait_match = self._session.wait_for_any_text(
                [connected_marker, "Attachments limited", "GitHub connection failed:"],
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
        if connected_marker not in body_text:
            raise AssertionError(
                "The hosted session did not expose the expected connected GitHub banner.\n"
                f"Observed body text:\n{body_text}",
            )
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
            r"""
            ({ searchLabel, createLabel, workspacePrefix, workspaceState, themeLabels }) => {
              const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
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
              const topBarElements = Array.from(document.querySelectorAll('button, flt-semantics, input'))
                .filter(visible)
                .filter((element) => {
                  const rect = element.getBoundingClientRect();
                  return rect.top < 90 && rect.left > 250;
                });
              const toPayload = (element, fallbackLabel) => {
                const rect = element.getBoundingClientRect();
                const accessibleLabel = normalize(element.getAttribute('aria-label') || '');
                const visibleText = normalize(element.innerText || element.textContent || '');
                return {
                  label: fallbackLabel || accessibleLabel || visibleText,
                  role: element.getAttribute('role'),
                  x: rect.x,
                  y: rect.y,
                  width: rect.width,
                  height: rect.height,
                  centerY: rect.y + (rect.height / 2),
                  visibleText,
                  accessibleLabel: accessibleLabel || null,
                  clientWidth: element.clientWidth || rect.width,
                  scrollWidth: element.scrollWidth || rect.width,
                };
              };
              const buttonText = (element) => normalize(element.innerText || element.textContent || '');
              const ariaLabel = (element) => normalize(element.getAttribute('aria-label') || '');
              const createIssue = topBarElements.find((element) => {
                return (
                  buttonText(element) === createLabel
                  && (element.getAttribute('role') === 'button' || element.tagName === 'BUTTON')
                );
              });
              const repositoryAccess = topBarElements.find((element) => {
                const label = ariaLabel(element);
                return label.startsWith(workspacePrefix) && label.includes(workspaceState);
              });
              const searchInput = topBarElements.find((element) => {
                return element.tagName === 'INPUT' && ariaLabel(element) === searchLabel;
              });
              const searchField = searchInput
                ? topBarElements.find((element) => {
                    if (element === searchInput || element.tagName === 'INPUT') {
                      return false;
                    }
                    const rect = element.getBoundingClientRect();
                    const searchRect = searchInput.getBoundingClientRect();
                    return (
                      Math.abs(rect.left - searchRect.left) <= 4
                      && Math.abs(rect.top - searchRect.top) <= 4
                      && rect.width >= (searchRect.width - 16)
                      && rect.height >= 28
                      && rect.height <= 36
                    );
                  })
                : null;
              const syncPill = topBarElements.find((element) => {
                const text = `${buttonText(element)} ${ariaLabel(element)}`;
                return (
                  text.includes('Attention needed')
                  || text.includes('Sync error')
                  || text.includes('Synced with Git')
                );
              });
              const themeToggle = topBarElements.find((element) => {
                return themeLabels.includes(buttonText(element)) || themeLabels.includes(ariaLabel(element));
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
                syncPill: toPayload(syncPill, buttonText(syncPill) || ariaLabel(syncPill)),
                searchField: toPayload(searchField, searchLabel),
                searchInput: toPayload(searchInput, searchLabel),
                createIssue: toPayload(createIssue, createLabel),
                repositoryAccess: toPayload(repositoryAccess, workspaceState),
                themeToggle: toPayload(
                  themeToggle,
                  buttonText(themeToggle) || ariaLabel(themeToggle),
                ),
              };
            }
            """,
            arg={
                "searchLabel": "Search issues",
                "createLabel": "Create issue",
                "workspacePrefix": "Workspace switcher:",
                "workspaceState": "Attachments limited",
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
            visible_text=str(payload.get("visibleText", "")).strip(),
            accessible_label=(
                str(payload.get("accessibleLabel")).strip()
                if payload.get("accessibleLabel") is not None
                else None
            ),
            client_width=float(payload.get("clientWidth", 0)),
            scroll_width=float(payload.get("scrollWidth", 0)),
        )
