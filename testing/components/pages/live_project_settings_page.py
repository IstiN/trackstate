from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class ProjectSettingsUiObservation:
    settings_text: str
    status_dialog_text: str
    status_list_text: str
    workflow_dialog_text: str
    workflow_tab_text: str
    post_save_text: str


@dataclass(frozen=True)
class RepositoryAccessCalloutObservation:
    title: str
    message: str
    rendered_text: str
    semantic_label: str
    border_color: str | None
    background_color: str | None
    border_width: str | None
    top: float
    left: float
    width: float
    height: float


@dataclass(frozen=True)
class RepositoryAccessSectionObservation:
    body_text: str
    section_text: str
    primary_callout: RepositoryAccessCalloutObservation
    secondary_callout: RepositoryAccessCalloutObservation


@dataclass(frozen=True)
class RepositoryAccessControlsObservation:
    body_text: str
    section_text: str
    project_settings_visible: bool
    repository_access_visible: bool
    fine_grained_token_visible: bool
    remember_on_this_browser_visible: bool
    connect_token_visible: bool


@dataclass(frozen=True)
class RepositoryAccessFocusObservation:
    label: str | None
    tag_name: str
    role: str | None
    accessible_name: str | None
    text: str
    outer_html: str
    body_text: str


@dataclass(frozen=True)
class ProjectSettingsTabObservation:
    body_text: str
    selected_tab_label: str
    selected_tab_semantics: str
    attachment_storage_visible: bool
    add_status_visible: bool


@dataclass(frozen=True)
class ProjectSettingsNavigationState:
    body_text: str
    settings_heading_visible: bool
    selected_tab_label: str
    attachments_tab_selected: bool
    attachment_storage_visible: bool
    add_status_visible: bool


class LiveProjectSettingsPage:
    _button_selector = 'flt-semantics[role="button"]'
    _tab_selector = 'flt-semantics[role="tab"]'
    _connect_selector = 'flt-semantics[aria-label="Connect GitHub"]'
    _token_input_selector = 'input[aria-label="Fine-grained token"]'
    _remember_on_this_browser_selector = (
        'flt-semantics[role="checkbox"][aria-label*="Remember on this browser"]'
    )
    _connect_token_selector = 'flt-semantics[role="button"][aria-label*="Connect token"]'
    _repository_access_selector = 'flt-semantics[aria-label*="Repository access"]'
    _settings_nav_selector = 'flt-semantics[role="button"]'
    _settings_heading = "Project Settings"
    _settings_admin_heading = "Project settings administration"
    _status_id_selector = 'input[aria-label="ID"]'
    _status_name_selector = 'input[aria-label="Name"]'
    _transition_name_selector = 'input[aria-label="Transition name"]'
    _save_settings_selector = 'flt-semantics[aria-label="Save settings"]'
    _close_selector = 'flt-semantics[aria-label="Close"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
        timeout_seconds: int = 240,
    ) -> str:
        connected_banner = TrackStateTrackerPage.CONNECTED_BANNER_TEMPLATE.format(
            user_login=user_login,
            repository=repository,
        )
        current_body = self.body_text()
        if connected_banner in current_body:
            return current_body

        if self._session.count(self._connect_selector) == 0:
            raise AssertionError(
                "Step 1 failed: the hosted runtime did not expose the Connect GitHub "
                "action needed to enter the writable Settings flow.\n"
                f"Observed body text:\n{current_body}",
            )

        for attempt in range(2):
            if self._session.count(self._token_input_selector) == 0:
                self._session.click(self._connect_selector, timeout_ms=30_000)
            self._session.wait_for_selector(self._token_input_selector, timeout_ms=30_000)
            self._session.fill(self._token_input_selector, token, timeout_ms=30_000)
            self._session.press(self._token_input_selector, "Tab", timeout_ms=30_000)
            self._session.click(
                self._button_selector,
                has_text="Connect token",
                timeout_ms=30_000,
            )

            try:
                wait_match = self._session.wait_for_any_text(
                    [
                        connected_banner,
                        "Attachments limited",
                        "Manage GitHub access",
                        "GitHub connection failed:",
                    ],
                    timeout_ms=timeout_seconds * 1_000,
                )
            except WebAppTimeoutError:
                current_body = self.body_text()
                if any(
                    marker in current_body
                    for marker in (
                        connected_banner,
                        "Attachments limited",
                        "Manage GitHub access",
                    )
                ):
                    return current_body
                if attempt == 0:
                    continue
                raise AssertionError(
                    "Step 3 failed: submitting the fine-grained token never reached a "
                    "connected hosted session.\n"
                    f"Observed body text:\n{current_body}",
                ) from None

            if wait_match.matched_text == "GitHub connection failed:":
                raise AssertionError(
                    "Step 3 failed: submitting the fine-grained token did not reach a "
                    "connected hosted session.\n"
                    f"Observed body text:\n{wait_match.body_text}",
                )
            return wait_match.body_text

        raise AssertionError(
            "Step 3 failed: the hosted token connect flow could not complete.",
        )

    def dismiss_connection_banner(self) -> None:
        if self._session.count(self._close_selector) == 0:
            return
        self._session.click(self._close_selector, timeout_ms=30_000)

    def open_settings(self) -> str:
        self._session.click(
            self._settings_nav_selector,
            has_text="Settings",
            timeout_ms=30_000,
        )
        return self._session.wait_for_text(self._settings_heading, timeout_ms=60_000)

    def selected_tab_label(self, *, timeout_ms: int = 30_000) -> str:
        payload = self._session.wait_for_function(
            """
            () => {
              const tab = Array.from(
                document.querySelectorAll('flt-semantics[role="tab"]'),
              ).find((candidate) => candidate.getAttribute('aria-selected') === 'true');
              return tab?.getAttribute('aria-label') ?? null;
            }
            """,
            timeout_ms=timeout_ms,
        )
        label = str(payload).strip()
        if not label:
            raise AssertionError(
                "Precondition failed: the hosted Project Settings surface did not expose "
                "a selected sub-tab.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return label

    def open_tab(
        self,
        label: str,
        *,
        expected_visible_text: str | None = None,
        timeout_ms: int = 30_000,
    ) -> str:
        selector = self._tab_selector_for(label)
        self._scroll_into_view(selector)
        self._session.click(selector, timeout_ms=timeout_ms)
        payload = self._session.wait_for_function(
            """
            ({ selector, expectedVisibleText }) => {
              const tab = document.querySelector(selector);
              const bodyText = document.body?.innerText ?? '';
              if (!tab || tab.getAttribute('aria-selected') !== 'true') {
                return null;
              }
              if (expectedVisibleText && !bodyText.includes(expectedVisibleText)) {
                return null;
              }
              return bodyText;
            }
            """,
            arg={
                "selector": selector,
                "expectedVisibleText": expected_visible_text,
            },
            timeout_ms=timeout_ms,
        )
        return str(payload)

    def observe_attachment_settings_surface(
        self,
        *,
        timeout_ms: int = 60_000,
    ) -> ProjectSettingsTabObservation:
        selector = self._tab_selector_for("Attachments")
        payload = self._session.wait_for_function(
            """
            ({ selector, settingsHeading, attachmentStorageLabel }) => {
              const bodyText = document.body?.innerText ?? '';
              const tab = document.querySelector(selector);
              if (!tab || tab.getAttribute('aria-selected') !== 'true') {
                return null;
              }
              if (
                !bodyText.includes(settingsHeading)
                || !bodyText.includes(attachmentStorageLabel)
              ) {
                return null;
              }
              return {
                bodyText,
                selectedTabLabel: ((tab.innerText || '').trim() || (tab.getAttribute('aria-label') ?? '')).trim(),
                selectedTabSemantics: tab.getAttribute('aria-label') ?? '',
                attachmentStorageVisible: bodyText.includes(attachmentStorageLabel),
                addStatusVisible: bodyText.includes('Add status'),
              };
            }
            """,
            arg={
                "selector": selector,
                "settingsHeading": self._settings_heading,
                "attachmentStorageLabel": "Attachment storage mode",
            },
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 2 failed: the hosted flow did not navigate to the Project Settings "
                "Attachments configuration after the user activated `Open settings`.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return ProjectSettingsTabObservation(
            body_text=str(payload.get("bodyText", "")),
            selected_tab_label=str(payload.get("selectedTabLabel", "")).strip(),
            selected_tab_semantics=str(payload.get("selectedTabSemantics", "")).strip(),
            attachment_storage_visible=bool(payload.get("attachmentStorageVisible")),
            add_status_visible=bool(payload.get("addStatusVisible")),
        )

    def navigation_state(self) -> ProjectSettingsNavigationState:
        payload = self._session.evaluate(
            """
            ({ settingsHeading, attachmentStorageLabel, attachmentsTabLabel }) => {
              const bodyText = document.body?.innerText ?? '';
              const selectedTab = Array.from(
                document.querySelectorAll('flt-semantics[role="tab"]'),
              ).find((candidate) => candidate.getAttribute('aria-selected') === 'true');
              const selectedTabLabel = selectedTab?.getAttribute('aria-label') ?? '';
              return {
                bodyText,
                settingsHeadingVisible: bodyText.includes(settingsHeading),
                selectedTabLabel,
                attachmentsTabSelected: selectedTabLabel === attachmentsTabLabel,
                attachmentStorageVisible: bodyText.includes(attachmentStorageLabel),
                addStatusVisible: bodyText.includes('Add status'),
              };
            }
            """,
            arg={
                "settingsHeading": self._settings_heading,
                "attachmentStorageLabel": "Attachment storage mode",
                "attachmentsTabLabel": "Attachments",
            },
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The hosted page did not expose a readable Project Settings navigation "
                "snapshot.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return ProjectSettingsNavigationState(
            body_text=str(payload.get("bodyText", "")),
            settings_heading_visible=bool(payload.get("settingsHeadingVisible")),
            selected_tab_label=str(payload.get("selectedTabLabel", "")).strip(),
            attachments_tab_selected=bool(payload.get("attachmentsTabSelected")),
            attachment_storage_visible=bool(payload.get("attachmentStorageVisible")),
            add_status_visible=bool(payload.get("addStatusVisible")),
        )

    def add_status(
        self,
        *,
        status_id: str,
        status_name: str,
    ) -> tuple[str, str]:
        self._session.click('flt-semantics[aria-label="Add status"]', timeout_ms=30_000)
        self._session.wait_for_selector(self._status_id_selector, timeout_ms=30_000)
        self._session.fill(self._status_id_selector, status_id, timeout_ms=30_000)
        self._session.fill(self._status_name_selector, status_name, timeout_ms=30_000)
        status_dialog_text = self.body_text()
        self._session.click(self._button_selector, has_text="Save", timeout_ms=30_000)
        self._session.wait_for_selector(
            self._status_id_selector,
            state="hidden",
            timeout_ms=60_000,
        )
        self._session.wait_for_selector(self._save_settings_selector, timeout_ms=30_000)
        status_list_text = self.body_text()
        return status_dialog_text, status_list_text

    def open_workflows_tab(self) -> str:
        self._session.click(
            'flt-semantics[role="tab"][aria-label="Workflows"]',
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(
            'flt-semantics[aria-label*="Delivery Workflow"]',
            timeout_ms=30_000,
        )
        return self.body_text()

    def update_workflow_transition_name(
        self,
        *,
        workflow_name: str,
        transition_index: int,
        transition_name: str,
    ) -> tuple[str, str]:
        self._session.click(
            f'flt-semantics[aria-label="Edit workflow {self._escape(workflow_name)}"]',
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(
            self._transition_name_selector,
            timeout_ms=30_000,
        )
        self._session.fill(
            self._transition_name_selector,
            transition_name,
            index=transition_index,
            timeout_ms=30_000,
        )
        workflow_dialog_text = self.body_text()
        self._session.click(self._button_selector, has_text="Save", timeout_ms=30_000)
        self._session.wait_for_selector(self._save_settings_selector, timeout_ms=30_000)
        workflow_tab_text = self.body_text()
        return workflow_dialog_text, workflow_tab_text

    def save_settings(self) -> str:
        self._session.click(self._save_settings_selector, timeout_ms=30_000)
        self._session.wait_for_text(self._settings_admin_heading, timeout_ms=120_000)
        return self.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def body_text(self) -> str:
        return self._tracker_page.body_text()

    def observe_repository_access_controls(
        self,
        *,
        timeout_ms: int = 60_000,
    ) -> RepositoryAccessControlsObservation:
        payload = self._session.wait_for_function(
            """
            ({ settingsHeading, repositoryAccessLabel, repositoryAccessSelector, tokenSelector, rememberSelector, connectSelector }) => {
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
              const visibleMatches = (selector) => Array.from(document.querySelectorAll(selector))
                .filter((candidate) => isVisible(candidate));
              const visibleMatchesWithin = (root, selector) => {
                const descendants = Array.from(root.querySelectorAll(selector))
                  .filter((candidate) => isVisible(candidate));
                if (
                  typeof root.matches === 'function'
                  && root.matches(selector)
                  && isVisible(root)
                ) {
                  descendants.unshift(root);
                }
                return descendants;
              };
              const candidateRoots = [];
              const seenRoots = new Set();
              for (const repositoryAccessHeading of visibleMatches(repositoryAccessSelector)) {
                let current = repositoryAccessHeading;
                while (current && current !== document.body) {
                  if (isVisible(current) && !seenRoots.has(current)) {
                    seenRoots.add(current);
                    candidateRoots.push(current);
                  }
                  current = current.parentElement;
                }
              }
              const bodyText = document.body?.innerText ?? '';
              const repositoryAccess = candidateRoots
                .map((candidate) => {
                  const sectionText = normalize(
                    candidate.getAttribute('aria-label')
                    ?? candidate.innerText
                    ?? '',
                  );
                  const tokenVisible = visibleMatchesWithin(candidate, tokenSelector).length > 0;
                  const rememberVisible =
                    visibleMatchesWithin(candidate, rememberSelector).length > 0;
                  const connectVisible =
                    visibleMatchesWithin(candidate, connectSelector).length > 0;
                  const rect = candidate.getBoundingClientRect();
                  return {
                    element: candidate,
                    area: rect.width * rect.height,
                    sectionText,
                    tokenVisible,
                    rememberVisible,
                    connectVisible,
                  };
                })
                .filter((candidate) =>
                  candidate.sectionText.includes(repositoryAccessLabel)
                  && candidate.tokenVisible
                  && candidate.rememberVisible
                  && candidate.connectVisible,
                )
                .sort((left, right) => left.area - right.area)[0] ?? null;
              if (
                !bodyText.includes(settingsHeading)
                || !repositoryAccess
              ) {
                return null;
              }
              return {
                bodyText,
                sectionText: repositoryAccess.sectionText,
                projectSettingsVisible: bodyText.includes(settingsHeading),
                repositoryAccessVisible: repositoryAccess.sectionText.includes(repositoryAccessLabel),
                fineGrainedTokenVisible: repositoryAccess.tokenVisible,
                rememberOnThisBrowserVisible: repositoryAccess.rememberVisible,
                connectTokenVisible: repositoryAccess.connectVisible,
              };
            }
            """,
            arg={
                "settingsHeading": self._settings_heading,
                "repositoryAccessLabel": "Repository access",
                "repositoryAccessSelector": self._repository_access_selector,
                "tokenSelector": self._token_input_selector,
                "rememberSelector": self._remember_on_this_browser_selector,
                "connectSelector": self._connect_token_selector,
            },
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 1 failed: the hosted Project Settings screen did not expose the "
                "visible Repository access controls needed for keyboard traversal.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return RepositoryAccessControlsObservation(
            body_text=str(payload.get("bodyText", "")),
            section_text=str(payload.get("sectionText", "")),
            project_settings_visible=bool(payload.get("projectSettingsVisible")),
            repository_access_visible=bool(payload.get("repositoryAccessVisible")),
            fine_grained_token_visible=bool(payload.get("fineGrainedTokenVisible")),
            remember_on_this_browser_visible=bool(
                payload.get("rememberOnThisBrowserVisible")
            ),
            connect_token_visible=bool(payload.get("connectTokenVisible")),
        )

    def focus_repository_access_token_field(self, *, timeout_ms: int = 30_000) -> None:
        focused = self._session.wait_for_function(
            """
            ({ repositoryAccessLabel, repositoryAccessSelector, tokenSelector, rememberSelector, connectSelector }) => {
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
              const visibleMatches = (selector) => Array.from(document.querySelectorAll(selector))
                .filter((candidate) => isVisible(candidate));
              const visibleMatchesWithin = (root, selector) => {
                const descendants = Array.from(root.querySelectorAll(selector))
                  .filter((candidate) => isVisible(candidate));
                if (
                  typeof root.matches === 'function'
                  && root.matches(selector)
                  && isVisible(root)
                ) {
                  descendants.unshift(root);
                }
                return descendants;
              };
              const candidateRoots = [];
              const seenRoots = new Set();
              for (const repositoryAccessHeading of visibleMatches(repositoryAccessSelector)) {
                let current = repositoryAccessHeading;
                while (current && current !== document.body) {
                  if (isVisible(current) && !seenRoots.has(current)) {
                    seenRoots.add(current);
                    candidateRoots.push(current);
                  }
                  current = current.parentElement;
                }
              }
              const repositoryAccess = candidateRoots
                .map((candidate) => {
                  const sectionText = normalize(
                    candidate.getAttribute('aria-label')
                    ?? candidate.innerText
                    ?? '',
                  );
                  const tokenMatches = visibleMatchesWithin(candidate, tokenSelector);
                  const rememberMatches = visibleMatchesWithin(candidate, rememberSelector);
                  const connectMatches = visibleMatchesWithin(candidate, connectSelector);
                  const rect = candidate.getBoundingClientRect();
                  return {
                    element: candidate,
                    area: rect.width * rect.height,
                    sectionText,
                    tokenMatches,
                    rememberMatches,
                    connectMatches,
                  };
                })
                .filter((candidate) =>
                  candidate.sectionText.includes(repositoryAccessLabel)
                  && candidate.tokenMatches.length > 0
                  && candidate.rememberMatches.length > 0
                  && candidate.connectMatches.length > 0,
                )
                .sort((left, right) => left.area - right.area)[0] ?? null;
              const token = repositoryAccess?.tokenMatches[0] ?? null;
              if (!token) {
                return null;
              }
              token.scrollIntoView({ block: 'center', inline: 'center' });
              token.focus();
              return document.activeElement === token;
            }
            """,
            arg={
                "repositoryAccessLabel": "Repository access",
                "repositoryAccessSelector": self._repository_access_selector,
                "tokenSelector": self._token_input_selector,
                "rememberSelector": self._remember_on_this_browser_selector,
                "connectSelector": self._connect_token_selector,
            },
            timeout_ms=timeout_ms,
        )
        if focused is not True:
            raise AssertionError(
                "Step 2 failed: could not focus the visible Fine-grained token input inside "
                "the Repository access section.\n"
                f"Observed body text:\n{self.body_text()}",
            )

    def press_tab(self, *, timeout_ms: int = 30_000) -> None:
        self._session.press_key("Tab", timeout_ms=timeout_ms)

    def press_tab_from_repository_access_focus(
        self,
        current_label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> None:
        if current_label not in {
            "Fine-grained token",
            "Remember on this browser",
            "Connect token",
        }:
            raise AssertionError(
                f"Unsupported Repository access focus target for Tab navigation: {current_label!r}.",
            )
        self.wait_for_repository_access_focus(current_label, timeout_ms=timeout_ms)
        self._session.press_key("Tab", timeout_ms=timeout_ms)

    def wait_for_repository_access_focus(
        self,
        expected_label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> RepositoryAccessFocusObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({ repositoryAccessLabel, repositoryAccessSelector, tokenSelector, rememberSelector, connectSelector, expectedLabel }) => {
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
                  const visibleMatches = (selector) => Array.from(document.querySelectorAll(selector))
                    .filter((candidate) => isVisible(candidate));
                  const visibleMatchesWithin = (root, selector) => {
                    const descendants = Array.from(root.querySelectorAll(selector))
                      .filter((candidate) => isVisible(candidate));
                    if (
                      typeof root.matches === 'function'
                      && root.matches(selector)
                      && isVisible(root)
                    ) {
                      descendants.unshift(root);
                    }
                    return descendants;
                  };
                  const candidateRoots = [];
                  const seenRoots = new Set();
                  for (const repositoryAccessHeading of visibleMatches(repositoryAccessSelector)) {
                    let current = repositoryAccessHeading;
                    while (current && current !== document.body) {
                      if (isVisible(current) && !seenRoots.has(current)) {
                        seenRoots.add(current);
                        candidateRoots.push(current);
                      }
                      current = current.parentElement;
                    }
                  }
                  const repositoryAccess = candidateRoots
                    .map((candidate) => {
                      const sectionText = normalize(
                        candidate.getAttribute('aria-label')
                        ?? candidate.innerText
                        ?? '',
                      );
                      const tokenMatches = visibleMatchesWithin(candidate, tokenSelector);
                      const rememberMatches = visibleMatchesWithin(candidate, rememberSelector);
                      const connectMatches = visibleMatchesWithin(candidate, connectSelector);
                      const rect = candidate.getBoundingClientRect();
                      return {
                        element: candidate,
                        area: rect.width * rect.height,
                        sectionText,
                        tokenMatches,
                        rememberMatches,
                        connectMatches,
                      };
                    })
                    .filter((candidate) =>
                      candidate.sectionText.includes(repositoryAccessLabel)
                      && candidate.tokenMatches.length > 0
                      && candidate.rememberMatches.length > 0
                      && candidate.connectMatches.length > 0,
                    )
                    .sort((left, right) => left.area - right.area)[0] ?? null;
                  if (!repositoryAccess) {
                    return null;
                  }
                  const active = document.activeElement;
                  const bodyText = document.body?.innerText ?? '';
                  if (!active || !repositoryAccess.element.contains(active)) {
                    return null;
                  }
                  const identify = (element) => {
                    if (!element) {
                      return null;
                    }
                    if (
                      typeof element.matches === 'function'
                      && element.matches(tokenSelector)
                      && isVisible(element)
                    ) {
                      return 'Fine-grained token';
                    }
                    if (
                      typeof element.matches === 'function'
                      && element.matches(rememberSelector)
                      && isVisible(element)
                    ) {
                      return 'Remember on this browser';
                    }
                    if (
                      typeof element.matches === 'function'
                      && element.matches(connectSelector)
                      && isVisible(element)
                    ) {
                      return 'Connect token';
                    }
                    if (typeof element.closest === 'function') {
                      const tokenMatch = element.closest(tokenSelector);
                      if (
                        tokenMatch
                        && repositoryAccess.element.contains(tokenMatch)
                        && isVisible(tokenMatch)
                      ) {
                        return 'Fine-grained token';
                      }
                      const rememberMatch = element.closest(rememberSelector);
                      if (
                        rememberMatch
                        && repositoryAccess.element.contains(rememberMatch)
                        && isVisible(rememberMatch)
                      ) {
                        return 'Remember on this browser';
                      }
                      const connectMatch = element.closest(connectSelector);
                      if (
                        connectMatch
                        && repositoryAccess.element.contains(connectMatch)
                        && isVisible(connectMatch)
                      ) {
                        return 'Connect token';
                      }
                    }
                    return null;
                  };
                  const label = identify(active);
                  if (label !== expectedLabel) {
                    return null;
                  }
                  const text = (active.textContent ?? '').replace(/\\s+/g, ' ').trim();
                  return {
                    label,
                    tagName: active.tagName,
                    role: active.getAttribute('role'),
                    accessibleName: active.getAttribute('aria-label') || text || null,
                    text,
                    outerHtml: active.outerHTML.slice(0, 400),
                    bodyText,
                  };
                }
                """,
                arg={
                    "repositoryAccessLabel": "Repository access",
                    "repositoryAccessSelector": self._repository_access_selector,
                    "tokenSelector": self._token_input_selector,
                    "rememberSelector": self._remember_on_this_browser_selector,
                    "connectSelector": self._connect_token_selector,
                    "expectedLabel": expected_label,
                },
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError:
            payload = None
        if not isinstance(payload, dict):
            active = self._session.active_element()
            raise AssertionError(
                f"Keyboard focus did not reach `{expected_label}` within the Repository "
                "access controls.\n"
                f"Observed active element label: {active.accessible_name!r}\n"
                f"Observed active element role: {active.role!r}\n"
                f"Observed active element HTML: {active.outer_html}\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return RepositoryAccessFocusObservation(
            label=str(payload.get("label")) if payload.get("label") is not None else None,
            tag_name=str(payload.get("tagName", "")),
            role=str(payload.get("role")) if payload.get("role") is not None else None,
            accessible_name=(
                str(payload.get("accessibleName"))
                if payload.get("accessibleName") is not None
                else None
            ),
            text=str(payload.get("text", "")),
            outer_html=str(payload.get("outerHtml", "")),
            body_text=str(payload.get("bodyText", "")),
        )

    def observe_repository_access_section(
        self,
        *,
        primary_title: str,
        secondary_title: str,
        timeout_ms: int = 120_000,
    ) -> RepositoryAccessSectionObservation:
        payload = self._session.wait_for_function(
            """
            ({ primaryTitle, secondaryTitle }) => {
              const normalize = (value) => value.replace(/\\s+/g, ' ').trim();
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
              const collectSemantics = (root) =>
                Array.from(root.querySelectorAll('flt-semantics[aria-label]'))
                  .filter((candidate) => isVisible(candidate))
                  .map((candidate) => {
                    const rect = candidate.getBoundingClientRect();
                    const label = candidate.getAttribute('aria-label') ?? '';
                    const normalizedLabel = normalize(label);
                    return {
                      element: candidate,
                      rect,
                      area: rect.width * rect.height,
                      label,
                      normalizedLabel,
                    };
                  });
              const matchesCallout = (candidate, title) =>
                candidate.normalizedLabel.includes(title)
                && candidate.normalizedLabel.length > title.length + 20;
              const extractVisibleStyles = (element) => {
                if (!element) {
                  return null;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                const hasVisibleBorder =
                  Number.parseFloat(style.borderTopWidth || '0') > 0
                  && style.borderTopColor !== 'transparent'
                  && style.borderTopColor !== 'rgba(0, 0, 0, 0)';
                const hasVisibleBackground =
                  style.backgroundColor !== 'transparent'
                  && style.backgroundColor !== 'rgba(0, 0, 0, 0)';
                if (!hasVisibleBorder && !hasVisibleBackground) {
                  return null;
                }
                return {
                  rect,
                  borderColor: style.borderTopColor || null,
                  backgroundColor: style.backgroundColor || null,
                  borderWidth: style.borderTopWidth || null,
                };
              };
              const findStyledElement = (semantics) => {
                const candidateElements = [];
                const seen = new Set();
                const addCandidate = (element) => {
                  if (!element || seen.has(element)) {
                    return;
                  }
                  seen.add(element);
                  candidateElements.push(element);
                };

                let ancestor = semantics.element;
                while (ancestor && ancestor !== document.body) {
                  addCandidate(ancestor);
                  ancestor = ancestor.parentElement;
                }

                const insetX = Math.min(Math.max(semantics.rect.width * 0.1, 8), semantics.rect.width / 2);
                const insetY = Math.min(Math.max(semantics.rect.height * 0.1, 8), semantics.rect.height / 2);
                const probePoints = [
                  [semantics.rect.left + semantics.rect.width / 2, semantics.rect.top + semantics.rect.height / 2],
                  [semantics.rect.left + insetX, semantics.rect.top + insetY],
                  [semantics.rect.right - insetX, semantics.rect.top + insetY],
                  [semantics.rect.left + insetX, semantics.rect.bottom - insetY],
                  [semantics.rect.right - insetX, semantics.rect.bottom - insetY],
                ]
                  .map(([x, y]) => [
                    Math.min(Math.max(x, 0), window.innerWidth - 1),
                    Math.min(Math.max(y, 0), window.innerHeight - 1),
                  ]);
                for (const [x, y] of probePoints) {
                  for (const element of document.elementsFromPoint(x, y)) {
                    addCandidate(element);
                  }
                }

                const centerX = semantics.rect.left + semantics.rect.width / 2;
                const centerY = semantics.rect.top + semantics.rect.height / 2;
                const styledCandidates = candidateElements
                  .map((element) => {
                    const styles = extractVisibleStyles(element);
                    if (!styles) {
                      return null;
                    }
                    const rect = styles.rect;
                    const overlapLeft = Math.max(rect.left, semantics.rect.left);
                    const overlapTop = Math.max(rect.top, semantics.rect.top);
                    const overlapRight = Math.min(rect.right, semantics.rect.right);
                    const overlapBottom = Math.min(rect.bottom, semantics.rect.bottom);
                    const overlapWidth = Math.max(0, overlapRight - overlapLeft);
                    const overlapHeight = Math.max(0, overlapBottom - overlapTop);
                    const overlapArea = overlapWidth * overlapHeight;
                    const area = Math.max(rect.width, 0) * Math.max(rect.height, 0);
                    const containsCenter =
                      rect.left <= centerX
                      && rect.right >= centerX
                      && rect.top <= centerY
                      && rect.bottom >= centerY;
                    const containsSemantics =
                      rect.left <= semantics.rect.left + 1
                      && rect.top <= semantics.rect.top + 1
                      && rect.right >= semantics.rect.right - 1
                      && rect.bottom >= semantics.rect.bottom - 1;
                    const insetPenalty =
                      Math.abs(rect.left - semantics.rect.left)
                      + Math.abs(rect.top - semantics.rect.top)
                      + Math.abs(rect.right - semantics.rect.right)
                      + Math.abs(rect.bottom - semantics.rect.bottom);
                    return {
                      styles,
                      area,
                      overlapArea,
                      containsCenter,
                      containsSemantics,
                      insetPenalty,
                    };
                  })
                  .filter((candidate) => candidate && candidate.overlapArea > 0 && candidate.containsCenter)
                  .sort((left, right) => {
                    if (left.containsSemantics !== right.containsSemantics) {
                      return left.containsSemantics ? -1 : 1;
                    }
                    if (left.overlapArea !== right.overlapArea) {
                      return right.overlapArea - left.overlapArea;
                    }
                    if (left.area !== right.area) {
                      return left.area - right.area;
                    }
                    return left.insetPenalty - right.insetPenalty;
                  });
                if (styledCandidates.length > 0) {
                  const { rect, ...styles } = styledCandidates[0].styles;
                  return styles;
                }
                return {
                  borderColor: null,
                  backgroundColor: null,
                  borderWidth: null,
                };
              };
              const findRepositoryAccessSection = () => {
                const sectionCandidates = Array.from(document.querySelectorAll('flt-semantics'))
                  .filter((candidate) => isVisible(candidate))
                  .map((candidate) => {
                    const rect = candidate.getBoundingClientRect();
                    const label = candidate.getAttribute('aria-label') ?? '';
                    const text = normalize(candidate.innerText ?? '');
                    return {
                      element: candidate,
                      rect,
                      area: rect.width * rect.height,
                      normalizedLabel: normalize(label),
                      normalizedText: text,
                    };
                  })
                  .filter((candidate) =>
                    candidate.normalizedText.includes('Connect token')
                    && candidate.normalizedText.includes('Local Git'),
                  )
                  .sort((left, right) => left.area - right.area);
                return sectionCandidates.find((candidate) => {
                  const semantics = collectSemantics(candidate.element);
                  return semantics.some((entry) => matchesCallout(entry, primaryTitle))
                    && semantics.some((entry) => matchesCallout(entry, secondaryTitle));
                }) ?? null;
              };
              const section = findRepositoryAccessSection();
              if (!section) {
                return null;
              }
              const sectionSemantics = collectSemantics(section.element);
              const findCallout = (title) => {
                const semanticsCandidates = sectionSemantics
                  .filter((candidate) => matchesCallout(candidate, title))
                  .sort((left, right) => left.area - right.area);
                const semantics = semanticsCandidates[0];
                if (!semantics) {
                  return null;
                }

                const visibleStyles = findStyledElement(semantics);

                const renderedLines = semantics.label
                  .split('\\n')
                  .map((line) => normalize(line))
                  .filter((line) => line.length > 0);
                const renderedTitle =
                  renderedLines.find((line) => line === title || line.startsWith(title))
                  ?? title;
                const nonTitleLines = renderedLines.filter((line) => line !== renderedTitle);
                const message = nonTitleLines.length > 0
                  ? nonTitleLines[nonTitleLines.length - 1]
                  : '';
                return {
                  title: renderedTitle,
                  message,
                  renderedText: normalize([renderedTitle, message].join(' ')),
                  semanticLabel: semantics.normalizedLabel,
                  borderColor: visibleStyles.borderColor,
                  backgroundColor: visibleStyles.backgroundColor,
                  borderWidth: visibleStyles.borderWidth,
                  top: semantics.rect.top,
                  left: semantics.rect.left,
                  width: semantics.rect.width,
                  height: semantics.rect.height,
                };
              };

              const primaryCallout = findCallout(primaryTitle);
              const secondaryCallout = findCallout(secondaryTitle);
              if (!primaryCallout || !secondaryCallout) {
                return null;
              }

              return {
                bodyText: document.body?.innerText ?? '',
                sectionText: [
                  section.normalizedLabel,
                  ...sectionSemantics.map((value) => value.normalizedLabel),
                ]
                  .filter((value, index, values) => value.length > 0 && values.indexOf(value) === index)
                  .join('\\n'),
                primaryCallout,
                secondaryCallout,
              };
            }
            """,
            arg={
                "primaryTitle": primary_title,
                "secondaryTitle": secondary_title,
            },
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The Repository access section did not expose the expected connected "
                "and GitHub Releases callouts.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        primary_payload = payload.get("primaryCallout")
        secondary_payload = payload.get("secondaryCallout")
        if not isinstance(primary_payload, dict) or not isinstance(secondary_payload, dict):
            raise AssertionError(
                "The Repository access section did not expose readable callout observations.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return RepositoryAccessSectionObservation(
            body_text=str(payload.get("bodyText", "")),
            section_text=str(payload.get("sectionText", "")),
            primary_callout=self._repository_access_callout(primary_payload),
            secondary_callout=self._repository_access_callout(secondary_payload),
        )

    def observe_saved_configuration(
        self,
        *,
        status_name: str,
        workflow_name: str,
        transition_name: str,
        transition_index: int,
    ) -> ProjectSettingsUiObservation:
        settings_text = self.open_settings()
        status_dialog_text, status_list_text = self.add_status(
            status_id=f"{status_name.lower().replace(' ', '-')}",
            status_name=status_name,
        )
        workflow_tab_text = self.open_workflows_tab()
        workflow_dialog_text, workflow_tab_text = self.update_workflow_transition_name(
            workflow_name=workflow_name,
            transition_index=transition_index,
            transition_name=transition_name,
        )
        post_save_text = self.save_settings()
        return ProjectSettingsUiObservation(
            settings_text=settings_text,
            status_dialog_text=status_dialog_text,
            status_list_text=status_list_text,
            workflow_dialog_text=workflow_dialog_text,
            workflow_tab_text=workflow_tab_text,
            post_save_text=post_save_text,
        )

    def _wait_for_visible_text(self, text: str, *, timeout_seconds: int) -> str:
        try:
            return self._session.wait_for_text(text, timeout_ms=timeout_seconds * 1_000)
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Human-style verification failed: the live Settings surface never '
                f'showed "{text}" after saving the dialog.\n'
                f"Observed body text:\n{self.body_text()}",
            ) from error

    def _wait_for_semantics_text(self, text: str, *, timeout_seconds: int) -> str:
        try:
            self._session.wait_for_function(
                """
                (expectedText) => Array.from(document.querySelectorAll("flt-semantics"))
                  .some((element) => {
                    const aria = element.getAttribute("aria-label") ?? "";
                    const innerText = element.innerText ?? "";
                    return aria.includes(expectedText) || innerText.includes(expectedText);
                  })
                """,
                arg=text,
                timeout_ms=timeout_seconds * 1_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Human-style verification failed: the live Settings semantics never '
                f'exposed "{text}" after saving the dialog.\n'
                f"Observed body text:\n{self.body_text()}",
            ) from error
        return self.body_text()

    def _scroll_into_view(self, selector: str) -> None:
        self._session.evaluate(
            """
            (selector) => {
              const element = document.querySelector(selector);
              if (element) {
                element.scrollIntoView({ block: 'center', inline: 'center' });
              }
            }
            """,
            arg=selector,
        )

    def _tab_selector_for(self, label: str) -> str:
        return f'{self._tab_selector}[aria-label="{self._escape(label)}"]'

    @staticmethod
    def _repository_access_callout(
        payload: dict[str, object],
    ) -> RepositoryAccessCalloutObservation:
        return RepositoryAccessCalloutObservation(
            title=str(payload.get("title", "")).strip(),
            message=str(payload.get("message", "")).strip(),
            rendered_text=str(payload.get("renderedText", "")).strip(),
            semantic_label=str(payload.get("semanticLabel", "")).strip(),
            border_color=(
                str(payload["borderColor"]).strip()
                if payload.get("borderColor") is not None
                else None
            ),
            background_color=(
                str(payload["backgroundColor"]).strip()
                if payload.get("backgroundColor") is not None
                else None
            ),
            border_width=(
                str(payload["borderWidth"]).strip()
                if payload.get("borderWidth") is not None
                else None
            ),
            top=float(payload.get("top", 0)),
            left=float(payload.get("left", 0)),
            width=float(payload.get("width", 0)),
            height=float(payload.get("height", 0)),
        )

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
