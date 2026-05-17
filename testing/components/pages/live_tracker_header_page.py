from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_project_settings_page import LiveProjectSettingsPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class HeaderControlObservation:
    tag_name: str
    label: str
    role: str | None
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
class DesktopHeaderObservation:
    body_text: str
    sync_pill: HeaderControlObservation
    search_field: HeaderControlObservation
    search_input: HeaderControlObservation
    create_issue: HeaderControlObservation
    repository_access: HeaderControlObservation
    theme_toggle: HeaderControlObservation


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

    def ensure_attachments_limited_state(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
        timeout_ms: int = 120_000,
    ) -> str:
        body_text = self.ensure_connected(
            token=token,
            repository=repository,
            user_login=user_login,
        )
        if "Attachments limited" in body_text:
            return body_text

        try:
            self._session.wait_for_any_text(
                ["Attachments limited", "Manage GitHub access", "GitHub connection failed:"],
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "The hosted desktop header never exposed the `Attachments limited` "
                "repository access state.\n"
                f"Observed body text:\n{self.body_text()}",
            ) from error

        body_text = self.body_text()
        if "GitHub connection failed:" in body_text:
            raise AssertionError(
                "Submitting the fine-grained token did not connect the hosted app.\n"
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
        self._settings_page.dismiss_connection_banner()

    def observe_desktop_header(
        self,
        *,
        user_login: str | None = None,
        timeout_ms: int = 60_000,
    ) -> HeaderObservation | DesktopHeaderObservation:
        payload = self._session.wait_for_function(
            """
            ({ userLogin, includeProfile }) => {
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
              const area = (element) => {
                const rect = element.getBoundingClientRect();
                return rect.width * rect.height;
              };
              const smallest = (elements) =>
                [...elements].sort((left, right) => area(left) - area(right))[0] ?? null;
              const descendantLabeledElement = (element) =>
                element.querySelector('input[aria-label], textarea[aria-label], [aria-label]');
              const labelFor = (element) => {
                const labeledDescendant = descendantLabeledElement(element);
                const accessibleLabel = normalize(
                  element.getAttribute('aria-label')
                  || labeledDescendant?.getAttribute('aria-label'),
                );
                const visibleText = normalize(element.innerText || element.textContent);
                const placeholder = normalize(
                  element.getAttribute('placeholder')
                  || labeledDescendant?.getAttribute('placeholder'),
                );
                return {
                  accessibleLabel,
                  visibleText,
                  placeholder,
                  label: accessibleLabel || visibleText || placeholder,
                };
              };
              const describeControl = (element) => {
                const rect = element.getBoundingClientRect();
                const labels = labelFor(element);
                return {
                  tagName: element.tagName.toLowerCase(),
                  label: labels.label,
                  role: element.getAttribute('role'),
                  accessibleLabel: labels.accessibleLabel,
                  visibleText: labels.visibleText,
                  placeholder: labels.placeholder,
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
              const matchesAnyLabel = (element, labels) => {
                const normalizedLabel = labelFor(element).label;
                return labels.some((label) => normalizedLabel === label);
              };
              const findHeaderContainer = (controls) => {
                const meaningfulControls = controls.filter(Boolean);
                if (meaningfulControls.length === 0) {
                  return null;
                }
                const viewportArea = window.innerWidth * window.innerHeight;
                const ignoredTags = new Set(['html', 'body', 'flutter-view']);
                const ancestorChains = meaningfulControls.map((element) => {
                  const chain = [];
                  let current = element.parentElement;
                  while (current && current !== document.documentElement) {
                    if (isVisible(current)) {
                      chain.push(current);
                    }
                    current = current.parentElement;
                  }
                  return chain;
                });
                return ancestorChains[0].find((candidate) => {
                  if (!candidate || meaningfulControls.includes(candidate)) {
                    return false;
                  }
                  const tagName = candidate.tagName.toLowerCase();
                  if (ignoredTags.has(tagName)) {
                    return false;
                  }
                  const rect = candidate.getBoundingClientRect();
                  return (
                    rect.y < 140
                    && rect.height <= 220
                    && area(candidate) < (viewportArea * 0.6)
                    && ancestorChains.every((chain) => chain.includes(candidate))
                  );
                }) ?? null;
              };

              const searchField = smallest(
                Array.from(document.querySelectorAll('flt-semantics')).filter(
                  (element) =>
                    isVisible(element)
                    && element.querySelector('input[aria-label="Search issues"]'),
                ),
              );
              const searchInput = Array.from(document.querySelectorAll('input')).find(
                (element) =>
                  isVisible(element)
                  && (
                    element.getAttribute('aria-label') === 'Search issues'
                    || (
                      searchField
                      && searchField.contains(element)
                      && !element.getAttribute('aria-label')
                    )
                  ),
              ) ?? null;
              const createIssueButton = smallest(
                Array.from(
                  document.querySelectorAll('flt-semantics[role="button"][aria-label="Create issue"]'),
                ).filter(isVisible),
              );
              const repositoryAccessButton = smallest(
                Array.from(document.querySelectorAll('flt-semantics[role="button"]')).filter(
                  (element) => {
                    if (!isVisible(element)) {
                      return false;
                    }
                    return matchesAnyLabel(element, [
                      'Attachments limited',
                      'Repository access',
                      'Manage GitHub access',
                      'Connected',
                    ]);
                  },
                ),
              );
              const themeToggle = smallest(
                Array.from(document.querySelectorAll('flt-semantics[role="button"]')).filter(
                  (element) => isVisible(element) && labelFor(element).label.toLowerCase().includes('theme'),
                ),
              );
              const syncStatusPill = smallest(
                Array.from(document.querySelectorAll('flt-semantics')).filter((element) => {
                  if (!isVisible(element)) {
                    return false;
                  }
                  const rect = element.getBoundingClientRect();
                  return (
                    rect.height >= 32
                    && rect.width < 220
                    && labelFor(element).label.includes('Synced with Git')
                  );
                }),
              );
              const profileIdentity = includeProfile
                ? smallest(
                    Array.from(document.querySelectorAll('flt-semantics')).filter((element) => {
                      if (!isVisible(element)) {
                        return false;
                      }
                      if ((element.getAttribute('role') || '').toLowerCase() === 'button') {
                        return false;
                      }
                      return labelFor(element).label === userLogin;
                    }),
                  )
                : null;

              if (
                !syncStatusPill
                || !searchField
                || !searchInput
                || !createIssueButton
                || !repositoryAccessButton
                || !themeToggle
                || (includeProfile && !profileIdentity)
              ) {
                return null;
              }

              const headerContainer = findHeaderContainer(
                [
                  syncStatusPill,
                  searchField,
                  createIssueButton,
                  repositoryAccessButton,
                  themeToggle,
                  profileIdentity,
                ].filter(Boolean),
              );

              return {
                bodyText: document.body?.innerText ?? '',
                syncStatusPill: describeControl(syncStatusPill),
                syncPill: describeControl(syncStatusPill),
                searchField: describeControl(searchField),
                searchInput: describeControl(searchInput),
                createIssueButton: describeControl(createIssueButton),
                createIssue: describeControl(createIssueButton),
                repositoryAccessButton: describeControl(repositoryAccessButton),
                repositoryAccess: describeControl(repositoryAccessButton),
                themeToggle: describeControl(themeToggle),
                profileIdentity: profileIdentity ? describeControl(profileIdentity) : null,
                coveringContainer: headerContainer ? describeContainer(headerContainer) : null,
              };
            }
            """,
            arg={
                "userLogin": user_login or "",
                "includeProfile": user_login is not None,
            },
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The deployed desktop tracker shell did not expose all expected header "
                "controls needed for the desktop header checks.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        if user_login is None:
            return DesktopHeaderObservation(
                body_text=str(payload.get("bodyText", "")),
                sync_pill=_control_from_payload(payload.get("syncPill")),
                search_field=_control_from_payload(payload.get("searchField")),
                search_input=_control_from_payload(payload.get("searchInput")),
                create_issue=_control_from_payload(payload.get("createIssue")),
                repository_access=_control_from_payload(payload.get("repositoryAccess")),
                theme_toggle=_control_from_payload(payload.get("themeToggle")),
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
    accessible_label = str(payload.get("accessibleLabel", ""))
    visible_text = str(payload.get("visibleText", ""))
    placeholder = str(payload.get("placeholder", ""))
    label = str(payload.get("label", "")) or accessible_label or visible_text or placeholder
    return HeaderControlObservation(
        tag_name=str(payload.get("tagName", "")),
        label=label,
        role=str(payload.get("role")) if payload.get("role") is not None else None,
        accessible_label=accessible_label,
        visible_text=visible_text,
        placeholder=placeholder,
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
