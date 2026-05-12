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


class LiveProjectSettingsPage:
    _button_selector = 'flt-semantics[role="button"]'
    _tab_selector = 'flt-semantics[role="tab"]'
    _connect_selector = 'flt-semantics[aria-label="Connect GitHub"]'
    _token_input_selector = 'input[aria-label="Fine-grained token"]'
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
              const findCallout = (title) => {
                const semanticsCandidates = Array.from(
                  document.querySelectorAll('flt-semantics[aria-label]'),
                )
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
                  })
                  .filter((candidate) =>
                    candidate.normalizedLabel.includes(title)
                    && candidate.normalizedLabel.length > title.length + 20,
                  )
                  .sort((left, right) => left.area - right.area);
                const semantics = semanticsCandidates[0];
                if (!semantics) {
                  return null;
                }

                let styled = semantics.element;
                let borderColor = null;
                let backgroundColor = null;
                let borderWidth = null;
                while (styled && styled !== document.body) {
                  const style = window.getComputedStyle(styled);
                  const hasVisibleBorder =
                    Number.parseFloat(style.borderTopWidth || '0') > 0
                    && style.borderTopColor !== 'transparent'
                    && style.borderTopColor !== 'rgba(0, 0, 0, 0)';
                  const hasVisibleBackground =
                    style.backgroundColor !== 'transparent'
                    && style.backgroundColor !== 'rgba(0, 0, 0, 0)';
                  if (hasVisibleBorder || hasVisibleBackground) {
                    borderColor = style.borderTopColor || null;
                    backgroundColor = style.backgroundColor || null;
                    borderWidth = style.borderTopWidth || null;
                    break;
                  }
                  styled = styled.parentElement;
                }

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
                  borderColor,
                  backgroundColor,
                  borderWidth,
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
                sectionText: [primaryCallout.semanticLabel, secondaryCallout.semanticLabel]
                  .filter((value) => value.length > 0)
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
