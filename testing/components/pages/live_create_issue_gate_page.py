from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class CreateIssueGateObservation:
    body_text: str
    callout_semantics_label: str
    create_heading_visible: bool
    summary_field_count: int
    create_button_count: int
    save_button_count: int
    open_settings_button_count: int


class LiveCreateIssueGatePage:
    _button_selector = 'flt-semantics[role="button"]'
    _summary_selector = 'input[aria-label="Summary"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def wait_for_create_trigger(self, *, timeout_ms: int = 60_000) -> str:
        self._session.wait_for_selector(
            self._button_selector,
            has_text=TrackStateTrackerPage.CREATE_ISSUE_LABEL,
            timeout_ms=timeout_ms,
        )
        return self.current_body_text()

    def open_create_issue(self, *, timeout_ms: int = 60_000) -> str:
        self._session.click(
            self._button_selector,
            has_text=TrackStateTrackerPage.CREATE_ISSUE_LABEL,
            timeout_ms=timeout_ms,
        )
        try:
            self._session.wait_for_text(TrackStateTrackerPage.CREATE_ISSUE_LABEL, timeout_ms=timeout_ms)
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 2 failed: clicking the visible `Create issue` trigger did not route "
                "the user to any production-visible create surface.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        return self.current_body_text()

    def wait_for_access_gate(
        self,
        *,
        title: str,
        message: str,
        primary_action_label: str,
        timeout_ms: int = 60_000,
    ) -> CreateIssueGateObservation:
        self._session.wait_for_function(
            """
            ({ title, message, actionLabel }) => {
              const bodyText = document.body?.innerText ?? '';
              const callout = Array.from(document.querySelectorAll('flt-semantics')).find(
                (candidate) => {
                  const label = candidate.getAttribute('aria-label') ?? '';
                  return label.includes('Create issue')
                    && label.includes(title)
                    && label.includes(message);
                },
              );
              const actionCount = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              ).filter((candidate) => {
                const label = candidate.getAttribute('aria-label') ?? '';
                const text = candidate.innerText ?? '';
                return label.includes(actionLabel) || text.includes(actionLabel);
              }).length;
              return bodyText.includes('Create issue') && callout && actionCount > 0;
            }
            """,
            arg={
                "title": title,
                "message": message,
                "actionLabel": primary_action_label,
            },
            timeout_ms=timeout_ms,
        )
        return self.observe_access_gate(title=title, message=message, primary_action_label=primary_action_label)

    def observe_access_gate(
        self,
        *,
        title: str,
        message: str,
        primary_action_label: str,
    ) -> CreateIssueGateObservation:
        payload = self._session.evaluate(
            """
            ({ title, message, actionLabel }) => {
              const bodyText = document.body?.innerText ?? '';
              const callout = Array.from(document.querySelectorAll('flt-semantics')).find(
                (candidate) => {
                  const label = candidate.getAttribute('aria-label') ?? '';
                  return label.includes('Create issue')
                    && label.includes(title)
                    && label.includes(message);
                },
              );
              const buttonCount = (label) => Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              ).filter((candidate) => {
                const ariaLabel = candidate.getAttribute('aria-label') ?? '';
                const text = candidate.innerText ?? '';
                return ariaLabel.includes(label) || text.includes(label);
              }).length;
              return {
                bodyText,
                calloutSemanticsLabel: callout?.getAttribute('aria-label') ?? '',
                createHeadingVisible: bodyText.includes('Create issue'),
                summaryFieldCount: document.querySelectorAll('input[aria-label="Summary"]').length,
                createButtonCount: buttonCount('Create'),
                saveButtonCount: buttonCount('Save'),
                openSettingsButtonCount: buttonCount(actionLabel),
              };
            }
            """,
            arg={
                "title": title,
                "message": message,
                "actionLabel": primary_action_label,
            },
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The create issue gate surface did not expose a readable DOM snapshot.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return CreateIssueGateObservation(
            body_text=str(payload["bodyText"]),
            callout_semantics_label=str(payload["calloutSemanticsLabel"]),
            create_heading_visible=bool(payload["createHeadingVisible"]),
            summary_field_count=int(payload["summaryFieldCount"]),
            create_button_count=int(payload["createButtonCount"]),
            save_button_count=int(payload["saveButtonCount"]),
            open_settings_button_count=int(payload["openSettingsButtonCount"]),
        )

    def open_settings_from_gate(self, *, timeout_ms: int = 60_000) -> str:
        self._session.click(
            self._button_selector,
            has_text="Open settings",
            timeout_ms=timeout_ms,
        )
        self._session.wait_for_function(
            """
            () => {
              const bodyText = document.body?.innerText ?? '';
              return bodyText.includes('Project Settings')
                && bodyText.includes('Repository access');
            }
            """,
            timeout=timeout_ms,
        )
        return self.current_body_text()

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)
