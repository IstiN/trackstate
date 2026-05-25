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
    search_input: HeaderControlObservation
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
class RepositoryAccessStateObservation:
    trigger_label: str
    trigger_visible_text: str
    trigger_x: float
    trigger_y: float
    trigger_width: float
    trigger_height: float
    state_found: bool
    state_label: str
    state_visible_text: str
    state_x: float
    state_y: float
    state_width: float
    state_height: float
    state_fully_within_trigger: bool
    center_hit_tag_name: str
    center_hit_text: str
    center_hit_within_trigger: bool
    state_outer_html: str


@dataclass(frozen=True)
class ThemeToggleCycleObservation:
    initial_label: str
    toggled_label: str
    restored_label: str


class LiveTrackerHeaderPage:
    _button_selector = 'button, flt-semantics[role="button"]'
    _close_selector = 'button[aria-label="Close"], flt-semantics[aria-label="Close"]'
    _connect_selector = (
        'button[aria-label="Connect GitHub"], flt-semantics[aria-label="Connect GitHub"]'
    )
    _token_input_selector = 'input[aria-label="Fine-grained token"]'
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
        connected_marker = f"Connected as {user_login} to {repository}"
        normalized_repository = repository.casefold()
        current_body = self.body_text()
        if (
            (connected_marker in current_body and "Attachments limited" in current_body)
            or (
                "Workspace switcher:" in current_body
                and normalized_repository in current_body.casefold()
                and "Attachments limited" in current_body
            )
        ):
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
            if (
                (connected_marker in current_body and "Attachments limited" in current_body)
                or (
                    "Workspace switcher:" in current_body
                    and normalized_repository in current_body.casefold()
                    and "Attachments limited" in current_body
                )
            ):
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
        if (
            connected_marker not in body_text
            and not (
                "Workspace switcher:" in body_text
                and normalized_repository in body_text.casefold()
                and "Attachments limited" in body_text
            )
        ):
            raise AssertionError(
                "The hosted session did not expose the expected hosted "
                "`Attachments limited` header state.\n"
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
        if self._session.count(self._close_selector) > 0:
            self._session.click(self._close_selector, timeout_ms=30_000)
            return
        self._settings_page.dismiss_connection_banner()

    def observe_desktop_header(
        self,
        *,
        user_login: str | None = None,
        timeout_ms: int = 60_000,
    ) -> HeaderObservation | DesktopHeaderObservation:
        if user_login is None:
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
                      tagName: element.tagName.toLowerCase(),
                      label: fallbackLabel || accessibleLabel || visibleText,
                      role: element.getAttribute('role'),
                      x: rect.x,
                      y: rect.y,
                      width: rect.width,
                      height: rect.height,
                      centerY: rect.y + (rect.height / 2),
                      visibleText,
                      accessibleLabel,
                      placeholder: normalize(element.getAttribute('placeholder') || ''),
                      outerHtml: element.outerHTML.slice(0, 500),
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
                    const text = buttonText(element);
                    return (
                      label.startsWith(workspacePrefix)
                      || (label.includes(workspaceState) && element.getAttribute('role') === 'button')
                      || text === workspaceState
                    );
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
                sync_pill=_control_from_payload(payload.get("syncPill")),
                search_field=_control_from_payload(payload.get("searchField")),
                search_input=_control_from_payload(payload.get("searchInput")),
                create_issue=_control_from_payload(payload.get("createIssue")),
                repository_access=_control_from_payload(payload.get("repositoryAccess")),
                theme_toggle=_control_from_payload(payload.get("themeToggle")),
            )

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
                const commonCandidates = ancestorChains[0].filter((candidate) => {
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
                });
                if (commonCandidates.length === 0) {
                  return null;
                }
                const displayScore = (candidate) => {
                  const style = window.getComputedStyle(candidate);
                  let score = 0;
                  if (!['flex', 'inline-flex'].includes(style.display)) {
                    score += 2;
                  }
                  if (style.alignItems !== 'center') {
                    score += 1;
                  }
                  return score;
                };
                return [...commonCandidates].sort((left, right) => {
                  const scoreDelta = displayScore(left) - displayScore(right);
                  if (scoreDelta !== 0) {
                    return scoreDelta;
                  }
                  return area(left) - area(right);
                })[0] ?? null;
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
                Array.from(document.querySelectorAll('flt-semantics[role="button"]')).filter(
                  (element) =>
                    isVisible(element)
                    && (
                      element.getAttribute('aria-label') === 'Create issue'
                      || labelFor(element).label === 'Create issue'
                    ),
                ),
              );
              const repositoryAccessButton = smallest(
                Array.from(document.querySelectorAll('flt-semantics')).filter(
                  (element) => {
                    if (!isVisible(element)) {
                      return false;
                    }
                    const rect = element.getBoundingClientRect();
                    if (rect.y >= 110 || rect.height > 60) {
                      return false;
                    }
                    const labels = labelFor(element);
                    return (
                      labels.accessibleLabel.startsWith('Workspace switcher:')
                      || matchesAnyLabel(element, [
                        'Attachments limited',
                        'Repository access',
                        'Manage GitHub access',
                        'Connected',
                      ])
                    );
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
                  const label = labelFor(element).label.toLowerCase();
                  const rect = element.getBoundingClientRect();
                  return (
                    rect.height >= 32
                    && rect.width < 220
                    && rect.y < 110
                    && label.includes('sync')
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
                  searchInput,
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
            search_input=_control_from_payload(payload.get("searchInput")),
            create_issue_button=_control_from_payload(payload.get("createIssueButton")),
            repository_access_button=_control_from_payload(
                payload.get("repositoryAccessButton"),
            ),
            theme_toggle=_control_from_payload(payload.get("themeToggle")),
            profile_identity=_control_from_payload(payload.get("profileIdentity")),
            covering_container=_container_from_payload(payload.get("coveringContainer")),
        )

    def observe_repository_access_state_surface(
        self,
        *,
        expected_state: str = "Attachments limited",
        timeout_ms: int = 60_000,
    ) -> RepositoryAccessStateObservation:
        payload = self._session.wait_for_function(
            """
            (expectedState) => {
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
              const labelFor = (element) =>
                normalize(
                  element?.getAttribute('aria-label')
                  || element?.getAttribute('placeholder')
                  || element?.innerText
                  || element?.textContent
                  || '',
                );
              const visibleText = (element) =>
                normalize(element?.innerText || element?.textContent || '');
              const buttons = Array.from(
                document.querySelectorAll('flt-semantics[role="button"], button, [role="button"]'),
              ).filter(
                (element) => isVisible(element) && element.getBoundingClientRect().left > 250,
              );
              const trigger = smallest(
                buttons.filter((element) => {
                  const label = labelFor(element);
                  const text = visibleText(element);
                  return label.includes('Workspace switcher:')
                    || text.includes('Workspace switcher:')
                    || label === expectedState
                    || text === expectedState;
                }),
              );
              if (!trigger) {
                return null;
              }

              const triggerRect = trigger.getBoundingClientRect();
              const describeState = (element) => {
                if (!element) {
                  return {
                    stateFound: false,
                    stateLabel: '',
                    stateVisibleText: '',
                    stateX: 0,
                    stateY: 0,
                    stateWidth: 0,
                    stateHeight: 0,
                    stateFullyWithinTrigger: false,
                    centerHitTagName: '',
                    centerHitText: '',
                    centerHitWithinTrigger: false,
                    stateOuterHtml: '',
                  };
                }
                const rect = element.getBoundingClientRect();
                const centerX = rect.left + (rect.width / 2);
                const centerY = rect.top + (rect.height / 2);
                const hit = document.elementFromPoint(centerX, centerY);
                const fullyWithinTrigger =
                  rect.left >= (triggerRect.left - 1)
                  && rect.right <= (triggerRect.right + 1)
                  && rect.top >= (triggerRect.top - 1)
                  && rect.bottom <= (triggerRect.bottom + 1);
                const centerHitWithinTrigger = Boolean(hit && trigger.contains(hit));
                return {
                  stateFound: true,
                  stateLabel: labelFor(element),
                  stateVisibleText: visibleText(element),
                  stateX: rect.left,
                  stateY: rect.top,
                  stateWidth: rect.width,
                  stateHeight: rect.height,
                  stateFullyWithinTrigger: fullyWithinTrigger,
                  centerHitTagName: hit?.tagName?.toLowerCase?.() || '',
                  centerHitText: visibleText(hit),
                  centerHitWithinTrigger,
                  stateOuterHtml: element.outerHTML.slice(0, 500),
                };
              };

              const descendants = [trigger, ...Array.from(trigger.querySelectorAll('*'))]
                .filter(isVisible);
              const exactMatch = smallest(
                descendants.filter((element) => {
                  const label = labelFor(element);
                  const text = visibleText(element);
                  return label === expectedState || text === expectedState;
                }),
              );
              const partialMatch = smallest(
                descendants.filter((element) => {
                  const label = labelFor(element);
                  const text = visibleText(element);
                  return (
                    (label.includes(expectedState) || text.includes(expectedState))
                    && !label.includes('Workspace switcher:')
                    && !text.includes('Workspace switcher:')
                  );
                }),
              );
              const stateSurface = exactMatch || partialMatch;

              return {
                triggerLabel: labelFor(trigger),
                triggerVisibleText: visibleText(trigger),
                triggerX: triggerRect.left,
                triggerY: triggerRect.top,
                triggerWidth: triggerRect.width,
                triggerHeight: triggerRect.height,
                ...describeState(stateSurface),
              };
            }
            """,
            arg=expected_state,
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The hosted desktop header did not expose a visible workspace switcher trigger "
                "for the repository access visibility check.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return RepositoryAccessStateObservation(
            trigger_label=str(payload.get("triggerLabel", "")),
            trigger_visible_text=str(payload.get("triggerVisibleText", "")),
            trigger_x=float(payload.get("triggerX", 0.0)),
            trigger_y=float(payload.get("triggerY", 0.0)),
            trigger_width=float(payload.get("triggerWidth", 0.0)),
            trigger_height=float(payload.get("triggerHeight", 0.0)),
            state_found=bool(payload.get("stateFound")),
            state_label=str(payload.get("stateLabel", "")),
            state_visible_text=str(payload.get("stateVisibleText", "")),
            state_x=float(payload.get("stateX", 0.0)),
            state_y=float(payload.get("stateY", 0.0)),
            state_width=float(payload.get("stateWidth", 0.0)),
            state_height=float(payload.get("stateHeight", 0.0)),
            state_fully_within_trigger=bool(payload.get("stateFullyWithinTrigger")),
            center_hit_tag_name=str(payload.get("centerHitTagName", "")),
            center_hit_text=str(payload.get("centerHitText", "")),
            center_hit_within_trigger=bool(payload.get("centerHitWithinTrigger")),
            state_outer_html=str(payload.get("stateOuterHtml", "")),
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
