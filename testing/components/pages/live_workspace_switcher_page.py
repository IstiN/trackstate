from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from testing.components.pages.live_project_settings_page import LiveProjectSettingsPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import FocusedElementObservation, WebAppTimeoutError
from testing.core.utils.color_contrast import color_distance
from testing.core.utils.png_image import RgbImage


@dataclass(frozen=True)
class WorkspaceSwitcherRowObservation:
    display_name: str | None
    target_type_label: str | None
    state_label: str | None
    detail_text: str
    visible_text: str
    selected: bool
    semantics_label: str | None
    icon_accessibility_label: str | None
    action_labels: tuple[str, ...]
    button_labels: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceSwitcherObservation:
    body_text: str
    switcher_text: str
    row_count: int
    rows: tuple[WorkspaceSwitcherRowObservation, ...]


@dataclass(frozen=True)
class WorkspaceSwitcherTriggerObservation:
    viewport_width: float
    viewport_height: float
    semantic_label: str
    visible_text: str
    raw_text_lines: tuple[str, ...]
    display_name: str
    workspace_type: str
    state_label: str
    icon_count: int
    left: float
    top: float
    width: float
    height: float
    top_button_labels: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceSwitcherPanelObservation:
    viewport_width: float
    viewport_height: float
    title_text: str
    container_kind: str
    container_role: str | None
    container_text: str
    bright_change_pixels: int
    left: float
    top: float
    width: float
    height: float
    anchored_to_trigger: bool
    bottom_aligned: bool
    full_screen_like: bool
    background_dimmed: bool


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
class WorkspaceSwitcherSemanticsObservation:
    label: str
    role: str | None
    tag_name: str
    visible_text: str
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
class WorkspaceSwitcherInteractiveTextObservation:
    label: str
    visible_text: str
    role: str | None
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
    semantics_nodes: tuple[WorkspaceSwitcherSemanticsObservation, ...]
    missing_interactive_labels: tuple[str, ...]
    missing_semantics_labels: tuple[str, ...]
    badges: tuple[WorkspaceSwitcherBadgeObservation, ...]
    interactive_icons: tuple[WorkspaceSwitcherIconObservation, ...]
    interactive_texts: tuple[WorkspaceSwitcherInteractiveTextObservation, ...]


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
    _settings_page = LiveProjectSettingsPage
    _search_input_selector = 'input[aria-label="Search issues"]'
    _top_bar_button_selector = 'flt-semantics[role="button"]'
    _trigger_label_prefix = "Workspace switcher:"
    _button_selector = 'flt-semantics[role="button"]'
    _switcher_heading = "Workspace switcher"

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._project_settings_page = self._settings_page(tracker_page)

    def dismiss_connection_banner(self) -> None:
        self._project_settings_page.dismiss_connection_banner()

    def set_viewport(self, *, width: int, height: int, timeout_ms: int = 15_000) -> None:
        self._session.set_viewport_size(width=width, height=height)
        try:
            self._session.wait_for_function(
                """
                ({ expectedWidth, expectedHeight }) =>
                  window.innerWidth === expectedWidth
                  && window.innerHeight === expectedHeight
                """,
                arg={"expectedWidth": width, "expectedHeight": height},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f"Resizing the hosted browser to {width}x{height} did not settle to the "
                "requested viewport.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        self._session.mouse_move(1, 1)

    def navigate_to_section(self, label: str) -> None:
        clicked = self._session.evaluate(
            """
            (label) => {
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
              const candidate = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              ).find((element) => isVisible(element) && normalize(element.innerText) === label);
              if (!candidate) {
                return false;
              }
              candidate.click();
              return true;
            }
            """,
            arg=label,
        )
        if clicked is not True:
            raise AssertionError(
                f'The hosted tracker did not expose a visible "{label}" navigation entry.\n'
                f"Observed body text:\n{self.current_body_text()}",
            )
        try:
            self._session.wait_for_function(
                """
                (label) => {
                  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                  return Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                    .some((element) =>
                      normalize(element.innerText) === label
                      && element.getAttribute('aria-current') === 'true');
                }
                """,
                arg=label,
                timeout_ms=30_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Clicking the "{label}" navigation entry did not activate that section.\n'
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

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
              const labelFor = (element) =>
                normalize(
                  element.getAttribute?.('aria-label')
                  || element.getAttribute?.('placeholder')
                  || element.getAttribute?.('title')
                  || element.innerText
                  || element.textContent
                  || '',
                );
              const visibleTextFor = (element) =>
                normalize(element.innerText || element.textContent || '');
              const rectPayload = (element) => {
                const rect = element.getBoundingClientRect();
                return {
                  x: rect.x,
                  y: rect.y,
                  width: rect.width,
                  height: rect.height,
                };
              };
              const visibleDialogs = Array.from(
                document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
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
              const semanticsSelector = [
                'flt-semantics',
                '[role]',
                '[aria-label]',
                '[placeholder]',
                'button',
                'input',
                'textarea',
              ].join(',');
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
              const semanticsCandidates = [dialog, ...Array.from(dialog.querySelectorAll(semanticsSelector))]
                .filter(isVisible)
                .filter((element, index, all) => all.indexOf(element) === index);
              const semanticsNodes = semanticsCandidates
                .filter((element) => {
                  if (element === dialog) {
                    return true;
                  }
                  return !Array.from(element.querySelectorAll(semanticsSelector)).some((descendant) =>
                    descendant !== element && isVisible(descendant)
                  );
                })
                .map((element) => ({
                  label: labelFor(element),
                  role: element.getAttribute('role'),
                  tagName: element.tagName.toLowerCase(),
                  visibleText: visibleTextFor(element),
                  ...rectPayload(element),
                }));
              const missingSemanticsLabels = semanticsNodes
                .filter((node) => node.label.length === 0)
                .map((node, index) =>
                  `${node.tagName}[${index}] role=${node.role ?? '<none>'} text=${node.visibleText || '<none>'}`,
                );
              const interactiveTexts = Array.from(dialog.querySelectorAll(interactiveSelector))
                .filter(isVisible)
                .map((element) => {
                  const visibleText = visibleTextFor(element);
                  const backgroundColor = resolveBackgroundColor(
                    element,
                    toHex(window.getComputedStyle(dialog).backgroundColor),
                  );
                  const foregroundColor = resolveForegroundColor(element);
                  return {
                    label: labelFor(element),
                    visibleText,
                    role: element.getAttribute('role'),
                    foregroundColor,
                    backgroundColor,
                    contrastRatio: contrastRatio(foregroundColor, backgroundColor),
                    ...rectPayload(element),
                  };
                })
                .filter((element) => element.visibleText.length > 0);
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
                semanticsNodes,
                missingInteractiveLabels,
                missingSemanticsLabels,
                badges,
                interactiveIcons,
                interactiveTexts,
              };
            }
            """,
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The deployed app did not expose a readable workspace switcher surface.\n"
                f"Observed body text:\n{self.current_body_text()}",
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
            semantics_nodes=tuple(
                WorkspaceSwitcherSemanticsObservation(
                    label=str(item.get("label", "")),
                    role=str(item.get("role")) if item.get("role") is not None else None,
                    tag_name=str(item.get("tagName", "")),
                    visible_text=str(item.get("visibleText", "")),
                    x=float(item.get("x", 0.0)),
                    y=float(item.get("y", 0.0)),
                    width=float(item.get("width", 0.0)),
                    height=float(item.get("height", 0.0)),
                )
                for item in payload.get("semanticsNodes", [])
            ),
            missing_interactive_labels=tuple(
                str(item) for item in payload.get("missingInteractiveLabels", [])
            ),
            missing_semantics_labels=tuple(
                str(item) for item in payload.get("missingSemanticsLabels", [])
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
            interactive_texts=tuple(
                WorkspaceSwitcherInteractiveTextObservation(
                    label=str(item.get("label", "")),
                    visible_text=str(item.get("visibleText", "")),
                    role=str(item.get("role")) if item.get("role") is not None else None,
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
                for item in payload.get("interactiveTexts", [])
            ),
        )

    def open_and_observe(
        self,
        *,
        timeout_ms: int = 60_000,
    ) -> WorkspaceSwitcherObservation:
        self._click_trigger(timeout_ms=timeout_ms)
        payload = self._session.wait_for_function(
            """
            ({ heading }) => {
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
              const accessibleLabel = (element) =>
                normalize(
                  element?.getAttribute?.('aria-label')
                    || element?.getAttribute?.('alt')
                    || element?.getAttribute?.('title')
                    || element?.innerText
                    || ''
                );
              const dedupeRepeatedLine = (value) => {
                const normalized = normalize(value);
                const match = normalized.match(/^(.+)\\s+\\1$/);
                return match ? match[1] : normalized;
              };
              const visibleElements = (root, selector = '*') =>
                Array.from(root.querySelectorAll(selector)).filter((candidate) => isVisible(candidate));
              const bodyText = document.body?.innerText ?? '';
              if (!bodyText.includes(heading)) {
                return null;
              }

              let switcher = null;
              const dialogCandidates = visibleElements(
                document,
                'flt-semantics[role="dialog"],[role="dialog"]',
              )
                .map((element) => ({
                  element,
                  text: normalize(element.innerText || ''),
                  area: (() => {
                    const rect = element.getBoundingClientRect();
                    return rect.width * rect.height;
                  })(),
                }))
                .filter((candidate) => candidate.text.includes(heading))
                .sort((left, right) => left.area - right.area);
              if (dialogCandidates.length > 0) {
                switcher = dialogCandidates[0].element;
              }
              if (!switcher) {
                const headings = visibleElements(document)
                  .map((element) => ({
                    element,
                    label: normalize(element.getAttribute?.('aria-label') || ''),
                    text: normalize(element.innerText || ''),
                    area: (() => {
                      const rect = element.getBoundingClientRect();
                      return rect.width * rect.height;
                    })(),
                  }))
                  .filter((candidate) =>
                    candidate.label === heading
                    || candidate.text === heading
                    || (
                      candidate.text.includes(heading)
                      && (
                        candidate.text.includes('Saved workspaces')
                        || candidate.text.includes('Save and switch')
                        || candidate.text.includes('Hosted Local')
                      )
                    )
                  )
                  .sort((left, right) => left.area - right.area);

                for (const headingCandidate of headings) {
                  let current = headingCandidate.element;
                  while (current && current !== document.body) {
                    const text = normalize(current.innerText || '');
                    if (
                      text.includes(heading)
                      && (
                        text.includes('Saved workspaces')
                        || text.includes('Save and switch')
                        || text.includes('Hosted Local')
                      )
                    ) {
                      switcher = current;
                      break;
                    }
                    current = current.parentElement;
                  }
                  if (switcher) {
                    break;
                  }
                }
              }
              if (!switcher) {
                return null;
              }

              const actionLabels = ['Open', 'Open workspace', 'Active', 'Delete'];
              const stateLabels = [
                'Local Git',
                'Needs sign-in',
                'Connected',
                'Read-only',
                'Saved hosted workspace',
                'Unavailable',
                'Attachments limited',
              ];

              const rowCandidates = visibleElements(switcher)
                .map((element) => {
                  const text = normalize(element.innerText || '');
                  const rect = element.getBoundingClientRect();
                  const branchCount = (text.match(/Branch:/g) || []).length;
                  const deleteCount = (text.match(/Delete/g) || []).length;
                  return {
                    element,
                    text,
                    area: rect.width * rect.height,
                    branchCount,
                    deleteCount,
                  };
                })
                .filter((candidate) =>
                  candidate.branchCount === 1
                  && candidate.deleteCount === 1
                  && candidate.text.includes('Branch:')
                  && candidate.text.includes('Delete')
                  && (candidate.text.includes('Hosted') || candidate.text.includes('Local'))
                  && (candidate.text.includes('Open') || candidate.text.includes('Active'))
                )
                .filter((candidate) => candidate)
                .sort((left, right) => left.area - right.area);

              const rows = [];
              for (const candidate of rowCandidates) {
                if (rows.some((accepted) => accepted.element.contains(candidate.element))) {
                  continue;
                }
                rows.push(candidate);
              }

              return {
                bodyText,
                switcherText: normalize(switcher.innerText || ''),
                rows: rows.map((rowCandidate) => {
                  const rowElement = rowCandidate.element;
                  const rawLines = (rowElement.innerText || '')
                    .split(/\\n+/)
                    .map((line) => dedupeRepeatedLine(line))
                    .filter((line) => line.length > 0 && line !== heading && line !== 'Saved workspaces');
                  const rowActionLabels = rawLines.filter((line) => actionLabels.includes(line));
                  const contentLines = rawLines.filter((line) => !actionLabels.includes(line));
                  const typeLabel =
                    contentLines.find((line) => line === 'Hosted' || line === 'Local') ?? null;
                  const stateLabel =
                    contentLines.find((line) => stateLabels.includes(line)) ?? null;
                  const detailText =
                    contentLines.find((line) => line.includes('Branch:')) ?? '';
                  const displayName =
                    contentLines.find((line) =>
                      line !== typeLabel
                      && line !== stateLabel
                      && line !== detailText
                    ) ?? null;
                  const semanticsLabels = [rowElement, ...visibleElements(rowElement, 'flt-semantics[aria-label],[aria-label]')]
                    .map((element) => dedupeRepeatedLine(element.getAttribute('aria-label') || ''))
                    .filter((label) =>
                      label.length > 0
                      && label !== 'repository'
                      && label !== 'folder'
                      && !actionLabels.includes(label)
                    );
                  const iconLabel =
                    [rowElement, ...visibleElements(rowElement, 'flt-semantics[aria-label],[aria-label]')]
                      .map((element) => dedupeRepeatedLine(element.getAttribute('aria-label') || ''))
                      .find((label) => label === 'repository' || label === 'folder')
                    ?? null;
                  const buttonLabels = visibleElements(
                    rowElement,
                    'flt-semantics[role="button"],[role="button"],button',
                  )
                    .map((element) => accessibleLabel(element) || normalize(element.innerText || ''))
                    .filter((label) => label.length > 0);
                  const visibleText = normalize(rowElement.innerText || '');
                  return {
                    displayName,
                    targetTypeLabel: typeLabel,
                    stateLabel,
                    detailText,
                    visibleText,
                    selected: visibleText.includes('Active'),
                    semanticsLabel: semanticsLabels[0] ?? null,
                    iconAccessibilityLabel: iconLabel,
                    actionLabels: rowActionLabels,
                    buttonLabels,
                  };
                }),
              };
            }
            """,
            arg={"heading": self._switcher_heading},
            timeout_ms=timeout_ms,
        )
        rows = tuple(
            WorkspaceSwitcherRowObservation(
                display_name=row.get("displayName"),
                target_type_label=row.get("targetTypeLabel"),
                state_label=row.get("stateLabel"),
                detail_text=str(row.get("detailText", "")),
                visible_text=str(row.get("visibleText", "")),
                selected=bool(row.get("selected")),
                semantics_label=row.get("semanticsLabel"),
                icon_accessibility_label=row.get("iconAccessibilityLabel"),
                action_labels=tuple(str(label) for label in row.get("actionLabels", [])),
                button_labels=tuple(str(label) for label in row.get("buttonLabels", [])),
            )
            for row in payload.get("rows", [])
        )
        if not rows:
            rows = _rows_from_switcher_text(str(payload.get("switcherText", "")))
        return WorkspaceSwitcherObservation(
            body_text=str(payload.get("bodyText", "")),
            switcher_text=str(payload.get("switcherText", "")),
            row_count=len(rows),
            rows=rows,
        )

    def close(self, *, timeout_ms: int = 15_000) -> None:
        if self._session.count('flt-semantics[role="dialog"],[role="dialog"]') == 0:
            return
        self._session.press_key("Escape")
        try:
            self._session.wait_for_function(
                """
                () => {
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
                  return !Array.from(
                    document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
                  ).some((candidate) => isVisible(candidate));
                }
                """,
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Closing the Workspace switcher did not dismiss the dialog.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def observe_trigger(self, *, timeout_ms: int = 30_000) -> WorkspaceSwitcherTriggerObservation:
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
              const labelFor = (element) =>
                normalize(element.getAttribute('aria-label') || element.innerText || '');
              const buttons = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              ).filter(isVisible);
              const trigger = buttons
                .filter((element) => labelFor(element).includes('Workspace switcher:'))
                .sort((left, right) => {
                  const leftRect = left.getBoundingClientRect();
                  const rightRect = right.getBoundingClientRect();
                  return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                })[0] ?? null;
              if (!trigger) {
                return null;
              }
              const rect = trigger.getBoundingClientRect();
              const rawText = (trigger.innerText || '').trim();
              const rawTextLines = rawText
                .split(/\\n+/)
                .map(normalize)
                .filter((line) => line.length > 0);
              const iconCount = Array.from(
                trigger.querySelectorAll('canvas,img,svg,[role="img"],flt-semantics[role="img"]'),
              ).filter(isVisible).length;
              return {
                viewportWidth: window.innerWidth,
                viewportHeight: window.innerHeight,
                semanticLabel: labelFor(trigger),
                visibleText: normalize(rawText),
                rawTextLines,
                iconCount,
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height,
                topButtonLabels: buttons
                  .filter((element) => element.getBoundingClientRect().top < 160)
                  .map((element) => labelFor(element))
                  .filter((label) => label.length > 0),
              };
            }
            """,
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The live app did not expose a visible workspace switcher trigger.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        semantic_label = str(payload["semanticLabel"])
        match = re.match(
            r"^Workspace switcher:\s*(.*?),\s*(Hosted|Local),\s*(.+)$",
            semantic_label,
        )
        display_name = match.group(1).strip() if match else ""
        workspace_type = match.group(2).strip() if match else ""
        state_label = match.group(3).strip() if match else ""
        return WorkspaceSwitcherTriggerObservation(
            viewport_width=float(payload["viewportWidth"]),
            viewport_height=float(payload["viewportHeight"]),
            semantic_label=semantic_label,
            visible_text=str(payload["visibleText"]),
            raw_text_lines=tuple(str(line) for line in payload["rawTextLines"]),
            display_name=display_name,
            workspace_type=workspace_type,
            state_label=state_label,
            icon_count=int(payload["iconCount"]),
            left=float(payload["left"]),
            top=float(payload["top"]),
            width=float(payload["width"]),
            height=float(payload["height"]),
            top_button_labels=tuple(str(label) for label in payload["topButtonLabels"]),
        )

    def open_switcher(self, *, timeout_ms: int = 30_000) -> None:
        try:
            self._session.click(
                'flt-semantics[role="button"]',
                has_text="Workspace switcher:",
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "The live app did not expose a clickable workspace switcher trigger.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def observe_panel(
        self,
        trigger: WorkspaceSwitcherTriggerObservation,
        *,
        before_screenshot_path: Path,
        after_screenshot_path: Path,
    ) -> WorkspaceSwitcherPanelObservation:
        before = RgbImage.open(before_screenshot_path)
        after = RgbImage.open(after_screenshot_path)
        if before.width != after.width or before.height != after.height:
            raise AssertionError(
                "The workspace switcher screenshots did not use the same viewport.\n"
                f"Before screenshot: {before.width}x{before.height}\n"
                f"After screenshot: {after.width}x{after.height}",
            )
        surface_box = _bright_surface_box(before=before, after=after)
        if surface_box is None:
            raise AssertionError(
                "Activating the workspace switcher did not render any visible switcher "
                "surface.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        left, top, right, bottom, bright_change_pixels = surface_box
        width = float(right - left)
        height = float(bottom - top)
        viewport_width = trigger.viewport_width
        viewport_height = trigger.viewport_height
        right = left + width
        trigger_right = trigger.left + trigger.width
        trigger_bottom = trigger.top + trigger.height
        anchored_to_trigger = (
            top >= (trigger_bottom - 12)
            and top <= (trigger_bottom + 96)
            and (
                abs(left - trigger.left) <= 56
                or abs(right - trigger_right) <= 96
                or abs((left + (width / 2)) - (trigger.left + (trigger.width / 2))) <= 120
            )
            and width <= min(760.0, viewport_width * 0.8)
        )
        bottom_aligned = (top + height) >= (viewport_height - 24)
        full_screen_like = (
            top <= 40
            and left <= 12
            and width >= viewport_width * 0.96
            and height >= viewport_height * 0.8
        )
        background_dimmed = _background_dimmed(before=before, after=after)
        centered_dialog = (
            abs((left + (width / 2)) - (viewport_width / 2)) <= viewport_width * 0.12
            and top >= 40
            and bottom <= (viewport_height - 40)
            and width >= viewport_width * 0.3
            and width <= viewport_width * 0.85
            and height >= viewport_height * 0.25
            and background_dimmed
        )
        if full_screen_like:
            container_kind = "full-screen-sheet"
        elif (
            bottom_aligned
            and left <= 12
            and width >= viewport_width * 0.96
            and height >= viewport_height * 0.3
        ):
            container_kind = "bottom-sheet"
        elif centered_dialog:
            container_kind = "dialog"
        elif anchored_to_trigger:
            container_kind = "anchored-panel"
        else:
            container_kind = "surface"
        return WorkspaceSwitcherPanelObservation(
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            title_text="",
            container_kind=container_kind,
            container_role=None,
            container_text=(
                "Rendered workspace switcher surface detected from screenshot diff."
            ),
            bright_change_pixels=bright_change_pixels,
            left=left,
            top=top,
            width=width,
            height=height,
            anchored_to_trigger=anchored_to_trigger,
            bottom_aligned=bottom_aligned,
            full_screen_like=full_screen_like,
            background_dimmed=background_dimmed,
        )

    def close_switcher(self) -> None:
        try:
            self._session.press_key("Escape", timeout_ms=10_000)
        except WebAppTimeoutError:
            return

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

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def body_text(self) -> str:
        return self.current_body_text()

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

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
            }
            """,
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The mobile layout did not expose the condensed workspace switcher trigger.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return payload

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
                  return Array.from(
                    document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
                  )
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
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    @staticmethod
    def _is_workspace_trigger_label(label: str | None) -> bool:
        return (label or "").startswith("Workspace switcher:")

    def _click_trigger(self, *, timeout_ms: int) -> None:
        self._session.click(
            self._button_selector,
            has_text=self._trigger_label_prefix,
            timeout_ms=timeout_ms,
        )


def _bright_surface_box(
    *,
    before: RgbImage,
    after: RgbImage,
) -> tuple[float, float, float, float, int] | None:
    minimum_brightness = 225.0
    minimum_pixels = max(1_500, int((after.width * after.height) * 0.004))
    min_x = after.width
    min_y = after.height
    max_x = -1
    max_y = -1
    bright_pixels = 0
    for y in range(after.height):
        for x in range(after.width):
            index = (y * after.width) + x
            after_pixel = after.pixels[index]
            before_pixel = before.pixels[index]
            if color_distance(after_pixel, before_pixel) <= 18.0:
                continue
            brightness = (after_pixel[0] + after_pixel[1] + after_pixel[2]) / 3
            if brightness < minimum_brightness:
                continue
            bright_pixels += 1
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y
    if bright_pixels < minimum_pixels or max_x < min_x or max_y < min_y:
        return None
    return (float(min_x), float(min_y), float(max_x + 1), float(max_y + 1), bright_pixels)


def _background_dimmed(*, before: RgbImage, after: RgbImage) -> bool:
    darker_pixels = 0
    for before_pixel, after_pixel in zip(before.pixels, after.pixels):
        before_brightness = sum(before_pixel) / 3
        after_brightness = sum(after_pixel) / 3
        if (before_brightness - after_brightness) >= 12 and color_distance(before_pixel, after_pixel) >= 14:
            darker_pixels += 1
    return darker_pixels >= int((after.width * after.height) * 0.08)


def _rows_from_switcher_text(switcher_text: str) -> tuple[WorkspaceSwitcherRowObservation, ...]:
    normalized = " ".join(switcher_text.split())
    if not normalized:
        return ()
    normalized = normalized.replace("Workspace switcher Workspace switcher ", "", 1)
    for trailer in (" Hosted Local Save and switch", " Save and switch"):
        if trailer in normalized:
            normalized = normalized.split(trailer, 1)[0].strip()
            break
    chunk_pattern = re.compile(r".+? Delete(?= .+? Delete|$)")
    states = (
        "Attachments limited",
        "Saved hosted workspace",
        "Needs sign-in",
        "Read-only",
        "Connected",
        "Unavailable",
        "Local Git",
    )
    rows: list[WorkspaceSwitcherRowObservation] = []
    for chunk_match in chunk_pattern.finditer(normalized):
        chunk = chunk_match.group(0).strip()
        action = "Open workspace" if chunk.endswith("Open workspace Delete") else "Open" if chunk.endswith("Open Delete") else "Active"
        suffix = f" {action} Delete"
        if not chunk.endswith(suffix):
            continue
        chunk_without_action = chunk[: -len(suffix)].strip()
        target_type = None
        state_label = None
        for candidate_state in states:
            for candidate_type in ("Hosted", "Local"):
                candidate_suffix = f" {candidate_type} {candidate_state}"
                if chunk_without_action.endswith(candidate_suffix):
                    target_type = candidate_type
                    state_label = candidate_state
                    chunk_without_action = chunk_without_action[: -len(candidate_suffix)].strip()
                    break
            if target_type is not None:
                break
        if target_type is None or state_label is None:
            continue
        detail_match = re.search(
            r"(?P<detail>\S+\s+•\s+Branch:\s+\S+(?:\s+•\s+Write\s+Branch:\s+\S+)?)$",
            chunk_without_action,
        )
        if detail_match is None:
            continue
        detail_text = detail_match.group("detail").strip()
        target = detail_text.split(" • Branch:", 1)[0].strip()
        display_name = chunk_without_action[: detail_match.start()].strip() or target
        button_labels = ("Delete",) if action == "Active" else (action, "Delete")
        rows.append(
            WorkspaceSwitcherRowObservation(
                display_name=display_name,
                target_type_label=target_type,
                state_label=state_label,
                detail_text=detail_text,
                visible_text=f"{display_name} {detail_text} {target_type} {state_label} {action} Delete",
                selected=action == "Active",
                semantics_label=None,
                icon_accessibility_label=None,
                action_labels=((action,) if action == "Active" else (action,)),
                button_labels=button_labels,
            ),
        )
    return tuple(rows)
