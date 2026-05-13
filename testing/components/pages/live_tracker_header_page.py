from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_project_settings_page import LiveProjectSettingsPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class HeaderControlObservation:
    tag_name: str
    accessible_label: str
    visible_text: str
    placeholder: str
    x: float
    y: float
    width: float
    height: float
    center_y: float
    outer_html: str


@dataclass(frozen=True)
class HeaderContainerObservation:
    tag_name: str
    display: str
    align_items: str
    justify_content: str
    x: float
    y: float
    width: float
    height: float
    outer_html: str


@dataclass(frozen=True)
class HeaderObservation:
    body_text: str
    sync_status_pill: HeaderControlObservation
    search_field: HeaderControlObservation
    create_issue_button: HeaderControlObservation
    repository_access_button: HeaderControlObservation
    theme_toggle: HeaderControlObservation
    profile_identity: HeaderControlObservation
    covering_container: HeaderContainerObservation | None


@dataclass(frozen=True)
class ThemeToggleCycleObservation:
    initial_label: str
    toggled_label: str
    restored_label: str


class LiveTrackerHeaderPage:
    _theme_button_selector = 'flt-semantics[role="button"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._settings_page = LiveProjectSettingsPage(tracker_page)

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> str:
        return self._settings_page.ensure_connected(
            token=token,
            repository=repository,
            user_login=user_login,
        )

    def dismiss_connection_banner(self) -> None:
        self._settings_page.dismiss_connection_banner()

    def observe_desktop_header(
        self,
        *,
        user_login: str,
        timeout_ms: int = 60_000,
    ) -> HeaderObservation:
        payload = self._session.wait_for_function(
            """
            ({ userLogin }) => {
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
              const isHeaderCandidate = (element) =>
                isVisible(element) && element.getBoundingClientRect().y < 110;
              const smallest = (elements) =>
                [...elements]
                  .sort(
                    (left, right) =>
                      (left.getBoundingClientRect().width * left.getBoundingClientRect().height)
                      - (right.getBoundingClientRect().width * right.getBoundingClientRect().height),
                  )[0] ?? null;
              const descendantLabeledElement = (element) =>
                element.querySelector('[aria-label], input[aria-label], textarea[aria-label]');
              const describeControl = (element) => {
                const rect = element.getBoundingClientRect();
                const labeledDescendant = descendantLabeledElement(element);
                const accessibleLabel = normalize(
                  element.getAttribute('aria-label')
                  || labeledDescendant?.getAttribute('aria-label'),
                );
                const placeholder = normalize(
                  element.getAttribute('placeholder')
                  || labeledDescendant?.getAttribute('placeholder'),
                );
                return {
                  tagName: element.tagName.toLowerCase(),
                  accessibleLabel,
                  visibleText: normalize(element.innerText),
                  placeholder,
                  x: rect.x,
                  y: rect.y,
                  width: rect.width,
                  height: rect.height,
                  centerY: rect.y + (rect.height / 2),
                  outerHtml: element.outerHTML.slice(0, 500),
                };
              };
              const describeContainer = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return {
                  tagName: element.tagName.toLowerCase(),
                  display: style.display,
                  alignItems: style.alignItems,
                  justifyContent: style.justifyContent,
                  x: rect.x,
                  y: rect.y,
                  width: rect.width,
                  height: rect.height,
                  outerHtml: element.outerHTML.slice(0, 500),
                };
              };

              const searchField = smallest(
                Array.from(document.querySelectorAll('flt-semantics'))
                  .filter(
                    (element) =>
                      isHeaderCandidate(element)
                      && element.querySelector('input[aria-label="Search issues"]'),
                  ),
              );
              const createIssueButton = smallest(
                Array.from(
                  document.querySelectorAll('flt-semantics[role="button"][aria-label="Create issue"]'),
                ).filter(isHeaderCandidate),
              );
              const repositoryAccessButton = smallest(
                Array.from(document.querySelectorAll('flt-semantics[role="button"]')).filter(
                  (element) => {
                    if (!isHeaderCandidate(element)) {
                      return false;
                    }
                    const label = normalize(
                      element.getAttribute('aria-label') || element.innerText,
                    );
                    return (
                      label === 'Attachments limited'
                      || label === 'Repository access'
                      || label === 'Manage GitHub access'
                      || label === 'Connected'
                    );
                  },
                ),
              );
              const themeToggle = smallest(
                Array.from(document.querySelectorAll('flt-semantics[role="button"]')).filter(
                  (element) => {
                    if (!isHeaderCandidate(element)) {
                      return false;
                    }
                    const label = normalize(
                      element.getAttribute('aria-label') || element.innerText,
                    ).toLowerCase();
                    return label.includes('theme');
                  },
                ),
              );
              const syncStatusPill = smallest(
                Array.from(document.querySelectorAll('flt-semantics')).filter((element) => {
                  if (!isHeaderCandidate(element)) {
                    return false;
                  }
                  const rect = element.getBoundingClientRect();
                  const text = normalize(element.getAttribute('aria-label') || element.innerText);
                  return (
                    rect.height >= 40
                    && rect.width < 220
                    && text.includes('Synced with Git')
                  );
                }),
              );
              const profileIdentity = smallest(
                Array.from(document.querySelectorAll('flt-semantics')).filter((element) => {
                  if (!isHeaderCandidate(element)) {
                    return false;
                  }
                  if ((element.getAttribute('role') || '').toLowerCase() === 'button') {
                    return false;
                  }
                  const rect = element.getBoundingClientRect();
                  const text = normalize(element.getAttribute('aria-label') || element.innerText);
                  return rect.height >= 40 && text === userLogin;
                }),
              );

              const controls = [
                syncStatusPill,
                searchField,
                createIssueButton,
                repositoryAccessButton,
                themeToggle,
                profileIdentity,
              ];
              if (controls.some((control) => !control)) {
                return null;
              }

              const bounds = controls.reduce(
                (accumulator, element) => {
                  const rect = element.getBoundingClientRect();
                  return {
                    left: Math.min(accumulator.left, rect.left),
                    top: Math.min(accumulator.top, rect.top),
                    right: Math.max(accumulator.right, rect.right),
                    bottom: Math.max(accumulator.bottom, rect.bottom),
                  };
                },
                {
                  left: Number.POSITIVE_INFINITY,
                  top: Number.POSITIVE_INFINITY,
                  right: Number.NEGATIVE_INFINITY,
                  bottom: Number.NEGATIVE_INFINITY,
                },
              );

              const coveringContainer = smallest(
                Array.from(document.querySelectorAll('body *')).filter((element) => {
                  if (!isVisible(element) || controls.includes(element)) {
                    return false;
                  }
                  const rect = element.getBoundingClientRect();
                  return (
                    rect.left <= bounds.left + 1
                    && rect.top <= bounds.top + 1
                    && rect.right >= bounds.right - 1
                    && rect.bottom >= bounds.bottom - 1
                  );
                }),
              );

              return {
                bodyText: document.body?.innerText ?? '',
                syncStatusPill: describeControl(syncStatusPill),
                searchField: describeControl(searchField),
                createIssueButton: describeControl(createIssueButton),
                repositoryAccessButton: describeControl(repositoryAccessButton),
                themeToggle: describeControl(themeToggle),
                profileIdentity: describeControl(profileIdentity),
                coveringContainer: coveringContainer
                  ? describeContainer(coveringContainer)
                  : null,
              };
            }
            """,
            arg={"userLogin": user_login},
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 2 failed: the deployed desktop tracker shell did not expose all "
                "expected header controls needed for TS-614.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return HeaderObservation(
            body_text=str(payload.get("bodyText", "")),
            sync_status_pill=_control_from_payload(payload.get("syncStatusPill")),
            search_field=_control_from_payload(payload.get("searchField")),
            create_issue_button=_control_from_payload(payload.get("createIssueButton")),
            repository_access_button=_control_from_payload(
                payload.get("repositoryAccessButton"),
            ),
            theme_toggle=_control_from_payload(payload.get("themeToggle")),
            profile_identity=_control_from_payload(payload.get("profileIdentity")),
            covering_container=_container_from_payload(payload.get("coveringContainer")),
        )

    def toggle_theme_and_restore(
        self,
        *,
        timeout_ms: int = 30_000,
    ) -> ThemeToggleCycleObservation:
        initial_label = self._current_theme_label(timeout_ms=timeout_ms)
        toggled_label = "Light theme" if initial_label == "Dark theme" else "Dark theme"
        self._session.click(
            self._theme_button_selector,
            has_text=initial_label,
            timeout_ms=timeout_ms,
        )
        self._wait_for_theme_label(toggled_label, timeout_ms=timeout_ms)
        self._session.click(
            self._theme_button_selector,
            has_text=toggled_label,
            timeout_ms=timeout_ms,
        )
        restored_label = self._wait_for_theme_label(initial_label, timeout_ms=timeout_ms)
        return ThemeToggleCycleObservation(
            initial_label=initial_label,
            toggled_label=toggled_label,
            restored_label=restored_label,
        )

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def body_text(self) -> str:
        return self._tracker_page.body_text()

    def _current_theme_label(self, *, timeout_ms: int) -> str:
        payload = self._session.wait_for_function(
            """
            () => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && rect.y < 110
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const button = Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                .find((candidate) => {
                  if (!isVisible(candidate)) {
                    return false;
                  }
                  const label = normalize(
                    candidate.getAttribute('aria-label') || candidate.innerText,
                  ).toLowerCase();
                  return label.includes('theme');
                });
              if (!button) {
                return null;
              }
              return normalize(button.getAttribute('aria-label') || button.innerText);
            }
            """,
            timeout_ms=timeout_ms,
        )
        label = str(payload).strip()
        if label not in {"Dark theme", "Light theme"}:
            raise AssertionError(
                "Human verification failed: the desktop header did not expose a visible "
                "theme toggle label before interaction.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return label

    def _wait_for_theme_label(self, label: str, *, timeout_ms: int) -> str:
        payload = self._session.wait_for_function(
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
                  && rect.y < 110
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const button = Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                .find((candidate) => {
                  if (!isVisible(candidate)) {
                    return false;
                  }
                  const currentLabel = normalize(
                    candidate.getAttribute('aria-label') || candidate.innerText,
                  );
                  return currentLabel === expectedLabel;
                });
              return button ? expectedLabel : null;
            }
            """,
            arg=label,
            timeout_ms=timeout_ms,
        )
        observed = str(payload).strip()
        if observed != label:
            raise AssertionError(
                "Human verification failed: the visible theme toggle did not reach the "
                f'expected "{label}" state.\n'
                f"Observed body text:\n{self.body_text()}",
            )
        return observed


def _control_from_payload(payload: object) -> HeaderControlObservation:
    if not isinstance(payload, dict):
        raise AssertionError(
            f"Expected a header control payload, received: {payload!r}",
        )
    return HeaderControlObservation(
        tag_name=str(payload.get("tagName", "")),
        accessible_label=str(payload.get("accessibleLabel", "")),
        visible_text=str(payload.get("visibleText", "")),
        placeholder=str(payload.get("placeholder", "")),
        x=float(payload.get("x", 0.0)),
        y=float(payload.get("y", 0.0)),
        width=float(payload.get("width", 0.0)),
        height=float(payload.get("height", 0.0)),
        center_y=float(payload.get("centerY", 0.0)),
        outer_html=str(payload.get("outerHtml", "")),
    )


def _container_from_payload(payload: object) -> HeaderContainerObservation | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise AssertionError(
            f"Expected a header container payload, received: {payload!r}",
        )
    return HeaderContainerObservation(
        tag_name=str(payload.get("tagName", "")),
        display=str(payload.get("display", "")),
        align_items=str(payload.get("alignItems", "")),
        justify_content=str(payload.get("justifyContent", "")),
        x=float(payload.get("x", 0.0)),
        y=float(payload.get("y", 0.0)),
        width=float(payload.get("width", 0.0)),
        height=float(payload.get("height", 0.0)),
        outer_html=str(payload.get("outerHtml", "")),
    )
