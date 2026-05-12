from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class CreateIssueGateObservation:
    body_text: str
    gate_panel_text: str
    callout_semantics_label: str
    create_heading_visible: bool
    summary_field_count: int
    create_button_count: int
    save_button_count: int
    open_settings_button_count: int
    gate_open_settings_button_count: int
    gate_cta_center_x: float | None
    gate_cta_center_y: float | None


class LiveCreateIssueGatePage:
    _button_selector = 'flt-semantics[role="button"]'

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
        primary_action_label: str,
        timeout_ms: int = 60_000,
    ) -> CreateIssueGateObservation:
        self._session.wait_for_function(
            """
            ({ actionLabel }) => {
              const createLabel = 'Create issue';
              const normalize = (value) => value.replace(/\\s+/g, ' ').trim();
              const bodyText = document.body?.innerText ?? '';
              const isVisible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const elementText = (element) => normalize(
                [
                  element.getAttribute('aria-label') ?? '',
                  element.innerText ?? '',
                ].join(' '),
              );
              const pointInRect = (x, y, rect) =>
                x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
              const buttons = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter((candidate) => {
                  const text = elementText(candidate);
                  return isVisible(candidate) && text.includes(actionLabel);
                })
                .map((candidate) => {
                  const rect = candidate.getBoundingClientRect();
                  return {
                    centerX: rect.left + (rect.width / 2),
                    centerY: rect.top + (rect.height / 2),
                  };
                });
              const containers = Array.from(document.querySelectorAll('flt-semantics'))
                .filter((candidate) => {
                  if (!isVisible(candidate)) {
                    return false;
                  }
                  const text = elementText(candidate);
                  return text.includes(createLabel)
                    && text.includes(actionLabel)
                    && text.length > (createLabel.length + actionLabel.length + 8);
                })
                .map((candidate) => {
                  const rect = candidate.getBoundingClientRect();
                  return {
                    area: rect.width * rect.height,
                    left: rect.left,
                    right: rect.right,
                    top: rect.top,
                    bottom: rect.bottom,
                  };
                })
                .sort((left, right) => left.area - right.area);
              const gateButton = buttons.find((button) =>
                containers.some((container) =>
                  pointInRect(button.centerX, button.centerY, container),
                ),
              );
              return bodyText.includes(createLabel) && !!gateButton;
            }
            """,
            arg={"actionLabel": primary_action_label},
            timeout_ms=timeout_ms,
        )
        return self.observe_access_gate(primary_action_label=primary_action_label)

    def observe_access_gate(
        self,
        *,
        primary_action_label: str,
    ) -> CreateIssueGateObservation:
        payload = self._session.evaluate(
            """
            ({ actionLabel }) => {
              const createLabel = 'Create issue';
              const normalize = (value) => value.replace(/\\s+/g, ' ').trim();
              const bodyText = document.body?.innerText ?? '';
              const isVisible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const elementText = (element) => normalize(
                [
                  element.getAttribute('aria-label') ?? '',
                  element.innerText ?? '',
                ].join(' '),
              );
              const pointInRect = (x, y, rect) =>
                x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
              const buttonCount = (label) => Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              ).filter((candidate) => {
                const text = elementText(candidate);
                return isVisible(candidate) && text.includes(label);
              }).length;
              const buttons = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter((candidate) => {
                  const text = elementText(candidate);
                  return isVisible(candidate) && text.includes(actionLabel);
                })
                .map((candidate) => {
                  const rect = candidate.getBoundingClientRect();
                  return {
                    centerX: rect.left + (rect.width / 2),
                    centerY: rect.top + (rect.height / 2),
                  };
                });
              const containers = Array.from(document.querySelectorAll('flt-semantics'))
                .filter((candidate) => {
                  if (!isVisible(candidate)) {
                    return false;
                  }
                  const text = elementText(candidate);
                  return text.includes(createLabel)
                    && text.includes(actionLabel)
                    && text.length > (createLabel.length + actionLabel.length + 8);
                })
                .map((candidate) => {
                  const text = elementText(candidate);
                  const rect = candidate.getBoundingClientRect();
                  return {
                    area: rect.width * rect.height,
                    left: rect.left,
                    right: rect.right,
                    top: rect.top,
                    bottom: rect.bottom,
                    label: candidate.getAttribute('aria-label') ?? '',
                    text,
                  };
                })
                .sort((left, right) => left.area - right.area);
              const gateMatch = buttons
                .map((button) => {
                  const container = containers.find((candidate) =>
                    pointInRect(button.centerX, button.centerY, candidate),
                  );
                  if (!container) {
                    return null;
                  }
                  return {
                    centerX: button.centerX,
                    centerY: button.centerY,
                    container,
                  };
                })
                .find((candidate) => candidate !== null);
              const gateContainer = gateMatch?.container ?? null;
              const gateOpenSettingsButtonCount = gateContainer
                ? buttons.filter((button) =>
                    pointInRect(button.centerX, button.centerY, gateContainer),
                  ).length
                : 0;
              return {
                bodyText,
                gatePanelText: gateContainer?.text ?? '',
                calloutSemanticsLabel: gateContainer?.label ?? '',
                createHeadingVisible: bodyText.includes(createLabel),
                summaryFieldCount: document.querySelectorAll('input[aria-label="Summary"]').length,
                createButtonCount: buttonCount('Create'),
                saveButtonCount: buttonCount('Save'),
                openSettingsButtonCount: buttonCount(actionLabel),
                gateOpenSettingsButtonCount,
                gateCtaCenterX: gateMatch?.centerX ?? null,
                gateCtaCenterY: gateMatch?.centerY ?? null,
              };
            }
            """,
            arg={"actionLabel": primary_action_label},
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The create issue gate surface did not expose a readable DOM snapshot.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return CreateIssueGateObservation(
            body_text=str(payload["bodyText"]),
            gate_panel_text=str(payload["gatePanelText"]),
            callout_semantics_label=str(payload["calloutSemanticsLabel"]),
            create_heading_visible=bool(payload["createHeadingVisible"]),
            summary_field_count=int(payload["summaryFieldCount"]),
            create_button_count=int(payload["createButtonCount"]),
            save_button_count=int(payload["saveButtonCount"]),
            open_settings_button_count=int(payload["openSettingsButtonCount"]),
            gate_open_settings_button_count=int(payload["gateOpenSettingsButtonCount"]),
            gate_cta_center_x=(
                float(payload["gateCtaCenterX"]) if payload["gateCtaCenterX"] is not None else None
            ),
            gate_cta_center_y=(
                float(payload["gateCtaCenterY"]) if payload["gateCtaCenterY"] is not None else None
            ),
        )

    def open_settings_from_gate(
        self,
        gate: CreateIssueGateObservation,
        *,
        timeout_ms: int = 60_000,
    ) -> str:
        if gate.gate_cta_center_x is None or gate.gate_cta_center_y is None:
            raise AssertionError(
                "Step 5 failed: the create issue gate did not expose a clickable "
                "`Open settings` recovery action.\n"
                f"Observed gate text:\n{gate.gate_panel_text}\n\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        self._session.mouse_click(gate.gate_cta_center_x, gate.gate_cta_center_y)
        settings_snapshot = self._session.wait_for_function(
            """
            (requiredFragments) => {
              const snapshot = Array.from(document.querySelectorAll('flt-semantics'))
                .flatMap((element) => [
                  element.getAttribute('aria-label') ?? '',
                  element.innerText ?? '',
                ])
                .map((value) => value.trim())
                .filter((value) => value.length > 0)
                .join('\\n');
              return requiredFragments.every((fragment) => snapshot.includes(fragment))
                ? snapshot
                : null;
            }
            """,
            arg=["Project Settings", "Repository access"],
            timeout_ms=timeout_ms,
        )
        return str(settings_snapshot)

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)
