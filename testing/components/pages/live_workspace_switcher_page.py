from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import FocusedElementObservation, WebAppTimeoutError


@dataclass(frozen=True)
class FocusNavigationStep:
    step: int
    before_label: str | None
    before_role: str | None
    after_label: str | None
    after_role: str | None
    after_tag_name: str
    after_outer_html: str


@dataclass(frozen=True)
class WorkspaceSwitcherInteractiveObservation:
    label: str
    accessible_label: str
    role: str | None
    tag_name: str
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class WorkspaceSwitcherBadgeObservation:
    label: str
    foreground_color: str | None
    background_color: str | None
    contrast_ratio: float | None
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class WorkspaceSwitcherIconObservation:
    label: str
    foreground_color: str | None
    background_color: str | None
    contrast_ratio: float | None
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class WorkspaceSwitcherSurfaceObservation:
    body_text: str
    dialog_visible: bool
    heading_text: str
    interactive_elements: tuple[WorkspaceSwitcherInteractiveObservation, ...]
    missing_interactive_labels: tuple[str, ...]
    badges: tuple[WorkspaceSwitcherBadgeObservation, ...]
    interactive_icons: tuple[WorkspaceSwitcherIconObservation, ...]


@dataclass(frozen=True)
class MobileTriggerFocusObservation:
    trigger_label: str
    trigger_text: str
    trigger_x: float
    trigger_y: float
    trigger_width: float
    trigger_height: float
    before_outline: str
    before_outline_color: str
    before_outline_width: str
    before_box_shadow: str
    after_outline: str
    after_outline_color: str
    after_outline_width: str
    after_box_shadow: str
    active_label_after_focus: str | None
    active_role_after_focus: str | None
    active_tag_name_after_focus: str
    active_outer_html_after_focus: str
    focus_sequence: tuple[FocusNavigationStep, ...]


class LiveWorkspaceSwitcherPage:
    _search_input_selector = 'input[aria-label="Search issues"]'
    _top_bar_button_selector = 'flt-semantics[role="button"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def focus_search_field(self, *, timeout_ms: int = 30_000) -> None:
        self._session.focus(self._search_input_selector, timeout_ms=timeout_ms)

    def collect_tab_sequence_from_search(
        self,
        *,
        tab_count: int,
        timeout_ms: int = 30_000,
    ) -> tuple[FocusNavigationStep, ...]:
        self.focus_search_field(timeout_ms=timeout_ms)
        return self._collect_tab_sequence(tab_count=tab_count, timeout_ms=timeout_ms)

    def collect_tab_sequence(
        self,
        *,
        tab_count: int,
        timeout_ms: int = 30_000,
    ) -> tuple[FocusNavigationStep, ...]:
        return self._collect_tab_sequence(tab_count=tab_count, timeout_ms=timeout_ms)

    def active_element(self) -> FocusedElementObservation:
        return self._session.active_element()

    def workspace_trigger_reached(
        self,
        sequence: tuple[FocusNavigationStep, ...],
    ) -> bool:
        return any(self._is_workspace_trigger_label(step.after_label) for step in sequence)

    def press_enter_on_active_element_and_wait_for_surface(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> None:
        self._session.press_key("Enter", timeout_ms=timeout_ms)
        self._wait_for_surface(timeout_ms=timeout_ms)

    def open_surface_with_click(self, *, timeout_ms: int = 30_000) -> None:
        self._session.click(
            self._top_bar_button_selector,
            has_text="Workspace switcher:",
            timeout_ms=timeout_ms,
        )
        self._wait_for_surface(timeout_ms=timeout_ms)

    def observe_surface(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> WorkspaceSwitcherSurfaceObservation:
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
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const toHex = (value) => {
                if (!value || value === 'transparent') {
                  return null;
                }
                const match = value.match(
                  /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([0-9.]+))?\\)/i,
                );
                if (!match) {
                  return null;
                }
                if (
                  match[4] !== undefined
                  && Number.parseFloat(match[4]) === 0
                ) {
                  return null;
                }
                return `#${match.slice(1, 4).map((part) => Number.parseInt(part, 10).toString(16).padStart(2, '0')).join('')}`;
              };
              const relativeLuminance = (hex) => {
                if (!hex || !hex.startsWith('#') || hex.length !== 7) {
                  return null;
                }
                const channels = [
                  Number.parseInt(hex.slice(1, 3), 16),
                  Number.parseInt(hex.slice(3, 5), 16),
                  Number.parseInt(hex.slice(5, 7), 16),
                ].map((value) => {
                  const normalized = value / 255;
                  return normalized <= 0.03928
                    ? normalized / 12.92
                    : Math.pow((normalized + 0.055) / 1.055, 2.4);
                });
                return (0.2126 * channels[0]) + (0.7152 * channels[1]) + (0.0722 * channels[2]);
              };
              const contrastRatio = (foreground, background) => {
                const foregroundHex = toHex(foreground);
                const backgroundHex = toHex(background);
                if (!foregroundHex || !backgroundHex) {
                  return null;
                }
                const foregroundLuminance = relativeLuminance(foregroundHex);
                const backgroundLuminance = relativeLuminance(backgroundHex);
                if (foregroundLuminance == null || backgroundLuminance == null) {
                  return null;
                }
                const lighter = Math.max(foregroundLuminance, backgroundLuminance);
                const darker = Math.min(foregroundLuminance, backgroundLuminance);
                return Number(((lighter + 0.05) / (darker + 0.05)).toFixed(2));
              };
              const visibleDialogs = Array.from(
                document.querySelectorAll('flt-semantics[role="dialog"]'),
              ).filter(isVisible);
              const dialog = visibleDialogs.find((candidate) =>
                normalize(candidate.innerText || candidate.textContent).includes('Workspace switcher'),
              );
              if (!dialog) {
                return null;
              }
              const interactiveSelector = [
                'flt-semantics[role="button"]',
                'button',
                '[role="button"]',
                'input',
                'textarea',
              ].join(',');
              const labelFor = (element) =>
                normalize(
                  element.getAttribute('aria-label')
                  || element.getAttribute('placeholder')
                  || element.innerText
                  || element.textContent
                  || '',
                );
              const resolveBackgroundColor = (element, fallback) => {
                let current = element;
                while (current && current !== document.body) {
                  const computedBackground = toHex(window.getComputedStyle(current).backgroundColor);
                  if (computedBackground) {
                    return computedBackground;
                  }
                  current = current.parentElement;
                }
                return fallback;
              };
              const resolveForegroundColor = (element) => {
                let current = element;
                while (current) {
                  const computedColor = toHex(window.getComputedStyle(current).color);
                  if (computedColor) {
                    return computedColor;
                  }
                  current = current.parentElement;
                }
                return null;
              };
              const rectPayload = (element) => {
                const rect = element.getBoundingClientRect();
                return {
                  x: rect.x,
                  y: rect.y,
                  width: rect.width,
                  height: rect.height,
                };
              };
              const interactiveElements = Array.from(
                dialog.querySelectorAll(interactiveSelector),
              )
                .filter(isVisible)
                .map((element) => ({
                  label: labelFor(element),
                  accessibleLabel: normalize(
                    element.getAttribute('aria-label')
                    || element.getAttribute('placeholder')
                    || '',
                  ),
                  role: element.getAttribute('role'),
                  tagName: element.tagName.toLowerCase(),
                  ...rectPayload(element),
                }));
              const missingInteractiveLabels = interactiveElements
                .filter((element) => element.label.length === 0)
                .map((element, index) =>
                  `${element.tagName}[${index}] role=${element.role ?? '<none>'}`,
                );
              const badgeLabels = new Set([
                'Hosted',
                'Local',
                'Needs sign-in',
                'Unavailable',
                'Read-only',
                'Connected',
                'Attachments limited',
                'Local Git',
                'Saved hosted workspace',
              ]);
              const dialogBackground = toHex(window.getComputedStyle(dialog).backgroundColor);
              const badgeElements = Array.from(dialog.querySelectorAll('*'))
                .filter(isVisible)
                .filter((element) => badgeLabels.has(normalize(element.innerText || element.textContent)))
                .filter((element) => {
                  const rect = element.getBoundingClientRect();
                  return rect.height <= 40 && rect.width <= 180;
                });
              const badges = badgeElements.map((element) => {
                const backgroundColor = resolveBackgroundColor(element, dialogBackground);
                const style = window.getComputedStyle(element);
                return {
                  label: normalize(element.innerText || element.textContent),
                  foregroundColor: toHex(style.color),
                  backgroundColor,
                  contrastRatio: contrastRatio(style.color, backgroundColor),
                  ...rectPayload(element),
                };
              });
              const workspaceTrigger = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              ).find((candidate) =>
                isVisible(candidate)
                && labelFor(candidate).startsWith('Workspace switcher:'),
              );
              const iconSelector = [
                'flt-semantics[role="img"]',
                '[role="img"]',
                'img',
                'svg',
                'canvas',
              ].join(',');
              const triggerAndDialogControls = [
                ...(workspaceTrigger ? [workspaceTrigger] : []),
                ...Array.from(dialog.querySelectorAll(interactiveSelector)).filter(isVisible),
              ];
              const interactiveIcons = triggerAndDialogControls.flatMap((element) => {
                const icons = Array.from(element.querySelectorAll(iconSelector)).filter(isVisible);
                const label = labelFor(element);
                if (!icons.length && !label.startsWith('Workspace switcher:') && label !== 'Delete') {
                  return [];
                }
                const iconElement = icons[0] ?? element;
                const backgroundColor = resolveBackgroundColor(
                  iconElement,
                  resolveBackgroundColor(element, dialogBackground),
                );
                const foregroundColor = resolveForegroundColor(iconElement);
                return [{
                  label,
                  foregroundColor,
                  backgroundColor,
                  contrastRatio: contrastRatio(foregroundColor, backgroundColor),
                  ...rectPayload(iconElement),
                }];
              });
              return {
                bodyText: document.body?.innerText ?? '',
                dialogVisible: true,
                headingText: normalize(dialog.innerText || dialog.textContent).split(' ')[0] === 'Workspace'
                  ? 'Workspace switcher'
                  : normalize(dialog.innerText || dialog.textContent),
                interactiveElements,
                missingInteractiveLabels,
                badges,
                interactiveIcons,
              };
            }
            """,
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The deployed app did not expose a readable workspace switcher surface.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return WorkspaceSwitcherSurfaceObservation(
            body_text=str(payload.get("bodyText", "")),
            dialog_visible=bool(payload.get("dialogVisible")),
            heading_text=str(payload.get("headingText", "")).strip(),
            interactive_elements=tuple(
                WorkspaceSwitcherInteractiveObservation(
                    label=str(item.get("label", "")),
                    accessible_label=str(item.get("accessibleLabel", "")),
                    role=str(item.get("role")) if item.get("role") is not None else None,
                    tag_name=str(item.get("tagName", "")),
                    x=float(item.get("x", 0.0)),
                    y=float(item.get("y", 0.0)),
                    width=float(item.get("width", 0.0)),
                    height=float(item.get("height", 0.0)),
                )
                for item in payload.get("interactiveElements", [])
            ),
            missing_interactive_labels=tuple(
                str(item) for item in payload.get("missingInteractiveLabels", [])
            ),
            badges=tuple(
                WorkspaceSwitcherBadgeObservation(
                    label=str(item.get("label", "")),
                    foreground_color=(
                        str(item.get("foregroundColor"))
                        if item.get("foregroundColor") is not None
                        else None
                    ),
                    background_color=(
                        str(item.get("backgroundColor"))
                        if item.get("backgroundColor") is not None
                        else None
                    ),
                    contrast_ratio=(
                        float(item.get("contrastRatio"))
                        if item.get("contrastRatio") is not None
                        else None
                    ),
                    x=float(item.get("x", 0.0)),
                    y=float(item.get("y", 0.0)),
                    width=float(item.get("width", 0.0)),
                    height=float(item.get("height", 0.0)),
                )
                for item in payload.get("badges", [])
            ),
            interactive_icons=tuple(
                WorkspaceSwitcherIconObservation(
                    label=str(item.get("label", "")),
                    foreground_color=(
                        str(item.get("foregroundColor"))
                        if item.get("foregroundColor") is not None
                        else None
                    ),
                    background_color=(
                        str(item.get("backgroundColor"))
                        if item.get("backgroundColor") is not None
                        else None
                    ),
                    contrast_ratio=(
                        float(item.get("contrastRatio"))
                        if item.get("contrastRatio") is not None
                        else None
                    ),
                    x=float(item.get("x", 0.0)),
                    y=float(item.get("y", 0.0)),
                    width=float(item.get("width", 0.0)),
                    height=float(item.get("height", 0.0)),
                )
                for item in payload.get("interactiveIcons", [])
            ),
        )

    def observe_mobile_trigger_focus(
        self,
        *,
        tab_count: int = 24,
        timeout_ms: int = 10_000,
    ) -> MobileTriggerFocusObservation:
        before = self._mobile_trigger_snapshot(timeout_ms=timeout_ms)
        steps: list[FocusNavigationStep] = []
        for step_index in range(1, tab_count + 1):
            active_before = self._session.active_element()
            self._session.press_key("Tab", timeout_ms=timeout_ms)
            active_after = self._session.active_element()
            steps.append(
                FocusNavigationStep(
                    step=step_index,
                    before_label=active_before.accessible_name,
                    before_role=active_before.role,
                    after_label=active_after.accessible_name,
                    after_role=active_after.role,
                    after_tag_name=active_after.tag_name,
                    after_outer_html=active_after.outer_html,
                )
            )
            if self._is_workspace_trigger_label(active_after.accessible_name):
                break
        after = self._mobile_trigger_snapshot(timeout_ms=timeout_ms)
        active = self._session.active_element()
        return MobileTriggerFocusObservation(
            trigger_label=str(before.get("triggerLabel", "")),
            trigger_text=str(before.get("triggerText", "")),
            trigger_x=float(before.get("triggerX", 0.0)),
            trigger_y=float(before.get("triggerY", 0.0)),
            trigger_width=float(before.get("triggerWidth", 0.0)),
            trigger_height=float(before.get("triggerHeight", 0.0)),
            before_outline=str(before.get("outline", "")),
            before_outline_color=str(before.get("outlineColor", "")),
            before_outline_width=str(before.get("outlineWidth", "")),
            before_box_shadow=str(before.get("boxShadow", "")),
            after_outline=str(after.get("outline", "")),
            after_outline_color=str(after.get("outlineColor", "")),
            after_outline_width=str(after.get("outlineWidth", "")),
            after_box_shadow=str(after.get("boxShadow", "")),
            active_label_after_focus=active.accessible_name,
            active_role_after_focus=active.role,
            active_tag_name_after_focus=active.tag_name,
            active_outer_html_after_focus=active.outer_html,
            focus_sequence=tuple(steps),
        )

    def _mobile_trigger_snapshot(
        self,
        *,
        timeout_ms: int,
    ) -> dict[str, object]:
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
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const trigger = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              ).find((candidate) =>
                isVisible(candidate)
                && normalize(candidate.getAttribute('aria-label') || candidate.innerText || candidate.textContent)
                  .startsWith('Workspace switcher:')
              );
              if (!trigger) {
                return null;
              }
              const describeTrigger = () => {
                const rect = trigger.getBoundingClientRect();
                const style = window.getComputedStyle(trigger);
                return {
                  triggerLabel: normalize(trigger.getAttribute('aria-label') || ''),
                  triggerText: normalize(trigger.innerText || trigger.textContent),
                  triggerX: rect.x,
                  triggerY: rect.y,
                  triggerWidth: rect.width,
                  triggerHeight: rect.height,
                  outline: style.outline,
                  outlineColor: style.outlineColor,
                  outlineWidth: style.outlineWidth,
                  boxShadow: style.boxShadow,
                };
              };
              return describeTrigger();
            }
            """,
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The mobile layout did not expose the condensed workspace switcher trigger.\n"
                f"Observed body text:\n{self.body_text()}",
            )
        return payload

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def body_text(self) -> str:
        return self._tracker_page.body_text()

    def _collect_tab_sequence(
        self,
        *,
        tab_count: int,
        timeout_ms: int,
    ) -> tuple[FocusNavigationStep, ...]:
        steps: list[FocusNavigationStep] = []
        for step_index in range(1, tab_count + 1):
            before = self._session.active_element()
            self._session.press_key("Tab", timeout_ms=timeout_ms)
            after = self._session.active_element()
            steps.append(
                FocusNavigationStep(
                    step=step_index,
                    before_label=before.accessible_name,
                    before_role=before.role,
                    after_label=after.accessible_name,
                    after_role=after.role,
                    after_tag_name=after.tag_name,
                    after_outer_html=after.outer_html,
                )
            )
        return tuple(steps)

    def _wait_for_surface(self, *, timeout_ms: int) -> None:
        try:
            self._session.wait_for_function(
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
                      && style.visibility !== 'hidden'
                      && style.display !== 'none';
                  };
                  return Array.from(document.querySelectorAll('flt-semantics[role="dialog"]'))
                    .filter(isVisible)
                    .some((dialog) =>
                      normalize(dialog.innerText || dialog.textContent).includes('Workspace switcher'),
                    )
                    ? true
                    : null;
                }
                """,
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            active = self._session.active_element()
            raise AssertionError(
                "The workspace switcher surface did not become visible.\n"
                f"Observed active element label: {active.accessible_name!r}\n"
                f"Observed active element role: {active.role!r}\n"
                f"Observed active element HTML: {active.outer_html}\n"
                f"Observed body text:\n{self.body_text()}",
            ) from error

    @staticmethod
    def _is_workspace_trigger_label(label: str | None) -> bool:
        return (label or "").startswith("Workspace switcher:")
