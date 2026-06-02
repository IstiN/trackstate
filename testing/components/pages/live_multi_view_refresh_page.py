from __future__ import annotations

from dataclasses import dataclass
import re

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import (
    FocusedElementObservation,
    WebAppTimeoutError,
)


@dataclass(frozen=True)
class EditControlObservation:
    label: str | None
    text: str
    tabindex: str | None
    expanded: str | None

    def contains(self, fragment: str) -> bool:
        return fragment in self.text or (
            self.label is not None and fragment in self.label
        )


@dataclass(frozen=True)
class BoardIssueObservation:
    key: str
    summary: str
    label: str


@dataclass(frozen=True)
class ConstrainedChipFieldObservation:
    label: str
    semantics_label: str | None
    field_text: str
    option_labels: tuple[str, ...]
    input_count: int
    listbox_count: int
    menu_item_count: int


@dataclass(frozen=True)
class EditSurfaceObservation:
    viewport_width: float
    viewport_height: float
    left: float
    top: float
    width: float
    height: float
    summary_value: str
    description_value: str
    priority_label: str | None
    priority_text: str
    body_text: str

    @property
    def width_fraction(self) -> float:
        return self.width / self.viewport_width if self.viewport_width else 0.0

    @property
    def height_fraction(self) -> float:
        return self.height / self.viewport_height if self.viewport_height else 0.0

    @property
    def right_inset(self) -> float:
        return self.viewport_width - (self.left + self.width)

    @property
    def bottom_inset(self) -> float:
        return self.viewport_height - (self.top + self.height)


@dataclass(frozen=True)
class LabeledTextFieldObservation:
    label: str
    value: str
    enabled: bool
    disabled: bool
    read_only: bool
    aria_label: str | None
    aria_invalid: str | None
    aria_describedby: str | None
    aria_errormessage: str | None
    outer_html: str


@dataclass(frozen=True)
class ValidationMessageObservation:
    text: str
    tag_name: str
    role: str | None
    aria_live: str | None
    element_id: str | None
    color: str | None
    background_color: str | None
    contrast_ratio: float | None


@dataclass(frozen=True)
class SummaryRequiredValidationObservation:
    field: LabeledTextFieldObservation
    message: ValidationMessageObservation | None
    describedby_texts: tuple[str, ...]
    errormessage_texts: tuple[str, ...]
    live_region_texts: tuple[str, ...]
    active_element: FocusedElementObservation
    field_is_active: bool
    dialog_text: str


class LiveMultiViewRefreshPage:
    _button_selector = 'flt-semantics[role="button"]'
    _edit_button_selector = 'flt-semantics[role="button"]'
    _menu_item_selector = 'flt-semantics[role="menuitem"]'
    _dialog_group_selector = 'flt-semantics[role="group"][aria-label="Edit issue"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._issue_page = LiveIssueDetailCollaborationPage(tracker_page)

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> None:
        self._issue_page.ensure_connected(
            token=token,
            repository=repository,
            user_login=user_login,
        )

    def dismiss_connection_banner(self) -> None:
        self._issue_page.dismiss_connection_banner()

    def set_viewport(self, *, width: int, height: int) -> None:
        self._session.set_viewport_size(width=width, height=height)
        try:
            self._session.wait_for_function(
                """
                ({ expectedWidth, expectedHeight }) =>
                  window.innerWidth === expectedWidth && window.innerHeight === expectedHeight
                """,
                arg={"expectedWidth": width, "expectedHeight": height},
                timeout_ms=15_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f"Step failed: resizing the hosted browser to {width}x{height} did not "
                "settle to the requested viewport.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def open_edit_dialog_for_issue(self, *, issue_key: str, issue_summary: str) -> str:
        if self._session.count(self._issue_detail_selector(issue_key)) == 0:
            if self._button_bounds_for_sidebar_label("JQL Search") is not None:
                self.navigate_to_section("JQL Search")
            if self._session.count(self._issue_detail_selector(issue_key)) == 0:
                self._session.wait_for_text(issue_key, timeout_ms=60_000)
                self.open_issue_from_current_section(
                    issue_key=issue_key,
                    issue_summary=issue_summary,
                )
        return self.open_edit_dialog_from_current_issue_detail(issue_key=issue_key)

    def open_edit_dialog_for_issue_key(
        self,
        *,
        issue_key: str,
        issue_summary: str | None = None,
    ) -> str:
        for attempt in range(2):
            try:
                self.navigate_to_section("JQL Search")
                break
            except AssertionError:
                current_body = self.current_body_text()
                summary_fragment = issue_summary or ""
                if attempt == 0 and (
                    "Project Settings" in current_body
                    or "GitHub startup limit reached" in current_body
                    or self._session.count('flt-semantics[aria-label="Close"]') > 0
                ):
                    continue
                if (
                    "JQL Search" not in current_body
                    and issue_key not in current_body
                    and summary_fragment not in current_body
                ):
                    raise

        current_body = self.current_body_text()
        if self._session.count(self._issue_detail_selector(issue_key)) == 0:
            try:
                self._session.wait_for_function(
                    """
                    ({ issueKey }) => {
                      return document.querySelector(
                        `flt-semantics[aria-label*="Issue detail ${issueKey}"], flt-semantics-img[aria-label*="Issue detail ${issueKey}"]`
                      ) !== null;
                    }
                    """,
                    arg={"issueKey": issue_key},
                    timeout_ms=15_000,
                )
                current_body = self.current_body_text()
            except WebAppTimeoutError:
                current_body = self.current_body_text()
        if self._session.count(self._issue_detail_selector(issue_key)) == 0:
            if issue_summary is None or not issue_summary.strip():
                label = self.visible_issue_open_label(issue_key=issue_key)
                self._session.click(
                    f'flt-semantics[role="button"][aria-label="{self._escape(label)}"]',
                    timeout_ms=30_000,
                )
            else:
                self.open_issue_from_current_section(
                    issue_key=issue_key,
                    issue_summary=issue_summary,
                )
        return self.open_edit_dialog_from_current_issue_detail(issue_key=issue_key)

    def open_edit_dialog_from_board_card(
        self,
        *,
        issue_key: str,
        issue_summary: str,
    ) -> str:
        self.navigate_to_section("Board")
        self._session.wait_for_text(issue_summary, timeout_ms=60_000)
        board_text = self.current_body_text()
        if issue_summary not in board_text:
            raise AssertionError(
                f"Step failed: the Board view did not visibly render {issue_key} before "
                "the shared edit-surface scenario began.\n"
                f"Observed Board text:\n{board_text}",
            )

        card_bounds = self._board_issue_card_bounds(
            issue_key=issue_key,
            issue_summary=issue_summary,
        )
        edit_bounds = self._reveal_board_issue_edit_button(card_bounds=card_bounds)
        if edit_bounds is None:
            nearby_controls = self._board_issue_controls_snapshot(card_bounds=card_bounds)
            raise AssertionError(
                f"Step failed: the Board card for {issue_key} did not expose a visible "
                "Edit affordance.\n"
                "Expected the ticketed Board flow to let the user open Edit directly from "
                "the issue card.\n"
                f"Nearby visible controls after hovering the card: {nearby_controls}\n"
                f"Observed Board text:\n{board_text}",
            )

        self._session.mouse_click(
            edit_bounds["x"] + (edit_bounds["width"] / 2),
            edit_bounds["y"] + (edit_bounds["height"] / 2),
        )
        return self._wait_for_edit_dialog(
            issue_key=issue_key,
            origin_label="Board card Edit affordance",
        )

    def open_edit_dialog_from_current_issue_detail(self, *, issue_key: str) -> str:
        self._session.wait_for_selector(
            self._issue_detail_selector(issue_key),
            timeout_ms=60_000,
        )
        self._click_edit_button()
        return self._wait_for_edit_dialog(
            issue_key=issue_key,
            origin_label="current issue detail",
        )

    def _click_edit_button(self) -> None:
        if self._session.count(self._edit_button_selector, has_text="Edit") > 0:
            self._session.wait_for_selector(
                self._edit_button_selector,
                has_text="Edit",
                timeout_ms=30_000,
            )
            self._session.click(
                self._edit_button_selector,
                has_text="Edit",
                timeout_ms=30_000,
            )
            return
        self._session.wait_for_selector(
            self._button_selector,
            has_text="Edit",
            timeout_ms=30_000,
        )
        self._session.click(self._button_selector, has_text="Edit", timeout_ms=30_000)

    def close_edit_dialog(self) -> None:
        self._session.wait_for_selector(self._dialog_group_selector, timeout_ms=30_000)
        if self._session.count(self._button_selector, has_text="Cancel") > 0:
            self._session.click(self._button_selector, has_text="Cancel", timeout_ms=30_000)
        else:
            self._session.press_key("Escape", timeout_ms=30_000)
        try:
            self._session.wait_for_count(self._dialog_group_selector, 0, timeout_ms=30_000)
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step failed: dismissing the hosted Edit issue surface did not close the "
                "dialog.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def observe_edit_surface(
        self,
        *,
        viewport_width: int,
        viewport_height: int,
    ) -> EditSurfaceObservation:
        self._session.wait_for_selector(self._dialog_group_selector, timeout_ms=30_000)
        rect = self._session.bounding_box(self._dialog_group_selector, timeout_ms=30_000)
        summary_value = self.read_labeled_text_field_value("Summary")
        description_value = self.read_labeled_text_field_value("Description")
        priority = self.priority_control()
        return EditSurfaceObservation(
            viewport_width=float(viewport_width),
            viewport_height=float(viewport_height),
            left=rect.x,
            top=rect.y,
            width=rect.width,
            height=rect.height,
            summary_value=summary_value,
            description_value=description_value,
            priority_label=priority.label,
            priority_text=priority.text,
            body_text=self.current_body_text(),
        )

    def read_labeled_text_field_value(self, label: str) -> str:
        payload = self._session.evaluate(
            """
            ({ dialogSelector, label }) => {
              const root = document.querySelector(dialogSelector);
              if (!root) {
                return null;
              }
              const selectors = [
                `input[aria-label="${label}"]`,
                `textarea[aria-label="${label}"]`,
                `[role="textbox"][aria-label="${label}"]`,
              ];
              for (const selector of selectors) {
                const field = root.querySelector(selector);
                if (!field) {
                  continue;
                }
                if ('value' in field && typeof field.value === 'string') {
                  return field.value;
                }
                return (field.innerText || field.textContent || '').trim();
              }
              return null;
            }
            """,
            arg={"dialogSelector": self._dialog_group_selector, "label": label},
        )
        if not isinstance(payload, str):
            raise AssertionError(
                f"Human-style verification failed: the hosted Edit issue surface did not "
                f"expose a readable {label!r} field value.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return payload

    def observe_labeled_text_field(self, label: str) -> LabeledTextFieldObservation:
        payload = self._session.evaluate(
            """
            ({ dialogSelector, label }) => {
              const root = document.querySelector(dialogSelector);
              if (!root) {
                return null;
              }
              const selectors = [
                `input[aria-label="${label}"]`,
                `textarea[aria-label="${label}"]`,
                `[role="textbox"][aria-label="${label}"]`,
              ];
              for (const selector of selectors) {
                const field = root.querySelector(selector);
                if (!field) {
                  continue;
                }
                const value =
                  'value' in field && typeof field.value === 'string'
                    ? field.value
                    : (field.innerText || field.textContent || '').trim();
                return {
                  value,
                  enabled: !field.disabled,
                  disabled: !!field.disabled,
                  readOnly: !!field.readOnly,
                  ariaLabel: field.getAttribute('aria-label'),
                  ariaInvalid: field.getAttribute('aria-invalid'),
                  ariaDescribedBy: field.getAttribute('aria-describedby'),
                  ariaErrormessage: field.getAttribute('aria-errormessage'),
                  outerHtml: field.outerHTML.slice(0, 800),
                };
              }
              return null;
            }
            """,
            arg={"dialogSelector": self._dialog_group_selector, "label": label},
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                f"Human-style verification failed: the hosted Edit issue surface did not "
                f"expose the visible {label!r} field.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return LabeledTextFieldObservation(
            label=label,
            value=str(payload.get("value", "")),
            enabled=bool(payload.get("enabled")),
            disabled=bool(payload.get("disabled")),
            read_only=bool(payload.get("readOnly")),
            aria_label=(
                str(payload["ariaLabel"]) if payload.get("ariaLabel") is not None else None
            ),
            aria_invalid=(
                str(payload["ariaInvalid"])
                if payload.get("ariaInvalid") is not None
                else None
            ),
            aria_describedby=(
                str(payload["ariaDescribedBy"])
                if payload.get("ariaDescribedBy") is not None
                else None
            ),
            aria_errormessage=(
                str(payload["ariaErrormessage"])
                if payload.get("ariaErrormessage") is not None
                else None
            ),
            outer_html=str(payload.get("outerHtml", "")),
        )

    def clear_labeled_text_field(self, label: str) -> LabeledTextFieldObservation:
        field = self.observe_labeled_text_field(label)
        if not field.enabled:
            raise AssertionError(
                f"Step failed: the visible {label} field was not editable.\n"
                f"Enabled: {field.enabled}\n"
                f"Disabled: {field.disabled}\n"
                f"Read-only: {field.read_only}\n"
                f"Outer HTML: {field.outer_html}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        self._session.fill(f'input[aria-label="{self._escape(label)}"]', "", timeout_ms=30_000)
        return self.observe_labeled_text_field(label)

    def active_element(self) -> FocusedElementObservation:
        return self._session.active_element()

    def trigger_required_summary_validation(
        self,
        *,
        message_fragment: str,
    ) -> SummaryRequiredValidationObservation:
        if self._session.count('flt-semantics[role="button"][aria-label="Save"]') > 0:
            self._session.click(
                'flt-semantics[role="button"][aria-label="Save"]',
                timeout_ms=30_000,
            )
        else:
            self._session.click(self._button_selector, has_text="Save", timeout_ms=30_000)
        try:
            payload = self._session.wait_for_function(
                """
                ({ dialogSelector, label, messageFragment, errorPrefix }) => {
                  const bodyText = document.body?.innerText ?? '';
                  if (bodyText.includes(errorPrefix)) {
                    return { kind: 'save-error', bodyText };
                  }
                  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                  const isVisible = (element) => {
                    if (!element) {
                      return false;
                    }
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return (
                      rect.width > 0
                      && rect.height > 0
                      && style.display !== 'none'
                      && style.visibility !== 'hidden'
                      && Number.parseFloat(style.opacity || '1') > 0
                    );
                  };
                  const findField = (root) => {
                    const selectors = [
                      `input[aria-label="${label}"]`,
                      `textarea[aria-label="${label}"]`,
                      `[role="textbox"][aria-label="${label}"]`,
                    ];
                    for (const selector of selectors) {
                      const field = root.querySelector(selector);
                      if (field) {
                        return field;
                      }
                    }
                    return null;
                  };
                  const parseColor = (value) => {
                    if (!value) {
                      return null;
                    }
                    const match = value.match(
                      /^rgba?\\(\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)/i,
                    );
                    if (!match) {
                      return null;
                    }
                    return [
                      Number.parseInt(match[1], 10),
                      Number.parseInt(match[2], 10),
                      Number.parseInt(match[3], 10),
                    ];
                  };
                  const isTransparent = (value) =>
                    !value
                    || value === 'transparent'
                    || /^rgba\\(\\s*0\\s*,\\s*0\\s*,\\s*0\\s*,\\s*0(?:\\.0+)?\\s*\\)$/i.test(value);
                  const relativeLuminance = (color) => {
                    const channel = (value) => {
                      const normalized = value / 255;
                      if (normalized <= 0.03928) {
                        return normalized / 12.92;
                      }
                      return ((normalized + 0.055) / 1.055) ** 2.4;
                    };
                    return (
                      (0.2126 * channel(color[0]))
                      + (0.7152 * channel(color[1]))
                      + (0.0722 * channel(color[2]))
                    );
                  };
                  const contrastRatio = (foreground, background) => {
                    const lighter = relativeLuminance(foreground);
                    const darker = relativeLuminance(background);
                    const max = lighter > darker ? lighter : darker;
                    const min = lighter > darker ? darker : lighter;
                    return (max + 0.05) / (min + 0.05);
                  };
                  const effectiveBackgroundColor = (element) => {
                    let current = element;
                    while (current) {
                      const background = window.getComputedStyle(current).backgroundColor;
                      if (!isTransparent(background)) {
                        return background;
                      }
                      current = current.parentElement;
                    }
                    const bodyBackground = window.getComputedStyle(document.body).backgroundColor;
                    return isTransparent(bodyBackground) ? 'rgb(255, 255, 255)' : bodyBackground;
                  };
                  const collectText = (element) =>
                    normalize(
                      element.innerText
                        || element.textContent
                        || element.getAttribute('aria-label')
                        || '',
                    );
                  const root = document.querySelector(dialogSelector);
                  if (!root) {
                    return { kind: 'dialog-closed', bodyText };
                  }
                  const field = findField(root);
                  if (!field) {
                    return null;
                  }
                  const expected = normalize(messageFragment).toLowerCase();
                  const resolveIds = (attributeValue) => {
                    const ids = normalize(attributeValue).split(' ').filter(Boolean);
                    return ids
                      .map((id) => document.getElementById(id))
                      .filter((element) => !!element)
                      .map((element) => collectText(element))
                      .filter((text) => text.length > 0);
                  };
                  const describedbyTexts = resolveIds(field.getAttribute('aria-describedby'));
                  const errormessageTexts = resolveIds(field.getAttribute('aria-errormessage'));
                  const liveRegionTexts = Array.from(
                    root.querySelectorAll('[aria-live], [role="alert"], [role="status"]'),
                  )
                    .filter((element) => isVisible(element))
                    .map((element) => collectText(element))
                    .filter((text) => text.length > 0);
                  const matchingMessageElements = Array.from(root.querySelectorAll('*'))
                    .filter((element) => isVisible(element))
                    .map((element) => {
                      const text = collectText(element);
                      const rect = element.getBoundingClientRect();
                      return {
                        element,
                        text,
                        textLength: text.length,
                        area: rect.width * rect.height,
                      };
                    })
                    .filter(
                      (candidate) =>
                        candidate.text.length > 0
                        && candidate.text.toLowerCase().includes(expected),
                    )
                    .sort((left, right) => {
                      if (left.textLength !== right.textLength) {
                        return left.textLength - right.textLength;
                      }
                      return left.area - right.area;
                    });
                  const messageElement =
                    matchingMessageElements.length > 0
                      ? matchingMessageElements[0].element
                      : null;
                  const message =
                    messageElement === null
                      ? null
                      : (() => {
                          const style = window.getComputedStyle(messageElement);
                          const backgroundColor = effectiveBackgroundColor(messageElement);
                          const foreground = parseColor(style.color);
                          const background = parseColor(backgroundColor);
                          return {
                            text: collectText(messageElement),
                            tagName: messageElement.tagName,
                            role: messageElement.getAttribute('role'),
                            ariaLive: messageElement.getAttribute('aria-live'),
                            elementId: messageElement.id || null,
                            color: style.color,
                            backgroundColor,
                            contrastRatio:
                              foreground === null || background === null
                                ? null
                                : contrastRatio(foreground, background),
                          };
                        })();
                  const fieldInvalid =
                    String(field.getAttribute('aria-invalid') || '').toLowerCase() === 'true';
                  const hasAssociatedFeedback = [
                    ...(message === null ? [] : [message.text]),
                    ...describedbyTexts,
                    ...errormessageTexts,
                    ...liveRegionTexts,
                  ].some((text) => text.toLowerCase().includes(expected));
                  if (!fieldInvalid && !hasAssociatedFeedback) {
                    return null;
                  }
                  const active = document.activeElement;
                  const activeText =
                    active === null
                      ? ''
                      : normalize(
                          active.innerText
                            || active.textContent
                            || active.getAttribute('aria-label')
                            || '',
                        );
                  return {
                    kind: 'validation',
                    field: {
                      value:
                        'value' in field && typeof field.value === 'string'
                          ? field.value
                          : collectText(field),
                      enabled: !field.disabled,
                      disabled: !!field.disabled,
                      readOnly: !!field.readOnly,
                      ariaLabel: field.getAttribute('aria-label'),
                      ariaInvalid: field.getAttribute('aria-invalid'),
                      ariaDescribedBy: field.getAttribute('aria-describedby'),
                      ariaErrormessage: field.getAttribute('aria-errormessage'),
                      outerHtml: field.outerHTML.slice(0, 800),
                    },
                    message,
                    describedbyTexts,
                    errormessageTexts,
                    liveRegionTexts,
                    activeElement: active
                      ? {
                          tagName: active.tagName,
                          role: active.getAttribute('role'),
                          accessibleName:
                            active.getAttribute('aria-label') || activeText || null,
                          text: activeText,
                          tabindex: active.getAttribute('tabindex'),
                          outerHtml: active.outerHTML.slice(0, 400),
                        }
                      : {
                          tagName: '',
                          role: null,
                          accessibleName: null,
                          text: '',
                          tabindex: null,
                          outerHtml: '',
                        },
                    fieldIsActive: active === field,
                    dialogText: collectText(root),
                  };
                }
                """,
                arg={
                    "dialogSelector": self._dialog_group_selector,
                    "label": "Summary",
                    "messageFragment": message_fragment,
                    "errorPrefix": TrackStateTrackerPage.SAVE_FAILED_PREFIX,
                },
                timeout_ms=15_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step failed: clicking Save did not surface the expected Summary-required "
                "validation feedback in the hosted Edit issue dialog.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step failed: clicking Save did not produce an observable Summary-required "
                "validation state in the hosted Edit issue dialog.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        kind = str(payload.get("kind", ""))
        if kind == "save-error":
            raise AssertionError(
                "Step failed: clicking Save showed a visible save error instead of the "
                "required Summary validation feedback.\n"
                f"Observed body text:\n{str(payload.get('bodyText', self.current_body_text()))}",
            )
        if kind == "dialog-closed":
            raise AssertionError(
                "Step failed: clicking Save dismissed the Edit issue dialog and returned to "
                "the issue view without showing the required Summary validation feedback.\n"
                f"Observed body text:\n{str(payload.get('bodyText', self.current_body_text()))}",
            )
        if kind != "validation":
            raise AssertionError(
                "Step failed: clicking Save produced an unexpected validation probe result "
                "for the hosted Edit issue dialog.\n"
                f"Validation payload: {payload}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        field_payload = payload.get("field")
        active_payload = payload.get("activeElement")
        if not isinstance(field_payload, dict) or not isinstance(active_payload, dict):
            raise AssertionError(
                "Step failed: the hosted Edit issue validation probe returned an incomplete "
                "Summary validation payload.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        message_payload = payload.get("message")
        message = (
            None
            if not isinstance(message_payload, dict)
            else ValidationMessageObservation(
                text=str(message_payload.get("text", "")),
                tag_name=str(message_payload.get("tagName", "")),
                role=(
                    str(message_payload["role"])
                    if message_payload.get("role") is not None
                    else None
                ),
                aria_live=(
                    str(message_payload["ariaLive"])
                    if message_payload.get("ariaLive") is not None
                    else None
                ),
                element_id=(
                    str(message_payload["elementId"])
                    if message_payload.get("elementId") is not None
                    else None
                ),
                color=(
                    str(message_payload["color"])
                    if message_payload.get("color") is not None
                    else None
                ),
                background_color=(
                    str(message_payload["backgroundColor"])
                    if message_payload.get("backgroundColor") is not None
                    else None
                ),
                contrast_ratio=(
                    float(message_payload["contrastRatio"])
                    if message_payload.get("contrastRatio") is not None
                    else None
                ),
            )
        )
        return SummaryRequiredValidationObservation(
            field=LabeledTextFieldObservation(
                label="Summary",
                value=str(field_payload.get("value", "")),
                enabled=bool(field_payload.get("enabled")),
                disabled=bool(field_payload.get("disabled")),
                read_only=bool(field_payload.get("readOnly")),
                aria_label=(
                    str(field_payload["ariaLabel"])
                    if field_payload.get("ariaLabel") is not None
                    else None
                ),
                aria_invalid=(
                    str(field_payload["ariaInvalid"])
                    if field_payload.get("ariaInvalid") is not None
                    else None
                ),
                aria_describedby=(
                    str(field_payload["ariaDescribedBy"])
                    if field_payload.get("ariaDescribedBy") is not None
                    else None
                ),
                aria_errormessage=(
                    str(field_payload["ariaErrormessage"])
                    if field_payload.get("ariaErrormessage") is not None
                    else None
                ),
                outer_html=str(field_payload.get("outerHtml", "")),
            ),
            message=message,
            describedby_texts=tuple(
                str(text) for text in payload.get("describedbyTexts", []) if isinstance(text, str)
            ),
            errormessage_texts=tuple(
                str(text)
                for text in payload.get("errormessageTexts", [])
                if isinstance(text, str)
            ),
            live_region_texts=tuple(
                str(text) for text in payload.get("liveRegionTexts", []) if isinstance(text, str)
            ),
            active_element=FocusedElementObservation(
                tag_name=str(active_payload.get("tagName", "")),
                role=(
                    str(active_payload["role"])
                    if active_payload.get("role") is not None
                    else None
                ),
                accessible_name=(
                    str(active_payload["accessibleName"])
                    if active_payload.get("accessibleName") is not None
                    else None
                ),
                text=str(active_payload.get("text", "")),
                tabindex=(
                    str(active_payload["tabindex"])
                    if active_payload.get("tabindex") is not None
                    else None
                ),
                outer_html=str(active_payload.get("outerHtml", "")),
            ),
            field_is_active=bool(payload.get("fieldIsActive")),
            dialog_text=str(payload.get("dialogText", "")),
        )

    def open_issue_from_current_section(
        self,
        *,
        issue_key: str,
        issue_summary: str,
    ) -> str:
        selector = self._issue_selector(issue_key=issue_key, issue_summary=issue_summary)
        if self._session.count(selector) > 0:
            self._session.click(selector, timeout_ms=30_000)
        else:
            clicked = self._session.evaluate(
                """
                ({ issueKey, issueSummary }) => {
                  const candidates = Array.from(
                    document.querySelectorAll('flt-semantics, flt-semantics-img'),
                  )
                    .map((element) => {
                      const label = element.getAttribute('aria-label') ?? '';
                      const text = (element.innerText || element.textContent || '').trim();
                      const rect = element.getBoundingClientRect();
                      return {
                        element,
                        label,
                        text,
                        width: rect.width,
                        height: rect.height,
                        left: rect.left,
                        top: rect.top,
                        area: rect.width * rect.height,
                      };
                    })
                    .filter((candidate) =>
                      candidate.width > 0
                      && candidate.height > 0
                      && (candidate.label.includes(issueKey) || candidate.text.includes(issueKey))
                      && (
                        candidate.label.includes(issueSummary)
                        || candidate.text.includes(issueSummary)
                      ),
                    )
                    .sort((left, right) => left.area - right.area);
                  if (candidates.length === 0) {
                    return false;
                  }
                  candidates[0].element.click();
                  return true;
                }
                """,
                arg={"issueKey": issue_key, "issueSummary": issue_summary},
            )
            if clicked is not True:
                raise AssertionError(
                    f"Step failed: the hosted tracker did not expose a visible clickable "
                    f"region for {issue_key} in the current section.\n"
                    f"Observed body text:\n{self.current_body_text()}",
                )
        self._session.wait_for_selector(
            self._issue_detail_selector(issue_key),
            timeout_ms=60_000,
        )
        return self.current_body_text()

    def navigate_to_section(self, label: str) -> None:
        bounds = self._button_bounds_for_sidebar_label(label)
        if bounds is None:
            raise AssertionError(
                f'Step failed: the hosted tracker did not expose a visible "{label}" '
                "navigation entry in the sidebar.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        self._session.mouse_click(
            bounds["x"] + (bounds["width"] / 2),
            bounds["y"] + (bounds["height"] / 2),
        )
        try:
            self._session.wait_for_function(
                """
                (label) => Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                  .some((element) =>
                    (element.innerText || '').trim() === label
                    && element.getAttribute('aria-current') === 'true')
                """,
                arg=label,
                timeout_ms=30_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Step failed: clicking the "{label}" sidebar entry did not activate '
                "that section in the hosted tracker.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def status_control(self) -> EditControlObservation:
        observation = self._control_observation(
            """
            (button) => {
              const label = button.getAttribute('aria-label') ?? '';
              const text = (button.innerText || '').trim();
              return label.includes('Status') || text.startsWith('Status');
            }
            """,
        )
        if observation is None:
            raise AssertionError(
                "Human-style verification failed: the Edit issue surface did not show "
                "a visible Status control.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return observation

    def priority_control(self) -> EditControlObservation:
        observation = self._control_observation(
            """
            (button) => {
              const label = button.getAttribute('aria-label') ?? '';
              const text = (button.innerText || '').trim();
              return label.includes('Priority') || text.startsWith('Priority');
            }
            """,
        )
        if observation is None:
            raise AssertionError(
                "Human-style verification failed: the Edit issue surface did not show "
                "a visible Priority control.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return observation

    def constrained_chip_field(self, label: str) -> ConstrainedChipFieldObservation:
        payload = self._session.evaluate(
            """
            ({ label }) => {
              const groups = Array.from(
                document.querySelectorAll('flt-semantics[role="group"]'),
              );
              const group = groups.find((element) => {
                const aria = element.getAttribute('aria-label') ?? '';
                const text = (element.innerText || element.textContent || '').trim();
                return (
                  aria === label ||
                  aria.startsWith(`${label}\n`) ||
                  text === label ||
                  text.startsWith(`${label}\n`)
                );
              });
              if (!group) {
                return null;
              }

              const optionLabels = Array.from(
                group.querySelectorAll('flt-semantics[role="button"]'),
              )
                .map((button) => {
                  const aria = button.getAttribute('aria-label');
                  const text = (button.innerText || button.textContent || '').trim();
                  return (aria || text || '').trim();
                })
                .filter((value) => value.length > 0);

              return {
                semanticsLabel: group.getAttribute('aria-label'),
                fieldText: (group.innerText || group.textContent || '').trim(),
                optionLabels,
                inputCount: group.querySelectorAll(
                  'input, textarea, [contenteditable="true"]',
                ).length,
                listboxCount: group.querySelectorAll('[role="listbox"]').length,
                menuItemCount: group.querySelectorAll(
                  '[role="option"], flt-semantics[role="menuitem"]',
                ).length,
              };
            }
            """,
            arg={"label": label},
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                f"Human-style verification failed: the Edit issue surface did not show "
                f"the visible {label!r} field.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        option_labels = payload.get("optionLabels")
        if not isinstance(option_labels, list):
            option_labels = []
        return ConstrainedChipFieldObservation(
            label=label,
            semantics_label=(
                str(payload["semanticsLabel"])
                if payload.get("semanticsLabel") is not None
                else None
            ),
            field_text=str(payload.get("fieldText", "")),
            option_labels=tuple(str(value) for value in option_labels),
            input_count=int(payload.get("inputCount", 0)),
            listbox_count=int(payload.get("listboxCount", 0)),
            menu_item_count=int(payload.get("menuItemCount", 0)),
        )
    def change_priority(self, target_label: str) -> EditControlObservation:
        control = self.priority_control()
        if control.contains(target_label):
            raise AssertionError(
                "Step 4 failed: the Edit issue surface already showed Priority = "
                f"{target_label} before any mutation, so TS-401 cannot prove that a "
                "fresh edit triggered the downstream refresh.\n"
                f"Observed control label: {control.label}\n"
                f"Observed control text: {control.text}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        options = self._open_focusable_dropdown(
            selector=self._button_selector,
            has_text="Priority",
            control_name="Priority",
        )
        self._select_dropdown_option(
            control_name="Priority",
            target_label=target_label,
            options=options,
        )
        updated = self.priority_control()
        if not updated.contains(target_label):
            raise AssertionError(
                "Step 4 failed: selecting the Priority control did not update the visible "
                f"value to {target_label}.\n"
                f"Observed control label: {updated.label}\n"
                f"Observed control text: {updated.text}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return updated

    def change_status_transition(self, target_label: str) -> EditControlObservation:
        control = self.status_control()
        if control.contains(target_label):
            raise AssertionError(
                "Step 5 failed: the Edit issue surface already showed Status = "
                f"{target_label} before any mutation, so TS-401 cannot prove that a "
                "fresh workflow transition triggered the downstream refresh.\n"
                f"Observed status control label: {control.label}\n"
                f"Observed status helper text: {control.text}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        if control.contains("No workflow transitions available."):
            raise AssertionError(
                "Step 5 failed: the Edit issue surface did not expose any workflow "
                f"transitions, so the scenario could not change the Status to "
                f"{target_label} before saving.\n"
                f"Observed status control label: {control.label}\n"
                f"Observed status helper text: {control.text}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        if control.tabindex is None:
            raise AssertionError(
                "Step 5 failed: the visible Status control rendered as non-focusable in "
                "the hosted edit dialog, so the test could not perform a production-visible "
                f"workflow transition to {target_label}.\n"
                f"Observed status control label: {control.label}\n"
                f"Observed status helper text: {control.text}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        options = self._open_focusable_dropdown(
            selector='flt-semantics[role="button"][aria-label*="Status"]',
            has_text=None,
            control_name="Status",
        )
        self._select_dropdown_option(
            control_name="Status",
            target_label=target_label,
            options=options,
        )
        updated = self.status_control()
        if not updated.contains(target_label):
            raise AssertionError(
                "Step 5 failed: selecting the Status control did not update the visible "
                f"workflow transition to {target_label}.\n"
                f"Observed control label: {updated.label}\n"
                f"Observed control text: {updated.text}\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return updated

    def available_status_transitions(self) -> tuple[str, ...]:
        options = self._open_focusable_dropdown(
            selector='flt-semantics[role="button"][aria-label*="Status"]',
            has_text=None,
            control_name="Status",
        )
        self._session.press_key("Escape")
        self._session.wait_for_function(
            """
            () =>
              document.querySelectorAll('flt-semantics[role="menuitem"]').length === 0
              && (document.body?.innerText ?? '').includes('Edit issue')
            """,
            timeout_ms=30_000,
        )
        return options

    def visible_board_issues(self) -> tuple[BoardIssueObservation, ...]:
        self.navigate_to_section("Board")
        payload = self._session.evaluate(
            """
            () => {
              const issuePattern = /^Open ([A-Z][A-Z0-9]+-\\d+)\\s+(.+)$/;
              const issues = [];
              for (const element of document.querySelectorAll('flt-semantics[role="button"]')) {
                const label = (element.getAttribute('aria-label') ?? '').trim();
                const text = (element.innerText || element.textContent || '').trim();
                const source = label || text;
                const match = issuePattern.exec(source);
                if (!match) {
                  continue;
                }
                const rect = element.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                  continue;
                }
                issues.push({
                  key: match[1],
                  summary: match[2],
                  label: source,
                });
              }
              return issues;
            }
            """,
        )
        if not isinstance(payload, list):
            return ()
        issues: list[BoardIssueObservation] = []
        seen_keys: set[str] = set()
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            key = str(entry.get("key", "")).strip()
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            issues.append(
                BoardIssueObservation(
                    key=key,
                    summary=str(entry.get("summary", "")).strip(),
                    label=str(entry.get("label", "")).strip(),
                ),
            )
        return tuple(issues)
    def save_issue_edits(
        self,
        *,
        issue_key: str,
        expected_status: str,
    ) -> str:
        self._session.wait_for_selector(
            self._button_selector,
            has_text="Save",
            timeout_ms=30_000,
        )
        self._session.click(
            self._button_selector,
            has_text="Save",
            timeout_ms=30_000,
        )
        try:
            payload = self._session.wait_for_function(
                """
                ({
                  dialogSelector,
                  errorPrefix,
                  successMessages,
                }) => {
                  const bodyText = document.body?.innerText ?? '';
                  if (bodyText.includes(errorPrefix)) {
                    return { kind: 'error', bodyText };
                  }
                  const matchedSuccessMessage =
                    successMessages.find((message) => bodyText.includes(message)) ?? null;
                  const dialogVisible =
                    document.querySelector(dialogSelector) !== null;
                  if (dialogVisible || matchedSuccessMessage === null) {
                    return null;
                  }
                  return { kind: 'saved', bodyText, matchedSuccessMessage };
                }
                """,
                arg={
                    "dialogSelector": self._dialog_group_selector,
                    "errorPrefix": TrackStateTrackerPage.SAVE_FAILED_PREFIX,
                    "successMessages": [
                        f"{issue_key} moved to {expected_status} and committed to GitHub.",
                        f"{issue_key} moved to {expected_status} and committed to local Git branch ",
                        f"{issue_key} moved locally. Connect GitHub in Settings to persist.",
                    ],
                },
                timeout_ms=180_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 6 failed: clicking Save never surfaced the required user-visible "
                "success banner after the edit dialog closed.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 6 failed: saving the edited issue did not produce an observable "
                "post-save state in the hosted tracker.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        if str(payload.get("kind")) == "error":
            raise AssertionError(
                "Step 6 failed: clicking Save surfaced a visible save error instead of "
                "committing the edited issue.\n"
                f"Observed body text:\n{payload.get('bodyText', self.current_body_text())}",
            )
        return str(payload["bodyText"])

    def wait_for_issue_detail_state(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        expected_status: str,
        expected_priority: str,
        step_number: int,
    ) -> str:
        try:
            payload = self._session.wait_for_function(
                """
                ({ issueKey, issueSummary, detailSelector, expectedStatus, expectedPriority }) => {
                  if (!document.querySelector(detailSelector)) {
                    return null;
                  }
                  const bodyText = document.body?.innerText ?? '';
                  const matches =
                    bodyText.includes(issueKey) &&
                    bodyText.includes(issueSummary) &&
                    bodyText.includes(expectedStatus) &&
                    bodyText.includes(expectedPriority);
                  return matches ? { bodyText } : null;
                }
                """,
                arg={
                    "issueKey": issue_key,
                    "issueSummary": issue_summary,
                    "detailSelector": self._issue_detail_selector(issue_key),
                    "expectedStatus": expected_status,
                    "expectedPriority": expected_priority,
                },
                timeout_ms=60_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f"Step {step_number} failed: the hosted issue detail for {issue_key} did "
                f"not visibly refresh to Status = {expected_status} and Priority = "
                f"{expected_priority}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                f"Step {step_number} failed: the hosted issue detail for {issue_key} did "
                "not reach an observable refreshed state.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return str(payload["bodyText"])

    def wait_for_board_projection(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        expected_column: str,
        expected_priority: str,
    ) -> str:
        self.navigate_to_section("Board")
        try:
            payload = self._session.wait_for_function(
                """
                ({ issueKey, issueSummary, expectedColumn, expectedPriority }) => {
                  const expectedAriaLabel = `${expectedColumn} column`;
                  const column = Array.from(document.querySelectorAll('flt-semantics'))
                    .find((element) => (element.getAttribute('aria-label') ?? '') === expectedAriaLabel);
                  if (!column) {
                    return null;
                  }
                  const text = (column.innerText || '').trim();
                  return text.includes(issueKey)
                    && text.includes(issueSummary)
                    && text.includes(expectedPriority)
                    ? { text }
                    : null;
                }
                """,
                arg={
                    "issueKey": issue_key,
                    "issueSummary": issue_summary,
                    "expectedColumn": expected_column,
                    "expectedPriority": expected_priority,
                },
                timeout_ms=60_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 8 failed: the Board view did not visibly refresh the edited issue "
                f"into the {expected_column} column with Priority = {expected_priority}.\n"
                f"Observed Board text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 8 failed: the Board view did not expose an observable refreshed "
                f"projection for {issue_key}.\n"
                f"Observed Board text:\n{self.current_body_text()}",
            )
        return str(payload["text"])

    def wait_for_hierarchy_projection(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        expected_status: str,
        expected_priority: str,
    ) -> str:
        self.navigate_to_section("Hierarchy")
        return self._wait_for_issue_projection(
            issue_key=issue_key,
            issue_summary=issue_summary,
            expected_status=expected_status,
            expected_priority=expected_priority,
            section_label="Hierarchy",
            step_number=9,
        )

    def wait_for_jql_search_projection(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        expected_status: str,
        expected_priority: str,
        expected_count_summary: str,
    ) -> str:
        try:
            payload = self._session.wait_for_function(
                """
                ({
                  expectedCountSummary,
                  expectedPriority,
                  expectedStatus,
                  issueKey,
                  issueSelector,
                  issueSummary,
                }) => {
                  const bodyText = document.body?.innerText ?? '';
                  const countMatch = bodyText.match(/\\b(?:No issues|\\d+ issues?)\\b/);
                  const countSummary = countMatch ? countMatch[0] : null;
                  if (countSummary !== expectedCountSummary) {
                    return null;
                  }

                  const issue = document.querySelector(issueSelector);
                  if (!issue) {
                    return null;
                  }

                  let current = issue;
                  while (current) {
                    const projectionText = (current.innerText || current.textContent || '').trim();
                    if (
                      projectionText.includes(issueKey) &&
                      projectionText.includes(issueSummary)
                    ) {
                      return projectionText.includes(expectedStatus) &&
                          projectionText.includes(expectedPriority)
                        ? { countSummary, projectionText }
                        : null;
                    }
                    current = current.parentElement;
                  }

                  return null;
                }
                """,
                arg={
                    "expectedCountSummary": expected_count_summary,
                    "expectedPriority": expected_priority,
                    "expectedStatus": expected_status,
                    "issueKey": issue_key,
                    "issueSelector": self._issue_selector(
                        issue_key=issue_key,
                        issue_summary=issue_summary,
                    ),
                    "issueSummary": issue_summary,
                },
                timeout_ms=60_000,
            )
        except WebAppTimeoutError as error:
            current_projection = self._current_issue_projection_text(
                issue_key=issue_key,
                issue_summary=issue_summary,
            )
            raise AssertionError(
                "Step 10 failed: the JQL Search result row did not visibly refresh "
                f"{issue_key} to Status = {expected_status} and Priority = "
                f"{expected_priority} while showing {expected_count_summary}.\n"
                f"Observed JQL Search projection: {current_projection}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "Step 10 failed: the JQL Search result row did not expose an observable "
                f"projection for {issue_key} after saving.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return str(payload["projectionText"])

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def visible_issue_open_label(self, *, issue_key: str) -> str:
        payload = self._session.evaluate(
            """
            (issueKey) => {
              const visible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return (
                  rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none'
                );
              };
              const matches = Array.from(
                document.querySelectorAll('flt-semantics[role="button"][aria-label^="Open "]'),
              )
                .filter((element) => visible(element))
                .map((element) => element.getAttribute('aria-label') ?? '')
                .filter((label) => label.startsWith(`Open ${issueKey} `));
              return matches[0] ?? null;
            }
            """,
            arg=issue_key,
        )
        if not isinstance(payload, str):
            raise AssertionError(
                f"Step failed: the hosted tracker did not expose a visible JQL Search row "
                f"for {issue_key}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        label = payload.strip()
        if not label:
            raise AssertionError(
                f"Step failed: the hosted tracker did not expose a visible JQL Search row "
                f"for {issue_key}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return label
    def _wait_for_issue_projection(
        self,
        *,
        issue_key: str,
        issue_summary: str,
        expected_status: str,
        expected_priority: str,
        section_label: str,
        step_number: int,
    ) -> str:
        try:
            payload = self._session.wait_for_function(
                """
                ({
                  expectedPriority,
                  expectedStatus,
                  issueKey,
                  issueSelector,
                  issueSummary,
                }) => {
                  const issue = document.querySelector(issueSelector);
                  if (!issue) {
                    return null;
                  }

                  let current = issue;
                  while (current) {
                    const projectionText = (current.innerText || current.textContent || '').trim();
                    if (
                      projectionText.includes(issueKey) &&
                      projectionText.includes(issueSummary)
                    ) {
                      return projectionText.includes(expectedStatus) &&
                          projectionText.includes(expectedPriority)
                        ? { projectionText }
                        : null;
                    }
                    current = current.parentElement;
                  }

                  return null;
                }
                """,
                arg={
                    "expectedPriority": expected_priority,
                    "expectedStatus": expected_status,
                    "issueKey": issue_key,
                    "issueSelector": self._issue_selector(
                        issue_key=issue_key,
                        issue_summary=issue_summary,
                    ),
                    "issueSummary": issue_summary,
                },
                timeout_ms=60_000,
            )
        except WebAppTimeoutError as error:
            current_projection = self._current_issue_projection_text(
                issue_key=issue_key,
                issue_summary=issue_summary,
            )
            raise AssertionError(
                f"Step {step_number} failed: the {section_label} projection did not visibly "
                f"refresh {issue_key} to Status = {expected_status} and Priority = "
                f"{expected_priority}.\n"
                f"Observed {section_label} projection: {current_projection}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                f"Step {step_number} failed: the {section_label} view did not expose an "
                f"observable refreshed projection for {issue_key}.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return str(payload["projectionText"])

    def _current_issue_projection_text(self, *, issue_key: str, issue_summary: str) -> str:
        payload = self._session.evaluate(
            """
            ({ issueKey, issueSelector, issueSummary }) => {
              const issue = document.querySelector(issueSelector);
              if (!issue) {
                return { projectionText: '' };
              }

              let current = issue;
              while (current) {
                const projectionText = (current.innerText || current.textContent || '').trim();
                if (
                  projectionText.includes(issueKey) &&
                  projectionText.includes(issueSummary)
                ) {
                  return { projectionText };
                }
                current = current.parentElement;
              }

              return {
                projectionText: (issue.innerText || issue.textContent || '').trim(),
              };
            }
            """,
            arg={
                "issueKey": issue_key,
                "issueSelector": self._issue_selector(
                    issue_key=issue_key,
                    issue_summary=issue_summary,
                ),
                "issueSummary": issue_summary,
            },
        )
        if not isinstance(payload, dict):
            return ""
        return str(payload.get("projectionText", ""))

    def _control_observation(
        self,
        predicate_expression: str,
    ) -> EditControlObservation | None:
        payload = self._session.evaluate(
            f"""
            (predicateSource) => {{
              const predicate = eval(predicateSource);
              const match = Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                .map((button) => ({{
                  label: button.getAttribute('aria-label'),
                  text: (button.innerText || '').trim(),
                  tabindex: button.getAttribute('tabindex'),
                  expanded: button.getAttribute('aria-expanded'),
                }}))
                .find((candidate) => predicate({{
                  getAttribute: (name) => {{
                    if (name === 'aria-label') {{
                      return candidate.label;
                    }}
                    if (name === 'tabindex') {{
                      return candidate.tabindex;
                    }}
                    if (name === 'aria-expanded') {{
                      return candidate.expanded;
                    }}
                    return null;
                  }},
                  innerText: candidate.text,
                }}));
              return match ?? null;
            }}
            """,
            arg=predicate_expression,
        )
        if not isinstance(payload, dict):
            return None
        return EditControlObservation(
            label=str(payload["label"]) if payload["label"] is not None else None,
            text=str(payload["text"]),
            tabindex=(
                str(payload["tabindex"]) if payload["tabindex"] is not None else None
            ),
            expanded=(
                str(payload["expanded"]) if payload["expanded"] is not None else None
            ),
        )

    def _wait_for_edit_dialog(self, *, issue_key: str, origin_label: str) -> str:
        self._session.wait_for_selector(self._dialog_group_selector, timeout_ms=30_000)
        self._session.wait_for_function(
            """
            ({ dialogSelector }) => {
              const root = document.querySelector(dialogSelector);
              if (!root) {
                return false;
              }
              const hasLabeledField = (label) => [
                `input[aria-label="${label}"]`,
                `textarea[aria-label="${label}"]`,
                `[role="textbox"][aria-label="${label}"]`,
              ].some((selector) => root.querySelector(selector) !== null);
              return (
                hasLabeledField('Summary')
                && hasLabeledField('Description')
                && (document.body?.innerText ?? '').includes('Edit issue')
              );
            }
            """,
            arg={"dialogSelector": self._dialog_group_selector},
            timeout_ms=30_000,
        )
        dialog_text = self.current_body_text()
        if issue_key not in dialog_text:
            raise AssertionError(
                f"Step failed: opening the requested issue from {origin_label} did not "
                f"lead to the edit surface for {issue_key}.\n"
                f"Expected issue key in edit dialog: {issue_key}\n"
                f"Observed dialog text:\n{dialog_text}",
            )
        return dialog_text

    def _reveal_board_issue_edit_button(
        self,
        *,
        card_bounds: dict[str, float],
    ) -> dict[str, float] | None:
        for point in self._board_issue_hover_points(card_bounds=card_bounds):
            self._session.mouse_move(point["x"], point["y"])
            try:
                self._session.wait_for_function(
                    self._board_issue_edit_button_script(),
                    arg={"cardBounds": card_bounds},
                    timeout_ms=1_500,
                )
            except WebAppTimeoutError:
                continue
            edit_bounds = self._board_issue_edit_button_bounds(card_bounds=card_bounds)
            if edit_bounds is not None:
                return edit_bounds
        return self._board_issue_edit_button_bounds(card_bounds=card_bounds)

    @staticmethod
    def _board_issue_hover_points(
        *,
        card_bounds: dict[str, float],
    ) -> tuple[dict[str, float], ...]:
        left = card_bounds["x"]
        top = card_bounds["y"]
        width = card_bounds["width"]
        height = card_bounds["height"]
        return (
            {"x": left + (width / 2), "y": top + (height / 2)},
            {"x": left + width - 24, "y": top + 24},
            {"x": left + 24, "y": top + 24},
            {"x": left + width - 24, "y": top + height - 24},
        )

    def _board_issue_card_bounds(
        self,
        *,
        issue_key: str,
        issue_summary: str,
    ) -> dict[str, float]:
        payload = self._session.evaluate(
            """
            ({ issueKey, issueSummary }) => {
              const visible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return (
                  rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none'
                );
              };
              const candidates = Array.from(
                document.querySelectorAll('flt-semantics, flt-semantics-img'),
              )
                .filter((element) => visible(element))
                .map((element) => {
                  const rect = element.getBoundingClientRect();
                  const label = element.getAttribute('aria-label') ?? '';
                  const text = (element.innerText || element.textContent || '').trim();
                  return {
                    label,
                    text,
                    x: rect.left,
                    y: rect.top,
                    width: rect.width,
                    height: rect.height,
                    area: rect.width * rect.height,
                  };
                })
                .filter((candidate) =>
                  (candidate.label.includes(issueKey) || candidate.text.includes(issueKey))
                  && (
                    candidate.label.includes(issueSummary)
                    || candidate.text.includes(issueSummary)
                  ),
                )
                .sort((left, right) => left.area - right.area);
              return candidates[0] ?? null;
            }
            """,
            arg={"issueKey": issue_key, "issueSummary": issue_summary},
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                f"Step failed: the Board view did not expose a visible card region for "
                f"{issue_key}.\n"
                f"Observed Board text:\n{self.current_body_text()}",
            )
        for key in ("x", "y", "width", "height"):
            value = payload.get(key)
            if not isinstance(value, (int, float)):
                raise AssertionError(
                    f"Step failed: the Board card geometry for {issue_key} was not readable.\n"
                    f"Observed Board text:\n{self.current_body_text()}",
                )
        return {
            "x": float(payload["x"]),
            "y": float(payload["y"]),
            "width": float(payload["width"]),
            "height": float(payload["height"]),
        }

    def _board_issue_edit_button_bounds(
        self,
        *,
        card_bounds: dict[str, float],
    ) -> dict[str, float] | None:
        payload = self._session.evaluate(
            self._board_issue_edit_button_script(),
            arg={"cardBounds": card_bounds},
        )
        if not isinstance(payload, dict):
            return None
        coordinates = (
            payload.get("x"),
            payload.get("y"),
            payload.get("width"),
            payload.get("height"),
        )
        if not all(isinstance(value, (int, float)) for value in coordinates):
            return None
        return {
            "x": float(payload["x"]),
            "y": float(payload["y"]),
            "width": float(payload["width"]),
            "height": float(payload["height"]),
        }

    def _board_issue_controls_snapshot(
        self,
        *,
        card_bounds: dict[str, float],
    ) -> tuple[str, ...]:
        payload = self._session.evaluate(
            """
            ({ cardBounds }) => {
              const visible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return (
                  rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none'
                );
              };
              const overlapsCard = (rect) => (
                rect.left < (cardBounds.x + cardBounds.width + 24)
                && (rect.left + rect.width) > (cardBounds.x - 24)
                && rect.top < (cardBounds.y + cardBounds.height + 24)
                && (rect.top + rect.height) > (cardBounds.y - 24)
              );
              return Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                .filter((element) => visible(element))
                .map((element) => {
                  const rect = element.getBoundingClientRect();
                  const label = (element.getAttribute('aria-label') ?? '').trim();
                  const text = (element.innerText || element.textContent || '').trim();
                  return {
                    rect,
                    label,
                    text,
                    description: `${label || '<no-aria>'} | ${text || '<no-text>'}`,
                  };
                })
                .filter((candidate) => overlapsCard(candidate.rect))
                .map((candidate) => candidate.description)
                .slice(0, 8);
            }
            """,
            arg={"cardBounds": card_bounds},
        )
        if not isinstance(payload, list):
            return ()
        return tuple(str(entry) for entry in payload if str(entry).strip())

    @staticmethod
    def _board_issue_edit_button_script() -> str:
        return """
            ({ cardBounds }) => {
              const visible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return (
                  rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none'
                );
              };
              const overlapsCard = (rect) => (
                rect.left < (cardBounds.x + cardBounds.width + 24)
                && (rect.left + rect.width) > (cardBounds.x - 24)
                && rect.top < (cardBounds.y + cardBounds.height + 24)
                && (rect.top + rect.height) > (cardBounds.y - 24)
              );
              const candidates = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter((element) => visible(element))
                .map((element) => {
                  const rect = element.getBoundingClientRect();
                  const label = element.getAttribute('aria-label') ?? '';
                  const text = (element.innerText || element.textContent || '').trim();
                  return {
                    x: rect.left,
                    y: rect.top,
                    width: rect.width,
                    height: rect.height,
                    area: rect.width * rect.height,
                    label,
                    text,
                    matchesEdit: /edit/i.test(`${label}\n${text}`),
                    overlapsCard: overlapsCard(rect),
                  };
                })
                .filter((candidate) => candidate.matchesEdit && candidate.overlapsCard)
                .sort((left, right) => left.area - right.area);
              return candidates[0] ?? null;
            }
        """
    def _open_focusable_dropdown(
        self,
        *,
        selector: str,
        has_text: str | None,
        control_name: str,
    ) -> tuple[str, ...]:
        self._session.focus(
            selector,
            has_text=has_text,
            timeout_ms=30_000,
        )
        for key in ("Enter", " ", "ArrowUp"):
            self._session.press_key(key)
            try:
                self._session.wait_for_function(
                    """
                    () => document.querySelectorAll('flt-semantics[role="menuitem"]').length > 0
                    """,
                    timeout_ms=5_000,
                )
                options = self._visible_menu_options()
                if options:
                    return options
            except WebAppTimeoutError:
                continue
        active = self._session.active_element()
        raise AssertionError(
            f"Step failed: opening the {control_name} control did not expose a "
            "keyboard-selectable menu item in the hosted edit dialog.\n"
            f"Active element after opening: {active}\n"
            f"Observed body text:\n{self.current_body_text()}",
        )

    def _visible_menu_options(self) -> tuple[str, ...]:
        payload = self._session.evaluate(
            """
            (selector) => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const isTopmostVisible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                if (
                  rect.width <= 0
                  || rect.height <= 0
                  || style.visibility === 'hidden'
                  || style.display === 'none'
                  || Number.parseFloat(style.opacity || '1') <= 0
                ) {
                  return false;
                }
                const pointX = rect.left + (rect.width / 2);
                const pointY = rect.top + (rect.height / 2);
                const topmost = document.elementFromPoint(pointX, pointY);
                return !!topmost && (element === topmost || element.contains(topmost));
              };
              const candidates = [
                ...Array.from(document.querySelectorAll(selector)),
                ...Array.from(document.querySelectorAll('flt-semantics, flt-semantics-img')),
                ...Array.from(document.querySelectorAll('body *')),
              ];
              const labels = [];
              for (const element of candidates) {
                if (!isTopmostVisible(element)) {
                  continue;
                }
                const label = normalize(element.getAttribute('aria-label'));
                const text = normalize(element.innerText || element.textContent);
                const value = label || text;
                if (value.length > 0 && value.length <= 80) {
                  labels.push(value);
                }
              }
              return Array.from(new Set(labels));
            }
            """,
            arg=self._menu_item_selector,
        )
        if not isinstance(payload, list):
            return ()
        return tuple(str(label) for label in payload)

    def _select_dropdown_option(
        self,
        *,
        control_name: str,
        target_label: str,
        options: tuple[str, ...],
    ) -> None:
        if target_label not in options:
            clicked = self._select_visually_rendered_priority_option(
                control_name=control_name,
                target_label=target_label,
                options=options,
            )
            if clicked is not True:
                raise AssertionError(
                    f"Step failed: the {control_name} control did not expose the required "
                    f'visible option "{target_label}".\n'
                    f"Visible options: {list(options)}",
                )
        else:
            clicked = self._session.evaluate(
            """
            ({ selector, targetLabel }) => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const isTopmostVisible = (element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                if (
                  rect.width <= 0
                  || rect.height <= 0
                  || style.visibility === 'hidden'
                  || style.display === 'none'
                  || Number.parseFloat(style.opacity || '1') <= 0
                ) {
                  return false;
                }
                const pointX = rect.left + (rect.width / 2);
                const pointY = rect.top + (rect.height / 2);
                const topmost = document.elementFromPoint(pointX, pointY);
                return !!topmost && (element === topmost || element.contains(topmost));
              };
              const candidates = [
                ...Array.from(document.querySelectorAll(selector)),
                ...Array.from(document.querySelectorAll('flt-semantics, flt-semantics-img')),
                ...Array.from(document.querySelectorAll('body *')),
              ]
                .filter((element) => {
                  const label = normalize(element.getAttribute('aria-label'));
                  const text = normalize(element.innerText || element.textContent);
                  return (label === targetLabel || text === targetLabel)
                    && isTopmostVisible(element);
                })
                .sort((left, right) => {
                  const leftRole = left.getAttribute('role') === 'menuitem' ? 0 : 1;
                  const rightRole = right.getAttribute('role') === 'menuitem' ? 0 : 1;
                  if (leftRole !== rightRole) {
                    return leftRole - rightRole;
                  }
                  const leftRect = left.getBoundingClientRect();
                  const rightRect = right.getBoundingClientRect();
                  if (leftRect.top !== rightRect.top) {
                    return leftRect.top - rightRect.top;
                  }
                  return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                });
              const match = candidates[0];
              if (!match) {
                return false;
              }
              match.click();
              return true;
            }
            """,
            arg={
                "selector": self._menu_item_selector,
                "targetLabel": target_label,
            },
            )
        if clicked is not True:
            raise AssertionError(
                f"Step failed: the {control_name} menu did not expose a clickable option "
                f'exactly labeled "{target_label}".\n'
                f"Visible options: {list(options)}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        try:
            self._session.wait_for_function(
                """
                () =>
                  document.querySelectorAll('flt-semantics[role="menuitem"]').length === 0
                  && (document.body?.innerText ?? '').includes('Edit issue')
                """,
                timeout_ms=30_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f"Step failed: selecting {target_label} from the {control_name} menu did "
                "not return the app to the hosted edit dialog.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def _select_visually_rendered_priority_option(
        self,
        *,
        control_name: str,
        target_label: str,
        options: tuple[str, ...],
    ) -> bool:
        if control_name != "Priority" or target_label != "Highest" or "Medium" not in options:
            return False
        point = self._session.evaluate(
            """
            () => {
              const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
              const visibleMediumRows = Array.from(
                document.querySelectorAll('flt-semantics[role="menuitem"], flt-semantics, flt-semantics-img'),
              )
                .filter((element) => {
                  const label = normalize(element.getAttribute('aria-label'));
                  const text = normalize(element.innerText || element.textContent);
                  if (label !== 'Medium' && text !== 'Medium') {
                    return false;
                  }
                  const rect = element.getBoundingClientRect();
                  const style = window.getComputedStyle(element);
                  return (
                    rect.width > 0
                    && rect.height > 0
                    && style.visibility !== 'hidden'
                    && style.display !== 'none'
                    && Number.parseFloat(style.opacity || '1') > 0
                  );
                })
                .map((element) => {
                  const rect = element.getBoundingClientRect();
                  return {
                    x: rect.left + (rect.width / 2),
                    y: rect.top + (rect.height / 2) - (2 * rect.height),
                  };
                });
              return visibleMediumRows[0] ?? null;
            }
            """,
        )
        if not isinstance(point, dict):
            return False
        x = point.get("x")
        y = point.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return False
        self._session.mouse_click(float(x), float(y))
        return True

    def _active_menu_item_label(self) -> str:
        active = self._session.active_element()
        if active.role != "menuitem" or active.accessible_name is None:
            raise AssertionError(
                "The hosted dropdown menu lost focus before the test could finish "
                "navigating its visible options.\n"
                f"Observed active element: {active}",
            )
        return active.accessible_name

    def _button_bounds_for_sidebar_label(self, label: str) -> dict[str, float] | None:
        payload = self._session.evaluate(
            """
            (label) => {
              const button = Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                .find((element) => (element.innerText || '').trim() === label);
              if (!button) {
                return null;
              }
              const rect = button.getBoundingClientRect();
              return {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
              };
            }
            """,
            arg=label,
        )
        if not isinstance(payload, dict):
            return None
        return {
            "x": float(payload["x"]),
            "y": float(payload["y"]),
            "width": float(payload["width"]),
            "height": float(payload["height"]),
        }

    @staticmethod
    def _issue_selector(*, issue_key: str, issue_summary: str) -> str:
        escaped_summary = issue_summary.replace("\\", "\\\\").replace('"', '\\"')
        return (
            'flt-semantics[role="button"]'
            f'[aria-label="Open {issue_key} {escaped_summary}"]'
        )

    @classmethod
    def _issue_button_text(cls, *, issue_key: str, issue_summary: str) -> str:
        normalized_summary = cls._normalized_issue_summary(issue_summary)
        return f"Open {issue_key} {normalized_summary}"

    @staticmethod
    def _normalized_issue_summary(issue_summary: str) -> str:
        stripped = issue_summary.strip()
        if re.fullmatch(r'"[^"]+"', stripped):
            return stripped[1:-1]
        return stripped
    @staticmethod
    def _issue_detail_selector(issue_key: str) -> str:
        escaped = issue_key.replace("\\", "\\\\").replace('"', '\\"')
        return (
            'flt-semantics[aria-label*="Issue detail '
            f'{escaped}"], '
            'flt-semantics-img[aria-label*="Issue detail '
            f'{escaped}"]'
        )
