from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from testing.components.pages.live_project_settings_page import LiveProjectSettingsPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import (
    ElementBoundingBox,
    FocusedElementObservation,
    WebAppTimeoutError,
)
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
class WorkspaceSwitcherSavedWorkspaceRowObservation:
    display_name: str
    target_type_label: str | None
    state_label: str | None
    detail_text: str
    selected: bool
    action_labels: tuple[str, ...]
    left: float
    top: float
    width: float
    height: float


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
class WorkspaceTriggerFocusabilityObservation:
    label: str
    role: str | None
    tag_name: str
    tabindex: str | None
    keyboard_focusable: bool
    outer_html: str


@dataclass(frozen=True)
class WorkspaceTriggerAriaExpandedObservation:
    label: str
    role: str | None
    tag_name: str
    tabindex: str | None
    keyboard_focusable: bool
    aria_expanded: str | None
    outer_html: str


@dataclass(frozen=True)
class WorkspaceTriggerAriaControlsObservation:
    label: str
    role: str | None
    tag_name: str
    tabindex: str | None
    keyboard_focusable: bool
    aria_controls: str | None
    outer_html: str


@dataclass(frozen=True)
class WorkspaceTriggerAriaControlsTargetObservation:
    trigger_label: str
    trigger_aria_controls: str | None
    controlled_element_found: bool
    controlled_element_visible: bool
    controlled_element_id: str | None
    controlled_element_role: str | None
    controlled_element_tag_name: str | None
    controlled_element_text: str
    trigger_outer_html: str
    controlled_element_outer_html: str


@dataclass(frozen=True)
class WorkspaceSwitcherSurfaceReferenceObservation:
    trigger_label: str
    trigger_aria_controls: str | None
    controlled_surface_found: bool
    controlled_surface_visible: bool
    controlled_surface_id: str | None
    controlled_surface_role: str | None
    controlled_surface_tag_name: str | None
    controlled_surface_text: str
    visible_surface_id: str | None
    visible_surface_role: str | None
    visible_surface_tag_name: str | None
    visible_surface_text: str
    trigger_outer_html: str
    visible_surface_outer_html: str


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
class BackgroundScrollObservation:
    scroll_y: float
    viewport_height: float
    scroll_height: float
    max_scroll_y: float


@dataclass(frozen=True)
class WorkspaceSwitcherInternalClickObservation:
    click_x: float
    click_y: float
    panel_left: float
    panel_top: float
    panel_width: float
    panel_height: float
    target_tag_name: str
    target_role: str | None
    target_label: str
    target_text: str


@dataclass(frozen=True)
class WorkspaceSwitcherOutsideDismissObservation:
    click_x: float
    click_y: float
    body_text: str
    dashboard_visible: bool
    trigger_visible: bool


@dataclass(frozen=True)
class WorkspaceSwitcherBlurDismissObservation:
    before_focus_label: str | None
    before_focus_role: str | None
    before_focus_tag_name: str
    before_focus_outer_html: str
    before_focus_visible: bool
    before_focus_in_viewport: bool
    before_focus_within_switcher: bool
    before_focus_on_trigger: bool
    before_focus_owned_by_switcher: bool
    after_focus_label: str | None
    after_focus_role: str | None
    after_focus_tag_name: str
    after_focus_outer_html: str
    after_focus_visible: bool
    after_focus_in_viewport: bool
    after_focus_different_from_before: bool
    after_focus_within_switcher: bool
    external_focus_reached: bool
    panel_visible_after_wait: bool
    panel_text_after_wait: str
    dashboard_visible_after_wait: bool
    trigger_visible_after_wait: bool
    waited_ms: int

@dataclass(frozen=True)
class WorkspaceSwitcherTriggerDismissObservation:
    body_text: str
    dashboard_visible: bool
    trigger_visible: bool
    trigger_label: str | None


@dataclass(frozen=True)
class WorkspaceSwitcherEscapeDismissObservation:
    body_text: str
    dashboard_visible: bool
    trigger_visible: bool


@dataclass(frozen=True)
class WorkspaceSwitcherTransitionMonitorObservation:
    sample_count: int
    visible_sample_count: int
    hidden_sample_count: int
    ever_hidden_after_visible: bool
    observed_container_kinds: tuple[str, ...]
    observed_row_counts: tuple[int, ...]
    observed_active_workspace_names: tuple[str, ...]
    latest_visible_container_kind: str | None
    latest_visible_row_count: int | None
    latest_visible_active_workspace_name: str | None


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
class WorkspaceSwitcherInternalFocusObservation:
    before_label: str | None
    before_role: str | None
    before_tag_name: str
    before_outer_html: str
    before_visible: bool
    before_in_viewport: bool
    before_within_switcher: bool
    before_on_trigger: bool
    before_owned_by_switcher: bool
    after_label: str | None
    after_role: str | None
    after_tag_name: str
    after_outer_html: str
    after_visible: bool
    after_in_viewport: bool
    after_within_switcher: bool
    after_on_trigger: bool
    after_owned_by_switcher: bool
    after_different_from_before: bool


@dataclass(frozen=True)
class WorkspaceSwitcherFocusOwnershipObservation:
    active_label: str | None
    active_role: str | None
    active_tag_name: str
    active_outer_html: str
    active_visible: bool
    active_in_viewport: bool
    switcher_focus_within: bool
    active_within_switcher: bool
    active_on_trigger: bool
    focus_owned_by_switcher: bool


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
class WorkspaceSwitcherFocusTargetObservation:
    active_label: str | None
    active_role: str | None
    active_tag_name: str
    active_outer_html: str
    active_visible: bool
    active_in_viewport: bool
    active_within_switcher: bool
    active_on_trigger: bool
    focus_owned_by_switcher: bool


@dataclass(frozen=True)
class WorkspaceSwitcherRowFocusObservation:
    active_label: str | None
    active_role: str | None
    active_tag_name: str
    active_outer_html: str
    active_visible: bool
    active_in_viewport: bool
    active_within_switcher: bool
    active_on_trigger: bool
    focus_owned_by_switcher: bool
    row_found: bool
    row_contains_active: bool
    row_text: str


@dataclass(frozen=True)
class WorkspaceSwitcherButtonFocusabilityObservation:
    label: str
    visible_text: str
    role: str | None
    tag_name: str
    tabindex: str | None
    keyboard_focusable: bool
    active_within: bool
    outer_html: str


@dataclass(frozen=True)
class WorkspaceSwitcherButtonStateObservation:
    label: str
    visible_text: str
    role: str | None
    tag_name: str
    tabindex: str | None
    tab_index_value: int
    aria_disabled: str | None
    disabled: bool
    keyboard_focusable: bool
    active_within: bool
    outer_html: str


@dataclass(frozen=True)
class WorkspaceSwitcherTabStopObservation:
    label: str
    visible_text: str
    role: str | None
    tag_name: str
    tabindex: str | None
    tab_index_value: int
    dom_index: int
    keyboard_focusable: bool
    disabled: bool
    outer_html: str


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


def _merge_surface_payload_items(
    primary_items: list[dict[str, object]],
    panel_scoped_items: list[dict[str, object]],
) -> list[dict[str, object]]:
    merged = list(primary_items)
    for panel_item in panel_scoped_items:
        label = str(panel_item.get("label", "")).strip()
        if not label:
            continue
        if any(_surface_payload_items_match(item, panel_item) for item in merged):
            continue
        merged.append(dict(panel_item))
    return merged


def _surface_payload_items_match(
    left: dict[str, object],
    right: dict[str, object],
) -> bool:
    left_label = str(left.get("label", "")).strip()
    right_label = str(right.get("label", "")).strip()
    if left_label != right_label:
        return False
    left_tag = str(left.get("tagName", "")).strip()
    right_tag = str(right.get("tagName", "")).strip()
    if left_tag != right_tag:
        return False
    left_role = str(left.get("role", "")).strip()
    right_role = str(right.get("role", "")).strip()
    if left_role != right_role:
        return False
    return (
        abs(float(left.get("x", 0.0)) - float(right.get("x", 0.0))) < 1
        and abs(float(left.get("y", 0.0)) - float(right.get("y", 0.0))) < 1
        and abs(float(left.get("width", 0.0)) - float(right.get("width", 0.0))) < 1
        and abs(float(left.get("height", 0.0)) - float(right.get("height", 0.0))) < 1
    )


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


@dataclass(frozen=True)
class WorkspaceTriggerForwardFocusObservation:
    trigger_label: str
    trigger_text: str
    starting_focus_label: str | None
    starting_focus_role: str | None
    starting_focus_tag_name: str
    next_focus_label: str | None
    next_focus_role: str | None
    next_focus_tag_name: str
    next_focus_outer_html: str
    next_focus_visible: bool
    next_focus_in_viewport: bool


@dataclass(frozen=True)
class WorkspaceTriggerReverseFocusObservation:
    trigger_label: str
    trigger_text: str
    starting_focus_label: str | None
    starting_focus_role: str | None
    starting_focus_tag_name: str
    starting_focus_outer_html: str
    before_reverse_outline: str
    before_reverse_outline_color: str
    before_reverse_outline_width: str
    before_reverse_box_shadow: str
    before_reverse_focus_visible: bool
    before_reverse_trigger_focused: bool
    after_reverse_outline: str
    after_reverse_outline_color: str
    after_reverse_outline_width: str
    after_reverse_box_shadow: str
    after_reverse_focus_visible: bool
    after_reverse_trigger_focused: bool
    restored_focus_label: str | None
    restored_focus_role: str | None
    restored_focus_tag_name: str
    restored_focus_outer_html: str


@dataclass(frozen=True)
class WorkspaceTriggerKeyboardFocusObservation:
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


@dataclass(frozen=True)
class WorkspaceTriggerFocusStateObservation:
    trigger_label: str
    trigger_text: str
    outline: str
    outline_color: str
    outline_width: str
    box_shadow: str
    focus_visible: bool
    is_focused: bool


class LiveWorkspaceSwitcherPage:
    _settings_page = LiveProjectSettingsPage
    _search_input_selector = 'input[aria-label="Search issues"]'
    _top_bar_button_selector = 'button, flt-semantics[role="button"], [role="button"]'
    _first_top_bar_control_label = "Create issue"
    _trigger_label_prefix = "Workspace switcher:"
    _button_selector = 'button, flt-semantics[role="button"], [role="button"]'
    _workspace_trigger_selector = '[aria-label^="Workspace switcher:"]'
    _switcher_heading = "Workspace switcher"

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._project_settings_page = self._settings_page(tracker_page)

    def _switcher_text_field_selector(self, label: str) -> str:
        return f'input[aria-label="{label}"]'

    def dismiss_connection_banner(self) -> None:
        self._project_settings_page.dismiss_connection_banner()

    def dismiss_project_settings_surface(self, *, timeout_ms: int = 30_000) -> None:
        self._project_settings_page.dismiss_if_open(timeout_ms=timeout_ms)

    def open_startup_entrypoint(
        self,
        *,
        wait_until: str = "commit",
        timeout_ms: int = 120_000,
    ) -> None:
        self._tracker_page.open_entrypoint(
            wait_until=wait_until,
            timeout_ms=timeout_ms,
        )

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

    def observe_background_scroll(self) -> BackgroundScrollObservation:
        payload = self._session.evaluate(
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
              const candidateScore = (candidate) => {
                const area = candidate.rect.width * candidate.rect.height;
                const overflowBonus =
                  candidate.overflowY === 'scroll' || candidate.overflowY === 'auto'
                    ? 1_000_000
                    : 0;
                return overflowBonus + area + candidate.scrollHeight;
              };
              const windowScrollHeight = Math.max(
                document.scrollingElement?.scrollHeight || 0,
                document.documentElement?.scrollHeight || 0,
                document.body?.scrollHeight || 0,
              );
              const windowViewportHeight =
                window.innerHeight || document.documentElement?.clientHeight || 0;
              const windowScrollY =
                window.scrollY
                || window.pageYOffset
                || document.scrollingElement?.scrollTop
                || document.documentElement?.scrollTop
                || document.body?.scrollTop
                || 0;
              const windowMaxScrollY = Math.max(0, windowScrollHeight - windowViewportHeight);
              const elementCandidates = Array.from(document.querySelectorAll('*'))
                .filter(isVisible)
                .map((element) => {
                  const rect = element.getBoundingClientRect();
                  const style = window.getComputedStyle(element);
                  return {
                    scrollTop: element.scrollTop || 0,
                    clientHeight: element.clientHeight || 0,
                    scrollHeight: element.scrollHeight || 0,
                    overflowY: style.overflowY,
                    text: normalize(element.innerText || element.textContent || ''),
                    rect: {
                      width: rect.width,
                      height: rect.height,
                    },
                  };
                })
                .filter((candidate) =>
                  candidate.scrollHeight - candidate.clientHeight > 40
                  && candidate.rect.width >= Math.min(window.innerWidth * 0.35, 280)
                  && candidate.rect.height >= Math.min(window.innerHeight * 0.35, 200)
                  && !candidate.text.startsWith('Workspace switcher'),
                )
                .sort((left, right) => candidateScore(right) - candidateScore(left));
              const bestCandidate = elementCandidates[0] || null;
              const scrollingElement =
                document.scrollingElement || document.documentElement || document.body;
              const useWindow =
                windowMaxScrollY > 0
                || bestCandidate === null
                || (windowMaxScrollY >= Math.max(80, (bestCandidate.scrollHeight - bestCandidate.clientHeight)));
              const scrollHeight = useWindow
                ? Math.max(
                    scrollingElement?.scrollHeight || 0,
                    document.documentElement?.scrollHeight || 0,
                    document.body?.scrollHeight || 0,
                  )
                : bestCandidate.scrollHeight;
              const viewportHeight = useWindow
                ? (window.innerHeight || document.documentElement?.clientHeight || 0)
                : bestCandidate.clientHeight;
              const scrollY = useWindow
                ? (
                    window.scrollY
                    || window.pageYOffset
                    || scrollingElement?.scrollTop
                    || 0
                  )
                : bestCandidate.scrollTop;
              return {
                scrollY,
                viewportHeight,
                scrollHeight,
                maxScrollY: Math.max(0, scrollHeight - viewportHeight),
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The hosted tracker did not expose readable background scroll metrics.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return BackgroundScrollObservation(
            scroll_y=float(payload.get("scrollY", 0.0)),
            viewport_height=float(payload.get("viewportHeight", 0.0)),
            scroll_height=float(payload.get("scrollHeight", 0.0)),
            max_scroll_y=float(payload.get("maxScrollY", 0.0)),
        )

    def scroll_background_to(
        self,
        *,
        y: float,
        timeout_ms: int = 15_000,
    ) -> BackgroundScrollObservation:
        payload = self._session.evaluate(
            """
            (targetY) => {
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
              const candidateScore = (candidate) => {
                const area = candidate.rect.width * candidate.rect.height;
                const overflowBonus =
                  candidate.overflowY === 'scroll' || candidate.overflowY === 'auto'
                    ? 1_000_000
                    : 0;
                return overflowBonus + area + candidate.scrollHeight;
              };
              const scrollingElement =
                document.scrollingElement || document.documentElement || document.body;
              const windowScrollHeight = Math.max(
                scrollingElement?.scrollHeight || 0,
                document.documentElement?.scrollHeight || 0,
                document.body?.scrollHeight || 0,
              );
              const windowViewportHeight =
                window.innerHeight || document.documentElement?.clientHeight || 0;
              const windowMaxScrollY = Math.max(0, windowScrollHeight - windowViewportHeight);
              const elementCandidates = Array.from(document.querySelectorAll('*'))
                .filter(isVisible)
                .map((element) => {
                  const rect = element.getBoundingClientRect();
                  const style = window.getComputedStyle(element);
                  return {
                    element,
                    scrollHeight: element.scrollHeight || 0,
                    clientHeight: element.clientHeight || 0,
                    overflowY: style.overflowY,
                    text: normalize(element.innerText || element.textContent || ''),
                    rect: {
                      width: rect.width,
                      height: rect.height,
                    },
                  };
                })
                .filter((candidate) =>
                  candidate.scrollHeight - candidate.clientHeight > 40
                  && candidate.rect.width >= Math.min(window.innerWidth * 0.35, 280)
                  && candidate.rect.height >= Math.min(window.innerHeight * 0.35, 200)
                  && !candidate.text.startsWith('Workspace switcher'),
                )
                .sort((left, right) => candidateScore(right) - candidateScore(left));
              const bestCandidate = elementCandidates[0] || null;
              const useWindow =
                windowMaxScrollY > 0
                || bestCandidate === null
                || (windowMaxScrollY >= Math.max(80, (bestCandidate.scrollHeight - bestCandidate.clientHeight)));
              const scrollHeight = useWindow
                ? windowScrollHeight
                : bestCandidate.scrollHeight;
              const viewportHeight = useWindow
                ? windowViewportHeight
                : bestCandidate.clientHeight;
              const maxScrollY = Math.max(0, scrollHeight - viewportHeight);
              const clampedY = Math.min(Math.max(Number(targetY) || 0, 0), maxScrollY);
              if (useWindow) {
                window.scrollTo({ top: clampedY, behavior: 'instant' });
              } else {
                bestCandidate.element.scrollTop = clampedY;
              }
              return {
                expectedScrollY: clampedY,
              };
            }
            """,
            arg=float(y),
        )
        expected_scroll_y = (
            float(payload.get("expectedScrollY", 0.0))
            if isinstance(payload, dict)
            else float(y)
        )
        try:
            self._session.wait_for_function(
                """
                ({ expectedScrollY }) => {
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
                  const candidateScore = (candidate) => {
                    const area = candidate.rect.width * candidate.rect.height;
                    const overflowBonus =
                      candidate.overflowY === 'scroll' || candidate.overflowY === 'auto'
                        ? 1_000_000
                        : 0;
                    return overflowBonus + area + candidate.scrollHeight;
                  };
                  const scrollingElement =
                    document.scrollingElement || document.documentElement || document.body;
                  const windowScrollHeight = Math.max(
                    scrollingElement?.scrollHeight || 0,
                    document.documentElement?.scrollHeight || 0,
                    document.body?.scrollHeight || 0,
                  );
                  const windowViewportHeight =
                    window.innerHeight || document.documentElement?.clientHeight || 0;
                  const windowMaxScrollY = Math.max(0, windowScrollHeight - windowViewportHeight);
                  const elementCandidates = Array.from(document.querySelectorAll('*'))
                    .filter(isVisible)
                    .map((element) => {
                      const rect = element.getBoundingClientRect();
                      const style = window.getComputedStyle(element);
                      return {
                        scrollTop: element.scrollTop || 0,
                        scrollHeight: element.scrollHeight || 0,
                        clientHeight: element.clientHeight || 0,
                        overflowY: style.overflowY,
                        text: normalize(element.innerText || element.textContent || ''),
                        rect: {
                          width: rect.width,
                          height: rect.height,
                        },
                      };
                    })
                    .filter((candidate) =>
                      candidate.scrollHeight - candidate.clientHeight > 40
                      && candidate.rect.width >= Math.min(window.innerWidth * 0.35, 280)
                      && candidate.rect.height >= Math.min(window.innerHeight * 0.35, 200)
                      && !candidate.text.startsWith('Workspace switcher'),
                    )
                    .sort((left, right) => candidateScore(right) - candidateScore(left));
                  const bestCandidate = elementCandidates[0] || null;
                  const useWindow =
                    windowMaxScrollY > 0
                    || bestCandidate === null
                    || (
                      windowMaxScrollY >= Math.max(
                        80,
                        bestCandidate.scrollHeight - bestCandidate.clientHeight,
                      )
                    );
                  const scrollY = useWindow
                    ? (
                        window.scrollY
                        || window.pageYOffset
                        || scrollingElement?.scrollTop
                        || 0
                      )
                    : bestCandidate.scrollTop;
                  return Math.abs(scrollY - expectedScrollY) <= 1;
                }
                """,
                arg={"expectedScrollY": expected_scroll_y},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Scrolling the background page to the requested position did not settle.\n"
                f"Requested scroll Y: {expected_scroll_y:.1f}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        return self.observe_background_scroll()

    def navigate_to_section(self, label: str) -> None:
        if self._session.count(self._button_selector, has_text=label) == 0:
            raise AssertionError(
                f'The hosted tracker did not expose a visible "{label}" navigation entry.\n'
                f"Observed body text:\n{self.current_body_text()}",
            )
        try:
            self._session.click(
                self._button_selector,
                has_text=label,
                timeout_ms=30_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The hosted tracker did not expose a clickable "{label}" navigation entry.\n'
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
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

    def open_settings(self) -> str:
        return self._project_settings_page.open_settings()

    def clear_focus(self) -> None:
        self._session.evaluate(
            """
            () => {
              const active = document.activeElement;
              if (active instanceof HTMLElement) {
                active.blur();
              }
              return true;
            }
            """,
        )

    def focus_search_field(self, *, timeout_ms: int = 30_000) -> None:
        self._session.focus(self._search_input_selector, timeout_ms=timeout_ms)

    def focus_first_top_bar_control(self, *, timeout_ms: int = 30_000) -> None:
        self.clear_focus()
        try:
            self._session.focus(
                self._top_bar_button_selector,
                has_text=self._first_top_bar_control_label,
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "The hosted desktop shell did not expose the expected first top-bar "
                f'control "{self._first_top_bar_control_label}" for the keyboard '
                "navigation start point.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

        active = self._session.active_element()
        if active.accessible_name != self._first_top_bar_control_label:
            raise AssertionError(
                "Keyboard navigation did not start from the expected first top-bar "
                f'control "{self._first_top_bar_control_label}".\n'
                f"Observed active element: label={active.accessible_name!r}, "
                f"role={active.role!r}, tag={active.tag_name!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
    def focus_workspace_trigger(
        self,
        *,
        panel: WorkspaceSwitcherPanelObservation | None = None,
        timeout_ms: int = 30_000,
    ) -> None:
        try:
            self._session.focus(
                self._workspace_trigger_selector,
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            try:
                self._session.focus(
                    'button[aria-label^="Workspace switcher:"], [role="button"][aria-label^="Workspace switcher:"]',
                    timeout_ms=timeout_ms,
                )
            except WebAppTimeoutError:
                raise AssertionError(
                    "The visible workspace switcher trigger could not be focused before the "
                    "keyboard blur scenario.\n"
                    f"Observed body text:\n{self.current_body_text()}",
                ) from error
        active = self._session.active_element()
        if self._is_workspace_trigger_label(active.accessible_name):
            return

        focus_probe: object = None
        if panel is not None:
            focus_probe = self._probe_blur_focus_state(panel)
            if isinstance(focus_probe, dict) and bool(
                focus_probe.get("focusOwnedBySwitcher"),
            ):
                return

        raise AssertionError(
            "The visible workspace switcher trigger could not be focused into a "
            "switcher-owned state before the keyboard blur scenario.\n"
            f"Observed active element: label={active.accessible_name!r}, "
            f"role={active.role!r}, tag={active.tag_name!r}\n"
            f"Observed focus ownership probe: {focus_probe!r}\n"
            "The test intentionally does not keyboard-walk to the trigger here because "
            "TS-821 only requires focus to be owned by the switcher component before "
            "pressing Tab.\n"
            "Observed body text:\n"
            f"{self.current_body_text()}",
        )

    def collect_tab_sequence_from_search(
        self,
        *,
        tab_count: int,
        timeout_ms: int = 30_000,
    ) -> tuple[FocusNavigationStep, ...]:
        self.focus_search_field(timeout_ms=timeout_ms)
        return self._collect_tab_sequence(
            tab_count=tab_count,
            timeout_ms=timeout_ms,
            stop_when_workspace_trigger_reached=True,
        )

    def collect_tab_sequence(
        self,
        *,
        tab_count: int,
        timeout_ms: int = 30_000,
    ) -> tuple[FocusNavigationStep, ...]:
        return self._collect_tab_sequence(tab_count=tab_count, timeout_ms=timeout_ms)

    def collect_tab_sequence_from_first_top_bar_control(
        self,
        *,
        tab_count: int,
        timeout_ms: int = 30_000,
    ) -> tuple[FocusNavigationStep, ...]:
        self.focus_first_top_bar_control(timeout_ms=timeout_ms)
        return self._collect_tab_sequence(tab_count=tab_count, timeout_ms=timeout_ms)

    def active_element(self) -> FocusedElementObservation:
        return self._session.active_element()

    def observe_focus_ownership(
        self,
        *,
        panel: WorkspaceSwitcherPanelObservation,
    ) -> WorkspaceSwitcherFocusOwnershipObservation:
        active = self._session.active_element()
        payload = self._probe_blur_focus_state(panel)
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher focus probe did not return an observation.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceSwitcherFocusOwnershipObservation(
            active_label=active.accessible_name,
            active_role=active.role,
            active_tag_name=active.tag_name,
            active_outer_html=active.outer_html,
            active_visible=bool(payload.get("activeVisible")),
            active_in_viewport=bool(payload.get("activeInViewport")),
            switcher_focus_within=bool(payload.get("switcherFocusWithin")),
            active_within_switcher=bool(payload.get("activeWithinSwitcher")),
            active_on_trigger=bool(payload.get("activeOnTrigger")),
            focus_owned_by_switcher=bool(payload.get("focusOwnedBySwitcher")),
        )

    def observe_switcher_focus_target(
        self,
        *,
        panel: WorkspaceSwitcherPanelObservation,
    ) -> WorkspaceSwitcherFocusTargetObservation:
        active = self._session.active_element()
        payload = self._probe_blur_focus_state(panel)
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher focus probe did not return an observation.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceSwitcherFocusTargetObservation(
            active_label=active.accessible_name,
            active_role=active.role,
            active_tag_name=active.tag_name,
            active_outer_html=active.outer_html,
            active_visible=bool(payload.get("activeVisible")),
            active_in_viewport=bool(payload.get("activeInViewport")),
            active_within_switcher=bool(payload.get("activeWithinSwitcher")),
            active_on_trigger=bool(payload.get("activeOnTrigger")),
            focus_owned_by_switcher=bool(payload.get("focusOwnedBySwitcher")),
        )

    def observe_saved_workspace_row_focus(
        self,
        *,
        display_name: str,
        panel: WorkspaceSwitcherPanelObservation,
    ) -> WorkspaceSwitcherRowFocusObservation:
        active = self._session.active_element()
        focus_payload = self._probe_blur_focus_state(panel)
        if not isinstance(focus_payload, dict):
            raise AssertionError(
                "The workspace switcher focus probe did not return an observation.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        row_payload = self._session.evaluate(
            """
            ({ displayName, panelLeft, panelTop, panelRight, panelBottom }) => {
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
              const isInsidePanel = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const centerX = rect.left + (rect.width / 2);
                const centerY = rect.top + (rect.height / 2);
                return centerX >= panelLeft - 1
                  && centerX <= panelRight + 1
                  && centerY >= panelTop - 1
                  && centerY <= panelBottom + 1;
              };
              const matchesRow = (element) => {
                const text = normalize(element?.innerText || element?.textContent || '');
                return text.includes(displayName)
                  && text.includes('Branch:')
                  && (
                    text.includes('Delete:')
                    || text.includes('Open:')
                    || text.includes('Active')
                  );
              };

              const active = document.activeElement instanceof Element
                ? document.activeElement
                : null;
              let focusedRow = null;
              let current = active;
              while (current && current !== document.body) {
                if (isVisible(current) && isInsidePanel(current) && matchesRow(current)) {
                  focusedRow = current;
                  break;
                }
                current = current.parentElement;
              }

              const visibleRow = Array.from(document.querySelectorAll('*'))
                .filter((element) => isVisible(element) && isInsidePanel(element) && matchesRow(element))
                .sort((left, right) => {
                  const leftRect = left.getBoundingClientRect();
                  const rightRect = right.getBoundingClientRect();
                  return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                })[0] || null;
              const targetRow = focusedRow || visibleRow;
              return {
                rowFound: Boolean(targetRow),
                rowContainsActive: Boolean(focusedRow),
                rowText: normalize(targetRow?.innerText || targetRow?.textContent || ''),
              };
            }
            """,
            arg={
                "displayName": display_name,
                "panelLeft": panel.left,
                "panelTop": panel.top,
                "panelRight": panel.left + panel.width,
                "panelBottom": panel.top + panel.height,
            },
        )
        if not isinstance(row_payload, dict):
            raise AssertionError(
                "The workspace switcher row-focus probe did not return an observation.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceSwitcherRowFocusObservation(
            active_label=active.accessible_name,
            active_role=active.role,
            active_tag_name=active.tag_name,
            active_outer_html=active.outer_html,
            active_visible=bool(focus_payload.get("activeVisible")),
            active_in_viewport=bool(focus_payload.get("activeInViewport")),
            active_within_switcher=bool(focus_payload.get("activeWithinSwitcher")),
            active_on_trigger=bool(focus_payload.get("activeOnTrigger")),
            focus_owned_by_switcher=bool(focus_payload.get("focusOwnedBySwitcher")),
            row_found=bool(row_payload.get("rowFound")),
            row_contains_active=bool(row_payload.get("rowContainsActive")),
            row_text=str(row_payload.get("rowText", "")),
        )

    def observe_switcher_button_focusability(
        self,
        label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> WorkspaceSwitcherButtonFocusabilityObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({ heading, label }) => {
                  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                  const displayNameHint = normalize(label.split(',')[0] || '');
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
                  const visibleText = (element) =>
                    normalize(element?.innerText || element?.textContent || '');
                  const labelFor = (element) =>
                    normalize(
                      element?.getAttribute?.('aria-label')
                      || element?.getAttribute?.('placeholder')
                      || element?.getAttribute?.('title')
                      || element?.innerText
                      || element?.textContent
                      || '',
                    );
                  let switcher = Array.from(
                    document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
                  )
                    .filter(isVisible)
                    .find((element) => visibleText(element).includes(heading)) || null;
                  if (!switcher) {
                    const candidates = Array.from(document.querySelectorAll('*'))
                      .filter(isVisible)
                      .filter((element) => {
                        const text = visibleText(element);
                        return text.includes(heading)
                          && (
                            text.includes('Saved workspaces')
                            || text.includes('Save and switch')
                            || text.includes('Hosted Local')
                          );
                      })
                      .sort((left, right) => {
                        const leftRect = left.getBoundingClientRect();
                        const rightRect = right.getBoundingClientRect();
                        return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                      });
                    switcher = candidates[0] || null;
                  }
                  if (!switcher) {
                    return null;
                  }
                  const controlSelector = [
                    'flt-semantics[role="button"]',
                    'button',
                    '[role="button"]',
                    '[aria-disabled]',
                    '[disabled]',
                    '[tabindex]:not([tabindex="-1"])',
                  ].join(',');
                  const isSwitcherOwnedControl = (element) => {
                    if (!element) {
                      return false;
                    }
                    const panelId = element.getAttribute?.('data-trackstate-browser-focus-panel-id');
                    if (panelId === 'trackstate-workspace-switcher') {
                      return true;
                    }
                    return switcher.contains(element);
                  };
                  const candidateMatches = Array.from(document.querySelectorAll('*'))
                    .filter(isVisible)
                    .map((element) => {
                      const elementLabel = labelFor(element);
                      const elementText = visibleText(element);
                      const combined = normalize(`${elementLabel} ${elementText}`);
                      const isActionButton = elementLabel.startsWith('Delete:')
                        || elementLabel.startsWith('Open:')
                        || elementText === 'Active';
                      const matches = elementLabel === label
                        || elementText === label
                        || (
                          displayNameHint.length > 0
                          && !isActionButton
                          && (
                            elementLabel === displayNameHint
                            || elementText === displayNameHint
                            || combined.includes(displayNameHint)
                          )
                        );
                      if (!matches) {
                        return null;
                      }
                      const control = element.closest(controlSelector);
                      const target = control instanceof Element ? control : element;
                      if (!isSwitcherOwnedControl(target) && !isSwitcherOwnedControl(element)) {
                        return null;
                      }
                      if (!isVisible(target)) {
                        return null;
                      }
                      const targetLabel = labelFor(target);
                      const targetText = visibleText(target);
                      const targetCombined = normalize(`${targetLabel} ${targetText}`);
                      const rect = target.getBoundingClientRect();
                      return {
                        target,
                        exactMatch: targetLabel === label
                          || targetText === label
                          || elementLabel === label
                          || elementText === label,
                        interactiveMatch:
                          target.matches?.('button,[role="button"],[aria-disabled],[disabled]')
                          || target.getAttribute?.('tabindex') === '0'
                          || target.tabIndex >= 0,
                        area: rect.width * rect.height,
                        targetCombined,
                      };
                    })
                    .filter((candidate) => candidate !== null)
                    .sort((left, right) => {
                      if (left.exactMatch !== right.exactMatch) {
                        return left.exactMatch ? -1 : 1;
                      }
                      if (left.interactiveMatch !== right.interactiveMatch) {
                        return left.interactiveMatch ? -1 : 1;
                      }
                      return left.area - right.area;
                    });
                  const candidate = candidateMatches[0]?.target || null;
                  if (!candidate) {
                    return null;
                  }
                  const active = document.activeElement instanceof Element
                    ? document.activeElement
                    : null;
                  const tabindex = candidate.getAttribute('tabindex');
                  return {
                    label: labelFor(candidate),
                    visibleText: visibleText(candidate),
                    role: candidate.getAttribute('role'),
                    tagName: candidate.tagName,
                    tabindex,
                    keyboardFocusable: candidate.tabIndex >= 0,
                    activeWithin: Boolean(active && (active === candidate || candidate.contains(active))),
                    outerHTML: candidate.outerHTML,
                  };
                }
                """,
                arg={"heading": self._switcher_heading, "label": label},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open workspace switcher did not expose a visible button labelled "{label}".\n'
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                f'The open workspace switcher did not expose a visible button labelled "{label}".\n'
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceSwitcherButtonFocusabilityObservation(
            label=str(payload.get("label", label)),
            visible_text=str(payload.get("visibleText", "")),
            role=str(payload.get("role")) if payload.get("role") is not None else None,
            tag_name=str(payload.get("tagName", "")),
            tabindex=(
                str(payload.get("tabindex"))
                if payload.get("tabindex") is not None
                else None
            ),
            keyboard_focusable=bool(payload.get("keyboardFocusable")),
            active_within=bool(payload.get("activeWithin")),
            outer_html=str(payload.get("outerHTML", "")),
        )

    def observe_switcher_button_state(
        self,
        label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> WorkspaceSwitcherButtonStateObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({ heading, label }) => {
                  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                  const displayNameHint = normalize(label.split(',')[0] || '');
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
                  const visibleText = (element) =>
                    normalize(element?.innerText || element?.textContent || '');
                  const labelFor = (element) =>
                    normalize(
                      element?.getAttribute?.('aria-label')
                      || element?.getAttribute?.('placeholder')
                      || element?.getAttribute?.('title')
                      || element?.innerText
                      || element?.textContent
                      || '',
                    );
                  let switcher = Array.from(
                    document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
                  )
                    .filter(isVisible)
                    .find((element) => visibleText(element).includes(heading)) || null;
                  if (!switcher) {
                    const candidates = Array.from(document.querySelectorAll('*'))
                      .filter(isVisible)
                      .filter((element) => {
                        const text = visibleText(element);
                        return text.includes(heading)
                          && (
                            text.includes('Saved workspaces')
                            || text.includes('Save and switch')
                            || text.includes('Hosted Local')
                          );
                      })
                      .sort((left, right) => {
                        const leftRect = left.getBoundingClientRect();
                        const rightRect = right.getBoundingClientRect();
                        return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                      });
                    switcher = candidates[0] || null;
                  }
                  const controlSelector = [
                    'flt-semantics[role="button"]',
                    'button',
                    '[role="button"]',
                    '[aria-disabled]',
                    '[disabled]',
                    '[tabindex]:not([tabindex="-1"])',
                  ].join(',');
                  const isSwitcherOwnedControl = (element) => {
                    if (!element) {
                      return false;
                    }
                    const panelId = element.getAttribute?.('data-trackstate-browser-focus-panel-id');
                    if (panelId === 'trackstate-workspace-switcher') {
                      return true;
                    }
                    return Boolean(switcher && switcher.contains(element));
                  };
                  const candidateMatches = Array.from(document.querySelectorAll('*'))
                    .filter(isVisible)
                    .map((element) => {
                      const elementLabel = labelFor(element);
                      const elementText = visibleText(element);
                      const combined = normalize(`${elementLabel} ${elementText}`);
                      const isActionButton = elementLabel.startsWith('Delete:')
                        || elementLabel.startsWith('Open:')
                        || elementText === 'Active';
                      const matches = elementLabel === label
                        || elementText === label
                        || (
                          displayNameHint.length > 0
                          && !isActionButton
                          && (
                            elementLabel === displayNameHint
                            || elementText === displayNameHint
                            || combined.includes(displayNameHint)
                          )
                        );
                      if (!matches) {
                        return null;
                      }
                      const control = element.closest(controlSelector);
                      const target = control instanceof Element ? control : element;
                      if (!isSwitcherOwnedControl(target) && !isSwitcherOwnedControl(element)) {
                        return null;
                      }
                      if (!isVisible(target)) {
                        return null;
                      }
                      const targetLabel = labelFor(target);
                      const targetText = visibleText(target);
                      const rect = target.getBoundingClientRect();
                      return {
                        target,
                        exactMatch: targetLabel === label
                          || targetText === label
                          || elementLabel === label
                          || elementText === label,
                        interactiveMatch:
                          target.matches?.('button,[role="button"],[aria-disabled],[disabled]')
                          || target.getAttribute?.('tabindex') === '0'
                          || target.tabIndex >= 0,
                        area: rect.width * rect.height,
                      };
                    })
                    .filter((candidate) => candidate !== null)
                    .sort((left, right) => {
                      if (left.exactMatch !== right.exactMatch) {
                        return left.exactMatch ? -1 : 1;
                      }
                      if (left.interactiveMatch !== right.interactiveMatch) {
                        return left.interactiveMatch ? -1 : 1;
                      }
                      return left.area - right.area;
                    });
                  const candidate = candidateMatches[0]?.target || null;
                  if (!candidate) {
                    return null;
                  }
                  const active = document.activeElement instanceof Element
                    ? document.activeElement
                    : null;
                  const tabindex = candidate.getAttribute('tabindex');
                  const tabIndexValue = Number.isFinite(candidate.tabIndex)
                    ? candidate.tabIndex
                    : -1;
                  const ariaDisabled = normalize(candidate.getAttribute('aria-disabled'));
                  const disabled =
                    typeof candidate.disabled === 'boolean'
                      ? candidate.disabled
                      : candidate.hasAttribute('disabled');
                  return {
                    label: labelFor(candidate),
                    visibleText: visibleText(candidate),
                    role: candidate.getAttribute('role'),
                    tagName: candidate.tagName,
                    tabindex,
                    tabIndexValue,
                    ariaDisabled: ariaDisabled.length > 0 ? ariaDisabled : null,
                    disabled,
                    keyboardFocusable: tabIndexValue >= 0,
                    activeWithin: Boolean(active && (active === candidate || candidate.contains(active))),
                    outerHTML: candidate.outerHTML,
                  };
                }
                """,
                arg={"heading": self._switcher_heading, "label": label},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open workspace switcher did not expose a visible button labelled "{label}".\n'
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                f'The open workspace switcher did not expose a visible button labelled "{label}".\n'
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceSwitcherButtonStateObservation(
            label=str(payload.get("label", label)),
            visible_text=str(payload.get("visibleText", "")),
            role=str(payload.get("role")) if payload.get("role") is not None else None,
            tag_name=str(payload.get("tagName", "")),
            tabindex=(
                str(payload.get("tabindex"))
                if payload.get("tabindex") is not None
                else None
            ),
            tab_index_value=int(payload.get("tabIndexValue", -1)),
            aria_disabled=(
                str(payload.get("ariaDisabled"))
                if payload.get("ariaDisabled") is not None
                else None
            ),
            disabled=bool(payload.get("disabled")),
            keyboard_focusable=bool(payload.get("keyboardFocusable")),
            active_within=bool(payload.get("activeWithin")),
            outer_html=str(payload.get("outerHTML", "")),
        )

    def focus_switcher_button(
        self,
        label: str,
        *,
        panel: WorkspaceSwitcherPanelObservation,
        timeout_ms: int = 30_000,
    ) -> WorkspaceSwitcherFocusTargetObservation:
        try:
            self._session.wait_for_function(
                """
                ({ heading, label }) => {
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
                  const visibleText = (element) =>
                    normalize(element?.innerText || element?.textContent || '');
                  const labelFor = (element) =>
                    normalize(
                      element?.getAttribute?.('aria-label')
                      || element?.getAttribute?.('placeholder')
                      || element?.getAttribute?.('title')
                      || element?.innerText
                      || element?.textContent
                      || '',
                    );
                  let switcher = Array.from(
                    document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
                  )
                    .filter(isVisible)
                    .find((element) => visibleText(element).includes(heading)) || null;
                  if (!switcher) {
                    const candidates = Array.from(document.querySelectorAll('*'))
                      .filter(isVisible)
                      .filter((element) => {
                        const text = visibleText(element);
                        return text.includes(heading)
                          && (
                            text.includes('Saved workspaces')
                            || text.includes('Save and switch')
                            || text.includes('Hosted Local')
                          );
                      })
                      .sort((left, right) => {
                        const leftRect = left.getBoundingClientRect();
                        const rightRect = right.getBoundingClientRect();
                        return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                      });
                    switcher = candidates[0] || null;
                  }
                  if (!switcher) {
                    return null;
                  }
                  const controlSelector = [
                    'flt-semantics[role="button"]',
                    'button',
                    '[role="button"]',
                    '[aria-disabled]',
                    '[disabled]',
                    '[tabindex]:not([tabindex="-1"])',
                  ].join(',');
                  const candidateMatches = Array.from(switcher.querySelectorAll('*'))
                    .filter(isVisible)
                    .map((element) => {
                      const elementLabel = labelFor(element);
                      const elementText = visibleText(element);
                      const combined = normalize(`${elementLabel} ${elementText}`);
                      const matches = elementLabel === label
                        || elementText === label
                        || combined.includes(label);
                      if (!matches) {
                        return null;
                      }
                      const control = element.closest(controlSelector);
                      const target = control && switcher.contains(control) ? control : element;
                      if (!isVisible(target)) {
                        return null;
                      }
                      const targetLabel = labelFor(target);
                      const targetText = visibleText(target);
                      const rect = target.getBoundingClientRect();
                      return {
                        target,
                        exactMatch: targetLabel === label || targetText === label,
                        interactiveMatch:
                          target.matches?.('button,[role="button"],[aria-disabled],[disabled]')
                          || target.getAttribute?.('tabindex') === '0'
                          || target.tabIndex >= 0,
                        area: rect.width * rect.height,
                      };
                    })
                    .filter((candidate) => candidate !== null)
                    .sort((left, right) => {
                      if (left.exactMatch !== right.exactMatch) {
                        return left.exactMatch ? -1 : 1;
                      }
                      if (left.interactiveMatch !== right.interactiveMatch) {
                        return left.interactiveMatch ? -1 : 1;
                      }
                      return left.area - right.area;
                    });
                  const candidate = candidateMatches[0]?.target || null;
                  if (!candidate) {
                    return null;
                  }
                  candidate.focus({ preventScroll: true });
                  const active = document.activeElement;
                  return active === candidate || candidate.contains(active)
                    ? {
                        activeLabel: labelFor(active),
                        activeTagName: active?.tagName || '',
                      }
                    : null;
                }
                """,
                arg={
                    "heading": self._switcher_heading,
                    "label": label,
                },
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open workspace switcher did not expose a focusable "{label}" button.\n'
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        observation = self.observe_switcher_focus_target(panel=panel)
        if (
            not observation.focus_owned_by_switcher
            or not observation.active_within_switcher
        ):
            raise AssertionError(
                f'Focusing the visible "{label}" button did not keep keyboard focus inside '
                "the open workspace switcher.\n"
                f"Observed focus label: {observation.active_label!r}\n"
                f"Observed focus role: {observation.active_role!r}\n"
                f"Observed focus tag: {observation.active_tag_name!r}\n"
                f"Observed focus within switcher: {observation.active_within_switcher!r}\n"
                f"Observed focus owned by switcher: {observation.focus_owned_by_switcher!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return observation

    def observe_internal_tab_stops(
        self,
        *,
        panel: WorkspaceSwitcherPanelObservation,
        timeout_ms: int = 30_000,
    ) -> tuple[WorkspaceSwitcherTabStopObservation, ...]:
        payload = self._session.wait_for_function(
            """
            ({ heading, panelLeft, panelTop, panelRight, panelBottom }) => {
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
              const visibleText = (element) =>
                normalize(element?.innerText || element?.textContent || '');
              const labelFor = (element) =>
                normalize(
                  element?.getAttribute?.('aria-label')
                  || element?.getAttribute?.('placeholder')
                  || element?.getAttribute?.('title')
                  || element?.innerText
                  || element?.textContent
                  || '',
                );
              const isInsidePanel = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const centerX = rect.left + (rect.width / 2);
                const centerY = rect.top + (rect.height / 2);
                return centerX >= panelLeft
                  && centerX <= panelRight
                  && centerY >= panelTop
                  && centerY <= panelBottom;
              };
              let switcher = Array.from(
                document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
              )
                .filter(isVisible)
                .find((element) => visibleText(element).includes(heading)) || null;
              if (!switcher) {
                const candidates = Array.from(document.querySelectorAll('*'))
                  .filter(isVisible)
                  .filter((element) => {
                    const text = visibleText(element);
                    return text.includes(heading)
                      && (
                        text.includes('Saved workspaces')
                        || text.includes('Save and switch')
                        || text.includes('Hosted Local')
                      );
                  })
                  .sort((left, right) => {
                    const leftRect = left.getBoundingClientRect();
                    const rightRect = right.getBoundingClientRect();
                    return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                  });
                switcher = candidates[0] || null;
              }
              if (!switcher) {
                return null;
              }
              const interactiveSelector = [
                'flt-semantics[role="button"]',
                'button',
                '[role="button"]',
                'a[href]',
                'input',
                'textarea',
                'select',
                '[tabindex]',
              ].join(',');
              const isSwitcherOwnedControl = (element) => {
                if (!element) {
                  return false;
                }
                const panelId = element.getAttribute?.('data-trackstate-browser-focus-panel-id');
                if (panelId === 'trackstate-workspace-switcher') {
                  return true;
                }
                return switcher.contains(element);
              };
              const panelScopedControls = Array.from(document.querySelectorAll(interactiveSelector))
                .filter((element) => isSwitcherOwnedControl(element));
              const orderedElements = panelScopedControls
                .filter((element, index, all) => all.indexOf(element) === index);
              const candidates = orderedElements
                .map((element, domIndex) => {
                  const label = labelFor(element);
                  const text = visibleText(element);
                  const tabIndexValue = Number.isFinite(element.tabIndex)
                    ? element.tabIndex
                    : -1;
                  const role = element.getAttribute('role');
                  const tagName = element.tagName;
                  const style = window.getComputedStyle(element);
                  const pointerEvents = style.pointerEvents;
                  const hasMeaningfulLabel = label.length > 0 || text.length > 0;
                  const hasFocusableDescendant = Array.from(element.querySelectorAll(interactiveSelector))
                    .some((descendant) => descendant !== element && isVisible(descendant));
                  const anonymousWrapper = (
                    tagName === 'FLT-SEMANTICS'
                    && !role
                    && !hasMeaningfulLabel
                    && (pointerEvents === 'none' || hasFocusableDescendant)
                  );
                  const ariaDisabled = normalize(element.getAttribute('aria-disabled')).toLowerCase();
                  const disabled =
                    typeof element.disabled === 'boolean'
                      ? element.disabled
                      : element.hasAttribute('disabled');
                  const keyboardReachable =
                    tabIndexValue >= 0
                    && !disabled
                    && ariaDisabled != 'true';
                  return {
                    domIndex,
                    element,
                    label,
                    text,
                    tabIndexValue,
                    tabindex: element.getAttribute('tabindex'),
                    role,
                    tagName,
                    pointerEvents,
                    keyboardFocusable: keyboardReachable,
                    disabled,
                    headingMatch: text.includes(heading) || label.startsWith('Workspace switcher:'),
                    hasMeaningfulLabel,
                    anonymousWrapper,
                  };
                })
                .filter((candidate) =>
                  candidate.keyboardFocusable
                  && isVisible(candidate.element)
                  && isSwitcherOwnedControl(candidate.element)
                  && isInsidePanel(candidate.element)
                  && !candidate.headingMatch
                  && candidate.hasMeaningfulLabel
                  && !candidate.anonymousWrapper
                  && candidate.pointerEvents !== 'none'
                )
                .sort((left, right) => {
                  const leftPositive = left.tabIndexValue > 0;
                  const rightPositive = right.tabIndexValue > 0;
                  if (leftPositive !== rightPositive) {
                    return leftPositive ? -1 : 1;
                  }
                  if (leftPositive && rightPositive && left.tabIndexValue !== right.tabIndexValue) {
                    return left.tabIndexValue - right.tabIndexValue;
                  }
                  return left.domIndex - right.domIndex;
                })
                .map((candidate) => ({
                  label: candidate.label,
                  visibleText: candidate.text,
                  role: candidate.role,
                  tagName: candidate.tagName,
                  tabindex: candidate.tabindex,
                  tabIndexValue: candidate.tabIndexValue,
                  domIndex: candidate.domIndex,
                  keyboardFocusable: candidate.keyboardFocusable,
                  disabled: candidate.disabled,
                  outerHTML: candidate.element.outerHTML?.slice?.(0, 400) || '',
                }));
              return candidates.length > 0 ? candidates : null;
            }
            """,
            arg={
                "heading": self._switcher_heading,
                "panelLeft": panel.left,
                "panelTop": panel.top,
                "panelRight": panel.left + panel.width,
                "panelBottom": panel.top + panel.height,
            },
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, list):
            raise AssertionError(
                "The open workspace switcher did not expose any internal keyboard tab stops.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return tuple(
            WorkspaceSwitcherTabStopObservation(
                label=str(item.get("label", "")),
                visible_text=str(item.get("visibleText", "")),
                role=str(item.get("role")) if item.get("role") is not None else None,
                tag_name=str(item.get("tagName", "")),
                tabindex=(
                    str(item.get("tabindex"))
                    if item.get("tabindex") is not None
                    else None
                ),
                tab_index_value=int(item.get("tabIndexValue", -1)),
                dom_index=int(item.get("domIndex", -1)),
                keyboard_focusable=bool(item.get("keyboardFocusable")),
                disabled=bool(item.get("disabled")),
                outer_html=str(item.get("outerHTML", "")),
            )
            for item in payload
            if isinstance(item, dict)
        )
    def focus_internal_tab_stop(
        self,
        label: str,
        *,
        panel: WorkspaceSwitcherPanelObservation,
        timeout_ms: int = 30_000,
    ) -> WorkspaceSwitcherFocusTargetObservation:
        observable_labels = {
            observation.label or observation.visible_text
            for observation in self.observe_internal_tab_stops(
                panel=panel,
                timeout_ms=timeout_ms,
            )
            if observation.label or observation.visible_text
        }
        if label not in observable_labels:
            raise AssertionError(
                f'The open workspace switcher did not expose a keyboard-reachable internal '
                f'tab stop matching "{label}".\n'
                f"Observed internal tab stops: {sorted(observable_labels)!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        try:
            target_payload = self._session.evaluate(
                """
                ({ heading, label, panelLeft, panelTop, panelRight, panelBottom }) => {
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
                  const visibleText = (element) =>
                    normalize(element?.innerText || element?.textContent || '');
                  const labelFor = (element) =>
                    normalize(
                      element?.getAttribute?.('aria-label')
                      || element?.getAttribute?.('placeholder')
                      || element?.getAttribute?.('title')
                      || element?.innerText
                      || element?.textContent
                      || '',
                    );
                  const isInsidePanel = (element) => {
                    if (!element) {
                      return false;
                    }
                    const rect = element.getBoundingClientRect();
                    const centerX = rect.left + (rect.width / 2);
                    const centerY = rect.top + (rect.height / 2);
                    return centerX >= panelLeft
                      && centerX <= panelRight
                      && centerY >= panelTop
                      && centerY <= panelBottom;
                  };
                  let switcher = Array.from(
                    document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
                  )
                    .filter(isVisible)
                    .find((element) => visibleText(element).includes(heading)) || null;
                  if (!switcher) {
                    const candidates = Array.from(document.querySelectorAll('*'))
                      .filter(isVisible)
                      .filter((element) => {
                        const text = visibleText(element);
                        return text.includes(heading)
                          && (
                            text.includes('Saved workspaces')
                            || text.includes('Save and switch')
                            || text.includes('Hosted Local')
                          );
                      })
                      .sort((left, right) => {
                        const leftRect = left.getBoundingClientRect();
                        const rightRect = right.getBoundingClientRect();
                        return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                      });
                    switcher = candidates[0] || null;
                  }
                  if (!switcher) {
                    return null;
                  }
                  const interactiveSelector = [
                    'flt-semantics[role="button"]',
                    'button',
                    '[role="button"]',
                    'a[href]',
                    'input',
                    'textarea',
                    'select',
                    '[tabindex]',
                  ].join(',');
                  const isSwitcherOwnedControl = (element) => {
                    if (!element) {
                      return false;
                    }
                    const panelId = element.getAttribute?.('data-trackstate-browser-focus-panel-id');
                    if (panelId === 'trackstate-workspace-switcher') {
                      return true;
                    }
                    return switcher.contains(element);
                  };
                  const orderedElements = Array.from(document.querySelectorAll(interactiveSelector))
                    .filter((element) => isSwitcherOwnedControl(element))
                    .filter((element, index, all) => all.indexOf(element) === index);
                  const target = orderedElements.find((element) => {
                    if (
                      !isVisible(element)
                      || !isSwitcherOwnedControl(element)
                      || !isInsidePanel(element)
                    ) {
                      return false;
                    }
                    const tabIndexValue = Number.isFinite(element.tabIndex)
                      ? element.tabIndex
                      : -1;
                    const ariaDisabled = normalize(element.getAttribute('aria-disabled')).toLowerCase();
                    const disabled =
                    typeof element.disabled === 'boolean'
                      ? element.disabled
                      : element.hasAttribute('disabled');
                    if (tabIndexValue < 0) {
                    return false;
                    }
                    if (disabled || ariaDisabled === 'true') {
                    return false;
                    }
                    const elementLabel = labelFor(element);
                    const elementText = visibleText(element);
                    const role = element.getAttribute('role');
                    const tagName = element.tagName;
                    const style = window.getComputedStyle(element);
                    const pointerEvents = style.pointerEvents;
                    const hasMeaningfulLabel = elementLabel.length > 0 || elementText.length > 0;
                    const hasFocusableDescendant = Array.from(element.querySelectorAll(interactiveSelector))
                      .some((descendant) => descendant !== element && isVisible(descendant));
                    const anonymousWrapper = (
                      tagName === 'FLT-SEMANTICS'
                      && !role
                      && !hasMeaningfulLabel
                      && (pointerEvents === 'none' || hasFocusableDescendant)
                    );
                    if (
                      !hasMeaningfulLabel
                      || anonymousWrapper
                      || pointerEvents === 'none'
                    ) {
                      return false;
                    }
                    return elementLabel === label || elementText === label;
                  });
                  if (!target) {
                    return null;
                  }
                  target.focus({ preventScroll: true });
                  const active = document.activeElement;
                  const focused = active === target || target.contains(active);
                  const activeRect = active?.getBoundingClientRect?.();
                  const activeVisible = !!activeRect
                    && activeRect.width > 0
                    && activeRect.height > 0
                    && window.getComputedStyle(active).visibility !== 'hidden'
                    && window.getComputedStyle(active).display !== 'none';
                  const activeInViewport = !!activeRect
                    && activeRect.bottom > 0
                    && activeRect.right > 0
                    && activeRect.top < window.innerHeight
                    && activeRect.left < window.innerWidth;
                  const activeLabel = labelFor(active);
                  const activePanelId = active?.getAttribute?.('data-trackstate-browser-focus-panel-id');
                  const activeWithinSwitcher = (
                    !!active
                    && (
                      activePanelId === 'trackstate-workspace-switcher'
                      || switcher.contains(active)
                    )
                  );
                  const activeOnTrigger = activeLabel.startsWith('Workspace switcher:');
                  return {
                    focused,
                    activeLabel,
                    activeRole: active?.getAttribute?.('role') || null,
                    activeTagName: active?.tagName || '',
                    activeOuterHtml: active?.outerHTML?.slice?.(0, 400) || '',
                    activeVisible,
                    activeInViewport,
                    activeWithinSwitcher,
                    activeOnTrigger,
                    focusOwnedBySwitcher: activeWithinSwitcher || activeOnTrigger,
                  };
                }
                """,
                arg={
                   "heading": self._switcher_heading,
                   "label": label,
                    "panelLeft": panel.left,
                    "panelTop": panel.top,
                    "panelRight": panel.left + panel.width,
                    "panelBottom": panel.top + panel.height,
                },
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open workspace switcher did not expose a focusable internal tab stop '
                f'matching "{label}".\n'
                f"Observed internal tab stops: {sorted(observable_labels)!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(target_payload, dict) or not bool(target_payload.get("focused")):
            raise AssertionError(
                f'The open workspace switcher did not expose a focusable internal tab stop '
                f'matching "{label}".\n'
                f"Observed internal tab stops: {sorted(observable_labels)!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        observation = WorkspaceSwitcherFocusTargetObservation(
            active_label=(
                str(target_payload.get("activeLabel"))
                if target_payload.get("activeLabel") is not None
                else None
            ),
            active_role=(
                str(target_payload.get("activeRole"))
                if target_payload.get("activeRole") is not None
                else None
            ),
            active_tag_name=str(target_payload.get("activeTagName", "")),
            active_outer_html=str(target_payload.get("activeOuterHtml", "")),
            active_visible=bool(target_payload.get("activeVisible")),
            active_in_viewport=bool(target_payload.get("activeInViewport")),
            active_within_switcher=bool(target_payload.get("activeWithinSwitcher")),
            active_on_trigger=bool(target_payload.get("activeOnTrigger")),
            focus_owned_by_switcher=bool(target_payload.get("focusOwnedBySwitcher")),
        )
        if (
            not observation.focus_owned_by_switcher
            or not observation.active_within_switcher
        ):
            raise AssertionError(
                f'Focusing the visible internal tab stop "{label}" did not keep keyboard '
                "focus inside the open workspace switcher.\n"
                f"Observed focus label: {observation.active_label!r}\n"
                f"Observed focus role: {observation.active_role!r}\n"
                f"Observed focus tag: {observation.active_tag_name!r}\n"
                f"Observed focus within switcher: {observation.active_within_switcher!r}\n"
                f"Observed focus owned by switcher: {observation.focus_owned_by_switcher!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return observation

    def focus_saved_workspace_row(
        self,
        display_name: str,
        *,
        panel: WorkspaceSwitcherPanelObservation,
        timeout_ms: int = 30_000,
    ) -> WorkspaceSwitcherFocusTargetObservation:
        try:
            self._session.wait_for_function(
                """
                ({ displayName, panelLeft, panelTop, panelRight, panelBottom }) => {
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
                  const visibleText = (element) =>
                    normalize(element?.innerText || element?.textContent || '');
                  const labelFor = (element) =>
                    normalize(
                      element?.getAttribute?.('aria-label')
                      || element?.getAttribute?.('placeholder')
                      || element?.getAttribute?.('title')
                      || element?.innerText
                      || element?.textContent
                      || '',
                    );
                  const interactiveSelector = [
                    '[data-trackstate-browser-focus-row-id]',
                    '[data-trackstate-browser-focus-id]',
                    'flt-semantics[role="button"]',
                    'button',
                    '[role="button"]',
                    'a[href]',
                    'input',
                    'textarea',
                    'select',
                    '[tabindex]',
                  ].join(',');
                  const orderedElements = Array.from(document.querySelectorAll(interactiveSelector))
                    .filter((element, index, all) => all.indexOf(element) === index)
                    .filter((element) => isVisible(element));
                  const rowCandidates = orderedElements.filter((element) => {
                    const tabIndexValue = Number.isFinite(element.tabIndex)
                      ? element.tabIndex
                      : -1;
                    const ariaDisabled = normalize(element.getAttribute('aria-disabled')).toLowerCase();
                    const disabled =
                      typeof element.disabled === 'boolean'
                        ? element.disabled
                        : element.hasAttribute('disabled');
                    if (tabIndexValue < 0 || disabled || ariaDisabled === 'true') {
                      return false;
                    }
                    const elementLabel = labelFor(element);
                    const elementText = visibleText(element);
                    const combined = normalize(`${elementLabel} ${elementText}`);
                    if (!combined.includes(displayName)) {
                      return false;
                    }
                    return !elementLabel.startsWith('Open:')
                      && !elementLabel.startsWith('Delete:')
                      && !elementLabel.startsWith('Workspace switcher:')
                      && !elementText.startsWith('Open:')
                      && !elementText.startsWith('Delete:')
                      && !elementText.startsWith('Workspace switcher:');
                  });
                  const target = rowCandidates.find((element) =>
                    element.hasAttribute('data-trackstate-browser-focus-row-id')
                    || element.getAttribute('flt-semantics-identifier')?.includes?.('workspace-switcher-row')
                  ) || rowCandidates.find((element) =>
                    normalize(element.getAttribute('aria-current')).toLowerCase() === 'true'
                    || normalize(element.getAttribute('aria-selected')).toLowerCase() === 'true'
                    || normalize(element.getAttribute('data-trackstate-browser-focus-selected')).toLowerCase() === 'true'
                  ) || rowCandidates[0] || null;
                  if (!target) {
                    return null;
                  }
                  target.focus({ preventScroll: true });
                  const active = document.activeElement;
                  return active === target || target.contains(active)
                    ? {
                        activeLabel: labelFor(active),
                        activeTagName: active?.tagName || '',
                      }
                    : null;
                }
                """,
                arg={
                    "displayName": display_name,
                },
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open workspace switcher did not expose a focusable saved workspace row '
                f'for "{display_name}".\n'
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        observation = self.observe_switcher_focus_target(panel=panel)
        if (
            not observation.focus_owned_by_switcher
            or not observation.active_within_switcher
        ):
            raise AssertionError(
                f'Focusing the visible saved workspace row "{display_name}" did not keep '
                "keyboard focus inside the open workspace switcher.\n"
                f"Observed focus label: {observation.active_label!r}\n"
                f"Observed focus role: {observation.active_role!r}\n"
                f"Observed focus tag: {observation.active_tag_name!r}\n"
                f"Observed focus within switcher: {observation.active_within_switcher!r}\n"
                f"Observed focus owned by switcher: {observation.focus_owned_by_switcher!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return observation

    def debug_saved_workspace_row_candidates(
        self,
        display_name: str,
    ) -> list[dict[str, object]]:
        payload = self._session.evaluate(
            """
            ({ displayName }) => {
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
                normalize(
                  element?.getAttribute?.('aria-label')
                  || element?.getAttribute?.('title')
                  || element?.innerText
                  || element?.textContent
                  || '',
                );
              return Array.from(
                document.querySelectorAll(
                  '[data-trackstate-browser-focus-row-id],[data-trackstate-browser-focus-id],flt-semantics[role="button"],button,[role="button"]',
                ),
              )
                .filter((element, index, all) => all.indexOf(element) === index)
                .filter((element) => isVisible(element))
                .map((element) => {
                  const label = labelFor(element);
                  const text = normalize(element?.innerText || element?.textContent || '');
                  return {
                    tag_name: element.tagName,
                    role: element.getAttribute('role'),
                    label,
                    text,
                    tabindex: element.getAttribute('tabindex'),
                    tab_index_value: Number.isFinite(element.tabIndex) ? element.tabIndex : null,
                    disabled:
                      typeof element.disabled === 'boolean'
                        ? element.disabled
                        : element.hasAttribute('disabled'),
                    aria_current: element.getAttribute('aria-current'),
                    aria_selected: element.getAttribute('aria-selected'),
                    focus_id: element.getAttribute('data-trackstate-browser-focus-id'),
                    row_id: element.getAttribute('data-trackstate-browser-focus-row-id'),
                    identifier: element.getAttribute('flt-semantics-identifier'),
                    outer_html: (element.outerHTML || '').slice(0, 400),
                  };
                })
                .filter((candidate) =>
                  JSON.stringify(candidate).includes(displayName),
                );
            }
            """,
            arg={"displayName": display_name},
        )
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]


    def click_switcher_button(
        self,
        label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> None:
        try:
            clicked = self._session.wait_for_function(
                """
                ({ heading, label }) => {
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
                  const visibleText = (element) =>
                    normalize(element?.innerText || element?.textContent || '');
                  const labelFor = (element) =>
                    normalize(
                      element?.getAttribute?.('aria-label')
                      || element?.getAttribute?.('placeholder')
                      || element?.getAttribute?.('title')
                      || element?.innerText
                      || element?.textContent
                      || '',
                    );
                  let switcher = Array.from(
                    document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
                  )
                    .filter(isVisible)
                    .find((element) => visibleText(element).includes(heading)) || null;
                  if (!switcher) {
                    const candidates = Array.from(document.querySelectorAll('*'))
                      .filter(isVisible)
                      .filter((element) => {
                        const text = visibleText(element);
                        return text.includes(heading)
                          && (
                            text.includes('Saved workspaces')
                            || text.includes('Save and switch')
                            || text.includes('Hosted Local')
                          );
                      })
                      .sort((left, right) => {
                        const leftRect = left.getBoundingClientRect();
                        const rightRect = right.getBoundingClientRect();
                        return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                      });
                    switcher = candidates[0] || null;
                  }
                  if (!switcher) {
                    return null;
                  }
                  const buttonSelector = [
                    'flt-semantics[role="button"]',
                    'button',
                    '[role="button"]',
                  ].join(',');
                  const candidate = Array.from(switcher.querySelectorAll(buttonSelector))
                    .filter(isVisible)
                    .find((element) => {
                      const elementLabel = labelFor(element);
                      const elementText = visibleText(element);
                      return elementLabel === label || elementText === label;
                    });
                  if (!candidate) {
                    return null;
                  }
                  candidate.click();
                  return {
                    label: labelFor(candidate),
                    visibleText: visibleText(candidate),
                  };
                }
                """,
                arg={"heading": self._switcher_heading, "label": label},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open workspace switcher did not expose a clickable button labelled "{label}".\n'
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(clicked, dict):
            raise AssertionError(
                f'The open workspace switcher did not expose a clickable button labelled "{label}".\n'
                f"Observed body text:\n{self.current_body_text()}",
            )

    def click_switcher_button_center(
        self,
        label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> WorkspaceSwitcherInternalClickObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({ heading, label }) => {
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
                  const visibleText = (element) =>
                    normalize(element?.innerText || element?.textContent || '');
                  const labelFor = (element) =>
                    normalize(
                      element?.getAttribute?.('aria-label')
                      || element?.getAttribute?.('placeholder')
                      || element?.getAttribute?.('title')
                      || element?.innerText
                      || element?.textContent
                      || '',
                    );
                  const controlSelector = [
                    'flt-semantics[role="button"]',
                    'button',
                    '[role="button"]',
                    '[aria-disabled]',
                    '[disabled]',
                    '[tabindex]:not([tabindex="-1"])',
                  ].join(',');
                  const candidateMatches = Array.from(document.querySelectorAll('*'))
                    .filter(isVisible)
                    .map((element) => {
                      const elementLabel = labelFor(element);
                      const elementText = visibleText(element);
                      const combined = normalize(`${elementLabel} ${elementText}`);
                      const matches = elementLabel === label
                        || elementText === label
                        || combined.includes(label);
                      if (!matches) {
                        return null;
                      }
                      const control = element.closest(controlSelector);
                      const target = control instanceof Element ? control : element;
                      if (!isVisible(target)) {
                        return null;
                      }
                      const targetLabel = labelFor(target);
                      const targetText = visibleText(target);
                      const rect = target.getBoundingClientRect();
                      return {
                        target,
                        exactMatch: targetLabel === label || targetText === label,
                        interactiveMatch:
                          target.matches?.('button,[role="button"],[aria-disabled],[disabled]')
                          || target.getAttribute?.('tabindex') === '0'
                          || target.tabIndex >= 0,
                        area: rect.width * rect.height,
                      };
                    })
                    .filter((candidate) => candidate !== null)
                    .sort((left, right) => {
                      if (left.exactMatch !== right.exactMatch) {
                        return left.exactMatch ? -1 : 1;
                      }
                      if (left.interactiveMatch !== right.interactiveMatch) {
                        return left.interactiveMatch ? -1 : 1;
                      }
                      return left.area - right.area;
                    });
                  const candidate = candidateMatches[0]?.target || null;
                  if (!candidate) {
                    return null;
                  }
                  const buttonRect = candidate.getBoundingClientRect();
                  const switcherAncestors = [];
                  let current = candidate;
                  while (current && current instanceof Element && current !== document.body) {
                    const text = visibleText(current);
                    if (
                      text.includes(heading)
                      || text.includes('Saved workspaces')
                      || text.includes('Add workspace')
                      || text.includes('Hosted Local')
                    ) {
                      const rect = current.getBoundingClientRect();
                      switcherAncestors.push({
                        element: current,
                        area: rect.width * rect.height,
                      });
                    }
                    current = current.parentElement;
                  }
                  const switcher = switcherAncestors
                    .sort((left, right) => left.area - right.area)[0]?.element || candidate;
                  const switcherRect = switcher.getBoundingClientRect();
                  return {
                    clickX: buttonRect.left + (buttonRect.width / 2),
                    clickY: buttonRect.top + (buttonRect.height / 2),
                    panelLeft: switcherRect.left,
                    panelTop: switcherRect.top,
                    panelWidth: switcherRect.width,
                    panelHeight: switcherRect.height,
                    targetTagName: candidate.tagName.toLowerCase(),
                    targetRole: candidate.getAttribute('role'),
                    targetLabel: labelFor(candidate),
                    targetText: visibleText(candidate),
                  };
                }
                """,
                arg={"heading": self._switcher_heading, "label": label},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open workspace switcher did not expose a visible button labelled "{label}" '
                "for a pointer click.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                f'The open workspace switcher did not expose a visible button labelled "{label}" '
                "for a pointer click.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        observation = WorkspaceSwitcherInternalClickObservation(
            click_x=float(payload.get("clickX", 0.0)),
            click_y=float(payload.get("clickY", 0.0)),
            panel_left=float(payload.get("panelLeft", 0.0)),
            panel_top=float(payload.get("panelTop", 0.0)),
            panel_width=float(payload.get("panelWidth", 0.0)),
            panel_height=float(payload.get("panelHeight", 0.0)),
            target_tag_name=str(payload.get("targetTagName", "")),
            target_role=(
                str(payload.get("targetRole"))
                if payload.get("targetRole") is not None
                else None
            ),
            target_label=str(payload.get("targetLabel", "")),
            target_text=str(payload.get("targetText", "")),
        )
        self._session.mouse_click(observation.click_x, observation.click_y)
        return observation

    def focus_switcher_text_field(
        self,
        label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> FocusedElementObservation:
        try:
            self._session.focus(
                self._switcher_text_field_selector(label),
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open workspace switcher did not expose a focusable "{label}" text '
                "field.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        return self._session.active_element()

    def read_switcher_text_field_value(
        self,
        label: str,
        *,
        timeout_ms: int = 30_000,
    ) -> str:
        try:
            return self._session.read_value(
                self._switcher_text_field_selector(label),
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open workspace switcher did not expose a readable "{label}" text '
                "field value.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def press_key(self, key: str, *, timeout_ms: int = 30_000) -> None:
        self._session.press_key(key, timeout_ms=timeout_ms)

    def wait_for_surface_to_remain_open(
        self,
        *,
        stability_ms: int = 1_000,
        timeout_ms: int = 4_000,
    ) -> None:
        self._session.evaluate(
            """
            () => {
              window.__tsWorkspaceSwitcherOpenStability = {
                visibleSinceMs: null,
              };
              return true;
            }
            """,
        )
        try:
            self._session.wait_for_function(
                """
                ({ heading, stabilityMs }) => {
                  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                  const isWorkspaceRowText = (text) =>
                    text.includes('Branch:')
                    && text.includes('Delete')
                    && (text.includes('Hosted') || text.includes('Local'))
                    && (text.includes('Open') || text.includes('Active'));
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
                  const visibleText = (element) => normalize(element.innerText || element.textContent || '');
                  const panelCandidates = Array.from(document.querySelectorAll('*'))
                    .filter(isVisible)
                    .map((element) => {
                      const rect = element.getBoundingClientRect();
                      const text = visibleText(element);
                      return {
                        element,
                        text,
                        area: rect.width * rect.height,
                        hasLegacyWorkspaceLabels:
                          text.includes('Saved workspaces') && text.includes('Add workspace'),
                        hasCurrentWorkspaceLabels:
                          text.includes('Save and switch')
                          && (text.includes('Hosted') || text.includes('Local'))
                          && (text.includes('Delete') || text.includes('Branch:')),
                        hasWorkspaceRowText: isWorkspaceRowText(text),
                      };
                    })
                    .filter((candidate) =>
                      candidate.text.includes(heading)
                      && (
                        candidate.hasLegacyWorkspaceLabels
                        || candidate.hasCurrentWorkspaceLabels
                        || candidate.hasWorkspaceRowText
                        || candidate.text.includes('Hosted Local')
                      ),
                    )
                    .sort((left, right) => left.area - right.area);
                  const surfaceVisible = panelCandidates.length > 0;
                  const stabilityState = window.__tsWorkspaceSwitcherOpenStability;
                  if (!surfaceVisible) {
                    stabilityState.visibleSinceMs = null;
                    return null;
                  }
                  if (typeof stabilityState.visibleSinceMs !== 'number') {
                    stabilityState.visibleSinceMs = window.performance.now();
                    return null;
                  }
                  const visibleForMs = window.performance.now() - stabilityState.visibleSinceMs;
                  return visibleForMs >= stabilityMs
                    ? {
                        visibleForMs,
                      }
                    : null;
                }
                """,
                arg={
                    "heading": self._switcher_heading,
                    "stabilityMs": stability_ms,
                },
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "The workspace switcher surface did not remain visibly open for the "
                f"required {stability_ms} ms stability window.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def observe_saved_workspace_rows(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...]:
        rows: list[WorkspaceSwitcherSavedWorkspaceRowObservation] = []
        switcher = self.observe_open_switcher(timeout_ms=timeout_ms)
        body_text = self.current_body_text()
        state_labels = (
            "Attachments limited",
            "Saved hosted workspace",
            "Sync issue",
            "Needs sign-in",
            "Read-only",
            "Connected",
            "Unavailable",
            "Local Git",
        )
        summary_line_pattern = re.compile(
            rf"^(?P<display>.+?), "
            rf"(?P<target_type>Hosted|Local), "
            rf"(?P<state>{'|'.join(re.escape(label) for label in state_labels)}), "
            rf"(?P<detail>.+Branch:.+)$",
        )
        panel_lines = [
            " ".join(line.split()).strip()
            for line in switcher.body_text.splitlines()
            if line.strip()
        ]
        deduped_lines = [
            re.sub(r"^(.+)\s+\1$", r"\1", line)
            for line in panel_lines
        ]
        heading_indexes = [
            index for index, line in enumerate(deduped_lines) if line == self._switcher_heading
        ]
        parsed_rows: list[
            tuple[str, str, str | None, str | None, tuple[str, ...], bool, str]
        ] = []
        if heading_indexes:
            candidate_lines = deduped_lines[heading_indexes[-1] + 1 :]
            index = 0
            while index < len(candidate_lines):
                if index + 2 < len(candidate_lines):
                    summary_line = candidate_lines[index]
                    action_label = candidate_lines[index + 1]
                    delete_label = candidate_lines[index + 2]
                    summary_match = summary_line_pattern.match(summary_line)
                    if (
                        summary_match is not None
                        and _is_saved_workspace_action_line(action_label)
                        and delete_label.startswith("Delete: ")
                    ):
                        parsed_rows.append(
                            (
                                summary_match.group("display").strip(),
                                summary_match.group("detail").strip(),
                                summary_match.group("target_type").strip(),
                                summary_match.group("state").strip(),
                                (action_label, delete_label),
                                action_label == "Active",
                                summary_line,
                            ),
                        )
                        index += 3
                        continue
                if index + 5 >= len(candidate_lines):
                    index += 1
                    continue
                display_name = candidate_lines[index]
                detail_text = candidate_lines[index + 1]
                target_type_label = candidate_lines[index + 2]
                state_label = candidate_lines[index + 3]
                action_label = candidate_lines[index + 4]
                delete_label = candidate_lines[index + 5]
                if (
                    "Branch:" in detail_text
                    and target_type_label in {"Hosted", "Local"}
                    and _is_saved_workspace_action_line(action_label)
                    and delete_label.startswith("Delete: ")
                ):
                    parsed_rows.append(
                        (
                            display_name,
                            detail_text,
                            target_type_label,
                            state_label,
                            (action_label, delete_label),
                            action_label == "Active",
                            display_name,
                        ),
                    )
                    index += 6
                    continue
                index += 1
            if not parsed_rows:
                index = 0
                while index + 2 < len(candidate_lines):
                    header = candidate_lines[index]
                    action_label = candidate_lines[index + 1]
                    delete_label = candidate_lines[index + 2]
                    if "Branch:" not in header or not delete_label.startswith("Delete: "):
                        index += 1
                        continue

                    display_name: str | None = None
                    target_type_label: str | None = None
                    state_label: str | None = None
                    detail_text = header
                    header_parts = [part.strip() for part in header.split(", ", 3)]
                    if len(header_parts) >= 4:
                        display_name = header_parts[0] or None
                        target_type_label = header_parts[1] or None
                        state_label = header_parts[2] or None
                        detail_text = header_parts[3]
                    elif len(header_parts) >= 2:
                        display_name = header_parts[0] or None
                        target_type_label = header_parts[1] or None
                        detail_text = ", ".join(header_parts[2:]) or header
                    if not display_name:
                        index += 1
                        continue

                    parsed_rows.append(
                        (
                            display_name,
                            detail_text,
                            target_type_label,
                            state_label,
                            (action_label, delete_label),
                            action_label == "Active",
                            header,
                        ),
                    )
                    index += 3
        if not parsed_rows:
            for row in switcher.rows:
                display_name = row.display_name
                detail_text = row.detail_text.strip()
                if not display_name or "Branch:" not in detail_text:
                    continue
                parsed_rows.append(
                    (
                        display_name,
                        detail_text,
                        row.target_type_label,
                        row.state_label,
                        row.action_labels,
                        row.selected,
                        display_name,
                    ),
                )
        if not parsed_rows:
            body_lines = [
                re.sub(r"^(.+)\s+\1$", r"\1", " ".join(line.split()).strip())
                for line in body_text.splitlines()
                if line.strip()
            ]
            body_heading_indexes = [
                index for index, line in enumerate(body_lines) if line == self._switcher_heading
            ]
            if body_heading_indexes:
                candidate_lines = body_lines[body_heading_indexes[-1] + 1 :]
                index = 0
                while index + 2 < len(candidate_lines):
                    summary_line = candidate_lines[index]
                    action_label = candidate_lines[index + 1]
                    delete_label = candidate_lines[index + 2]
                    if (
                        "Branch:" in summary_line
                        and _is_saved_workspace_action_line(action_label)
                        and delete_label.startswith("Delete: ")
                    ):
                        summary_parts = [
                            part.strip() for part in summary_line.split(",") if part.strip()
                        ]
                        if len(summary_parts) >= 4:
                            parsed_rows.append(
                                (
                                    summary_parts[0],
                                    ", ".join(summary_parts[3:]),
                                    summary_parts[1],
                                    summary_parts[2],
                                    (action_label, delete_label),
                                    action_label == "Active",
                                    summary_line,
                                ),
                            )
                            index += 3
                            continue
                    index += 1
        for (
            display_name,
            detail_text,
            target_type_label,
            state_label,
            action_labels,
            selected,
            locator_text,
        ) in parsed_rows:
            bounds = self._session.evaluate(
                """
                ({
                  displayName,
                  locatorText,
                  detailText,
                  actionLabels,
                  deleteLabel,
                  targetTypeLabel,
                }) => {
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
                  const textFor = (element) => normalize(element.innerText || element.textContent || '');
                  const areaFor = (element) => {
                    const rect = element.getBoundingClientRect();
                    return rect.width * rect.height;
                  };
                  const rectFor = (element) => element.getBoundingClientRect();
                  const normalizedActions = (actionLabels || [])
                    .map((label) => normalize(label))
                    .filter((label) => label.length > 0);
                  const unionRect = (elements) => {
                    if (!elements.length) {
                      return null;
                    }
                    const rects = elements.map((element) => rectFor(element));
                    const left = Math.min(...rects.map((rect) => rect.left));
                    const top = Math.min(...rects.map((rect) => rect.top));
                    const right = Math.max(...rects.map((rect) => rect.right));
                    const bottom = Math.max(...rects.map((rect) => rect.bottom));
                    return {
                      left,
                      top,
                      width: Math.max(0, right - left),
                      height: Math.max(0, bottom - top),
                    };
                  };
                  const countMatches = (text, fragment) =>
                    !fragment ? 0 : text.split(fragment).length - 1;
                  const matchesRow = (element) => {
                    const text = textFor(element);
                    return text.includes(displayName)
                      && (!locatorText || text.includes(locatorText))
                      && text.includes(detailText)
                      && (!targetTypeLabel || text.includes(targetTypeLabel))
                      && normalizedActions.every((label) => !label || text.includes(label))
                      && (!deleteLabel || text.includes(deleteLabel));
                  };
                  const anchors = Array.from(document.querySelectorAll('*'))
                    .filter((element) => isVisible(element))
                    .filter((element) => {
                      const text = textFor(element);
                      const ariaLabel = normalize(element.getAttribute('aria-label') || '');
                      return (
                        text === locatorText
                        || text === displayName
                        || text === deleteLabel
                        || ariaLabel === deleteLabel
                        || normalizedActions.includes(text)
                        || normalizedActions.includes(ariaLabel)
                      );
                    })
                    .sort((left, right) => areaFor(left) - areaFor(right));
                  const displayAnchor = anchors.find((element) => {
                    const text = textFor(element);
                    return text === locatorText || text === displayName;
                  }) || null;
                  const actionAnchor = anchors.find((element) => {
                    const text = textFor(element);
                    const ariaLabel = normalize(element.getAttribute('aria-label') || '');
                    return normalizedActions.includes(text) || normalizedActions.includes(ariaLabel);
                  }) || null;
                  const deleteAnchor = anchors.find((element) => {
                    const text = textFor(element);
                    const ariaLabel = normalize(element.getAttribute('aria-label') || '');
                    return text === deleteLabel || ariaLabel === deleteLabel;
                  }) || null;
                  const anchorBounds = unionRect(
                    [displayAnchor, actionAnchor, deleteAnchor].filter(Boolean),
                  );
                  if (anchorBounds && anchorBounds.width > 0 && anchorBounds.height > 0) {
                    return anchorBounds;
                  }
                  let candidate = null;
                  for (const anchor of anchors) {
                    let current = anchor;
                    while (current && current !== document.body) {
                      const text = textFor(current);
                      if (
                        isVisible(current)
                        && matchesRow(current)
                        && countMatches(text, 'Branch:') <= 1
                        && countMatches(text, 'Delete:') <= 1
                      ) {
                        candidate = current;
                        break;
                      }
                      current = current.parentElement;
                    }
                    if (candidate) {
                      break;
                    }
                  }
                  if (!candidate) {
                    candidate = Array.from(document.querySelectorAll('*'))
                      .filter((element) => isVisible(element) && matchesRow(element))
                      .sort((left, right) => areaFor(left) - areaFor(right))[0];
                  }
                  if (!candidate) {
                    return null;
                  }
                  const rect = rectFor(candidate);
                  return {
                    left: rect.left,
                    top: rect.top,
                    width: rect.width,
                    height: rect.height,
                  };
                }
                """,
                arg={
                    "displayName": display_name,
                    "locatorText": locator_text,
                    "detailText": detail_text,
                    "actionLabels": list(action_labels),
                    "deleteLabel": action_labels[-1] if action_labels else "",
                    "targetTypeLabel": target_type_label,
                },
            )
            if not isinstance(bounds, dict):
                raise AssertionError(
                    f'The open workspace switcher exposed saved workspace text for "{display_name}", '
                    "but its visible label could not be located for interaction.\n"
                    f"Observed switcher text:\n{switcher.switcher_text}\n"
                    f"Observed body text:\n{body_text}",
                )
            rows.append(
                WorkspaceSwitcherSavedWorkspaceRowObservation(
                    display_name=display_name,
                    target_type_label=target_type_label,
                    state_label=state_label,
                    detail_text=detail_text,
                    selected=selected,
                    action_labels=action_labels,
                    left=float(bounds.get("left", 0.0)),
                    top=float(bounds.get("top", 0.0)),
                    width=float(bounds.get("width", 0.0)),
                    height=float(bounds.get("height", 0.0)),
                ),
            )
        if not rows:
            for row in switcher.rows:
                display_name = (row.display_name or "").strip()
                detail_text = row.detail_text.strip()
                if not display_name or "Branch:" not in detail_text:
                    continue
                action_labels = tuple(
                    label
                    for label in (
                        *row.action_labels,
                        *row.button_labels,
                    )
                    if label
                )
                bounds = self._session.evaluate(
                    """
                    ({ displayName, detailText, actionLabels, deleteLabel }) => {
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
                      const textFor = (element) => normalize(element.innerText || element.textContent || '');
                      const areaFor = (element) => {
                        const rect = element.getBoundingClientRect();
                        return rect.width * rect.height;
                      };
                      const rectFor = (element) => element.getBoundingClientRect();
                      const unionRect = (elements) => {
                        if (!elements.length) {
                          return null;
                        }
                        const rects = elements.map((element) => rectFor(element));
                        const left = Math.min(...rects.map((rect) => rect.left));
                        const top = Math.min(...rects.map((rect) => rect.top));
                        const right = Math.max(...rects.map((rect) => rect.right));
                        const bottom = Math.max(...rects.map((rect) => rect.bottom));
                        return {
                          left,
                          top,
                          width: Math.max(0, right - left),
                          height: Math.max(0, bottom - top),
                        };
                      };
                      const countMatches = (text, fragment) =>
                        !fragment ? 0 : text.split(fragment).length - 1;
                      const matchesRow = (element) => {
                        const text = textFor(element);
                        return text.includes(displayName)
                          && text.includes(detailText)
                          && actionLabels.every((label) => !label || text.includes(label))
                          && (!deleteLabel || text.includes(deleteLabel));
                      };
                      const anchors = Array.from(document.querySelectorAll('*'))
                        .filter((element) => isVisible(element))
                        .filter((element) => {
                          const text = textFor(element);
                          const ariaLabel = normalize(element.getAttribute('aria-label') || '');
                          return text === deleteLabel || ariaLabel === deleteLabel;
                        })
                        .sort((left, right) => areaFor(left) - areaFor(right));
                      const displayAnchor = Array.from(document.querySelectorAll('*'))
                        .filter((element) => isVisible(element) && textFor(element) === displayName)
                        .sort((left, right) => areaFor(left) - areaFor(right))[0] || null;
                      const actionAnchor = anchors.find((element) => {
                        const text = textFor(element);
                        const ariaLabel = normalize(element.getAttribute('aria-label') || '');
                        return actionLabels.includes(text) || actionLabels.includes(ariaLabel);
                      }) || null;
                      const deleteAnchor = anchors.find((element) => {
                        const text = textFor(element);
                        const ariaLabel = normalize(element.getAttribute('aria-label') || '');
                        return text === deleteLabel || ariaLabel === deleteLabel;
                      }) || null;
                      const anchorBounds = unionRect(
                        [displayAnchor, actionAnchor, deleteAnchor].filter(Boolean),
                      );
                      if (anchorBounds && anchorBounds.width > 0 && anchorBounds.height > 0) {
                        return anchorBounds;
                      }
                      let candidate = null;
                      for (const anchor of anchors) {
                        let current = anchor;
                        while (current && current !== document.body) {
                          const text = textFor(current);
                          if (
                            isVisible(current)
                            && matchesRow(current)
                            && countMatches(text, 'Branch:') <= 1
                            && countMatches(text, 'Delete:') <= 1
                          ) {
                            candidate = current;
                            break;
                          }
                          current = current.parentElement;
                        }
                        if (candidate) {
                          break;
                        }
                      }
                      if (!candidate) {
                        candidate = Array.from(document.querySelectorAll('*'))
                          .filter((element) => isVisible(element) && matchesRow(element))
                          .sort((left, right) => areaFor(left) - areaFor(right))[0];
                      }
                      if (!candidate) {
                        return null;
                      }
                      const rect = rectFor(candidate);
                      return {
                        left: rect.left,
                        top: rect.top,
                        width: rect.width,
                        height: rect.height,
                      };
                    }
                    """,
                    arg={
                        "displayName": display_name,
                        "detailText": detail_text,
                        "actionLabels": list(action_labels),
                        "deleteLabel": action_labels[-1] if action_labels else "",
                    },
                )
                if not isinstance(bounds, dict):
                    continue
                rows.append(
                    WorkspaceSwitcherSavedWorkspaceRowObservation(
                        display_name=display_name,
                        target_type_label=row.target_type_label,
                        state_label=row.state_label,
                        detail_text=detail_text,
                        selected=row.selected,
                        action_labels=action_labels,
                        left=float(bounds.get("left", 0.0)),
                        top=float(bounds.get("top", 0.0)),
                        width=float(bounds.get("width", 0.0)),
                        height=float(bounds.get("height", 0.0)),
                    ),
                )
        if not rows:
            row_pattern = re.compile(
                r"(?P<display>[^\n]+)\n"
                r"(?P<detail>[^\n]*Branch:[^\n]+)\n"
                r"(?P<type>Hosted|Local)\n"
                r"(?P<state>[^\n]+)\n"
                r"(?P<action>Active|Open: [^\n]+)\n"
                r"(?P<delete>Delete: [^\n]+)",
                re.MULTILINE,
            )
            for match in row_pattern.finditer(body_text):
                display_name = match.group("display").strip()
                bounds = self._session.evaluate(
                    """
                    ({ text }) => {
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
                      const candidate = Array.from(document.querySelectorAll('*'))
                        .filter((element) => isVisible(element))
                        .find((element) => normalize(element.innerText || element.textContent || '') === text);
                      if (!candidate) {
                        return null;
                      }
                      const rect = candidate.getBoundingClientRect();
                      return {
                        left: rect.left,
                        top: rect.top,
                        width: rect.width,
                        height: rect.height,
                      };
                    }
                    """,
                    arg={"text": display_name},
                )
                if not isinstance(bounds, dict):
                    continue
                rows.append(
                    WorkspaceSwitcherSavedWorkspaceRowObservation(
                        display_name=display_name,
                        target_type_label=match.group("type").strip(),
                        state_label=match.group("state").strip(),
                        detail_text=match.group("detail").strip(),
                        selected=match.group("action").strip() == "Active",
                        action_labels=(
                            match.group("action").strip(),
                            match.group("delete").strip(),
                        ),
                        left=float(bounds.get("left", 0.0)),
                        top=float(bounds.get("top", 0.0)),
                        width=float(bounds.get("width", 0.0)),
                        height=float(bounds.get("height", 0.0)),
                    ),
                )
        if not rows:
            rows = list(self._accessible_saved_workspace_rows(timeout_ms=timeout_ms))
        if not rows:
            raise AssertionError(
                "The open workspace switcher did not expose any readable saved workspace rows.\n"
                f"Observed body text:\n{body_text}",
            )
        return tuple(rows)

    def observe_accessible_saved_workspace_rows(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> tuple[WorkspaceSwitcherRowObservation, ...]:
        del timeout_ms
        payload = self._session.evaluate(
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
              const accessibleLabel = (element) =>
                normalize(
                  element?.getAttribute?.('aria-label')
                    || element?.getAttribute?.('alt')
                    || element?.getAttribute?.('title')
                    || element?.innerText
                    || element?.textContent
                    || ''
                );
              const stateLabels = [
                'Local Git',
                'Sync issue',
                'Needs sign-in',
                'Connected',
                'Read-only',
                'Saved hosted workspace',
                'Unavailable',
                'Attachments limited',
              ];
              const actionLabelMatcher = (label) =>
                label === 'Active'
                || label.startsWith('Retry:')
                || label.startsWith('Open:')
                || label.startsWith('Re-authenticate:')
                || label.startsWith('Reauthenticate:')
                || label.startsWith('Delete:');
              const visibleButtons = Array.from(
                document.querySelectorAll('button,[role="button"],flt-semantics[role="button"],[aria-label]'),
              ).filter(isVisible);
              const rows = visibleButtons
                .map((element) => {
                  const summaryLabel = accessibleLabel(element);
                  if (
                    summaryLabel.startsWith('Workspace switcher:')
                    || !summaryLabel.includes('Branch:')
                  ) {
                    return null;
                  }
                  const summaryParts = summaryLabel.split(',').map((part) => normalize(part));
                  if (summaryParts.length < 4) {
                    return null;
                  }
                  const displayName = summaryParts[0];
                  const targetTypeLabel = summaryParts[1];
                  const stateLabel = summaryParts[2];
                  const detailText = summaryParts.slice(3).join(', ');
                  if (
                    !displayName
                    || (targetTypeLabel !== 'Hosted' && targetTypeLabel !== 'Local')
                    || !stateLabels.includes(stateLabel)
                    || !detailText.includes('Branch:')
                  ) {
                    return null;
                  }
                  let rowElement = element;
                  let current = element.parentElement;
                  while (current && current !== document.body) {
                    const labels = Array.from(
                      current.querySelectorAll('button,[role="button"],flt-semantics[role="button"],[aria-label]'),
                    )
                      .filter(isVisible)
                      .map((candidate) => accessibleLabel(candidate))
                      .filter((label) => actionLabelMatcher(label));
                    if (
                      labels.some((label) => label.startsWith('Delete:'))
                      && labels.some((label) => !label.startsWith('Delete:'))
                    ) {
                      rowElement = current;
                      break;
                    }
                    current = current.parentElement;
                  }
                  const buttonLabels = Array.from(
                    rowElement.querySelectorAll('button,[role="button"],flt-semantics[role="button"],[aria-label]'),
                  )
                    .filter(isVisible)
                    .map((candidate) => accessibleLabel(candidate))
                    .filter((label) => actionLabelMatcher(label));
                  return {
                    displayName,
                    targetTypeLabel,
                    stateLabel,
                    detailText,
                    visibleText: [summaryLabel, ...buttonLabels].join(' ').trim(),
                    selected: buttonLabels.includes('Active'),
                    semanticsLabel: summaryLabel,
                    iconAccessibilityLabel: null,
                    actionLabels: buttonLabels.filter((label) => !label.startsWith('Delete:')),
                    buttonLabels,
                  };
                })
                .filter((row) => row !== null);
              return rows;
            }
            """,
        )
        if not isinstance(payload, list) or not payload:
            raise AssertionError(
                "The open workspace switcher did not expose any accessible saved workspace rows.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return tuple(
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
            for row in payload
        )

    def observe_saved_workspace_row(
        self,
        *,
        display_name: str,
        target_path: str,
        target_type_label: str | None = None,
        expected_state_label: str | None = None,
        accepted_action_labels: tuple[str, ...] = (),
        disallowed_action_labels: tuple[str, ...] = (),
        timeout_ms: int = 10_000,
    ) -> WorkspaceSwitcherRowObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({
                  displayName,
                  targetPath,
                  targetTypeLabel,
                  expectedStateLabel,
                  acceptedActions,
                  disallowedActions,
                }) => {
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
                        || '',
                    );
                  const allButtons = Array.from(
                    document.querySelectorAll('button,[role="button"],flt-semantics[role="button"]'),
                  ).filter((candidate) => isVisible(candidate));
                  const rowButton = allButtons.find((candidate) => {
                    const label = accessibleLabel(candidate);
                    if (!label.includes(displayName) || !label.includes(targetPath)) {
                      return false;
                    }
                    if (targetTypeLabel && !label.includes(targetTypeLabel)) {
                      return false;
                    }
                    if (expectedStateLabel && !label.includes(expectedStateLabel)) {
                      return false;
                    }
                    return true;
                  });
                  if (!rowButton) {
                    return null;
                  }
                  const rowLabel = accessibleLabel(rowButton);
                  const rect = rowButton.getBoundingClientRect();
                  const buttonLabels = allButtons
                    .filter((candidate) => {
                      const label = accessibleLabel(candidate);
                      const candidateRect = candidate.getBoundingClientRect();
                      return label.endsWith(`: ${displayName}`)
                        && candidateRect.top >= (rect.bottom - 4)
                        && candidateRect.top <= (rect.bottom + 64)
                        && candidateRect.left >= (rect.left - 8)
                        && candidateRect.left <= (rect.right + 120);
                    })
                    .map((candidate) => accessibleLabel(candidate));
                  const actionLabels = buttonLabels
                    .map((label) => label.split(':', 1)[0].trim())
                    .filter((label) =>
                      acceptedActions.includes(label)
                      || disallowedActions.includes(label)
                      || label === 'Delete',
                    );
                  const headerParts = rowLabel.split(',').map((part) => normalize(part));
                  const detailText =
                    headerParts.length >= 4
                      ? headerParts.slice(3).join(', ')
                      : (rowLabel.includes(targetPath) ? rowLabel : '');
                  return {
                    displayName,
                    targetTypeLabel: targetTypeLabel && rowLabel.includes(targetTypeLabel)
                      ? targetTypeLabel
                      : null,
                    stateLabel: expectedStateLabel && rowLabel.includes(expectedStateLabel)
                      ? expectedStateLabel
                      : null,
                    detailText,
                    visibleText: rowLabel,
                    selected: rowLabel.includes('Active'),
                    semanticsLabel: rowLabel || null,
                    iconAccessibilityLabel: null,
                    actionLabels,
                    buttonLabels,
                  };
                }
                """,
                arg={
                    "displayName": display_name,
                    "targetPath": target_path,
                    "targetTypeLabel": target_type_label,
                    "expectedStateLabel": expected_state_label,
                    "acceptedActions": list(accepted_action_labels),
                    "disallowedActions": list(disallowed_action_labels),
                },
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open Workspace switcher did not expose the "{display_name}" saved '
                "workspace row with readable state and action labels.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                f'The open Workspace switcher did not expose the "{display_name}" saved '
                "workspace row with readable state and action labels."
            )
        return WorkspaceSwitcherRowObservation(
            display_name=str(payload.get("displayName", "")),
            target_type_label=(
                None if payload.get("targetTypeLabel") is None else str(payload.get("targetTypeLabel"))
            ),
            state_label=(
                None if payload.get("stateLabel") is None else str(payload.get("stateLabel"))
            ),
            detail_text=str(payload.get("detailText", "")),
            visible_text=str(payload.get("visibleText", "")),
            selected=bool(payload.get("selected")),
            semantics_label=(
                None if payload.get("semanticsLabel") is None else str(payload.get("semanticsLabel"))
            ),
            icon_accessibility_label=(
                None
                if payload.get("iconAccessibilityLabel") is None
                else str(payload.get("iconAccessibilityLabel"))
            ),
            action_labels=tuple(str(label) for label in payload.get("actionLabels", [])),
            button_labels=tuple(str(label) for label in payload.get("buttonLabels", [])),
        )

    def wait_for_refreshed_switcher_row_state(
        self,
        *,
        display_name: str,
        target_path: str,
        target_type_label: str | None = None,
        expected_state_label: str | None = None,
        accepted_action_labels: tuple[str, ...] = (),
        timeout_ms: int = 10_000,
    ) -> WorkspaceSwitcherObservation:
        try:
            self._session.wait_for_function(
                """
                ({
                  heading,
                  displayName,
                  targetPath,
                  targetTypeLabel,
                  expectedStateLabel,
                  acceptedActions,
                }) => {
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
                        || '',
                    );
                  const bodyText = document.body?.innerText ?? '';
                  if (!bodyText.includes(heading)) {
                    return null;
                  }
                  const allButtons = Array.from(
                    document.querySelectorAll('button,[role="button"],flt-semantics[role="button"]'),
                  ).filter((candidate) => isVisible(candidate));
                  const rowButton = allButtons.find((candidate) => {
                    const label = accessibleLabel(candidate);
                    if (!label.includes(displayName) || !label.includes(targetPath)) {
                      return false;
                    }
                    if (targetTypeLabel && !label.includes(targetTypeLabel)) {
                      return false;
                    }
                    if (expectedStateLabel && !label.includes(expectedStateLabel)) {
                      return false;
                    }
                    return true;
                  });
                  if (!rowButton) {
                    return null;
                  }
                  const rowLabel = accessibleLabel(rowButton);
                  const rect = rowButton.getBoundingClientRect();
                  const buttonLabels = allButtons
                    .filter((candidate) => candidate !== rowButton)
                    .filter((candidate) => {
                      const candidateRect = candidate.getBoundingClientRect();
                      return candidateRect.top >= (rect.bottom - 4)
                        && candidateRect.top <= (rect.bottom + 64)
                        && candidateRect.left >= (rect.left - 8)
                        && candidateRect.left <= (rect.right + 120);
                    })
                    .map((candidate) => accessibleLabel(candidate))
                    .filter(Boolean);
                  const actionLabels = buttonLabels.map((label) => {
                    const separatorIndex = label.indexOf(':');
                    return separatorIndex === -1 ? label.trim() : label.slice(0, separatorIndex).trim();
                  });
                  if (rowLabel.includes('Local Git') || rowLabel.includes('Active')) {
                    return null;
                  }
                  if (buttonLabels.includes('Active')) {
                    return null;
                  }
                  if (buttonLabels.some((label) => label.includes('Local Git'))) {
                    return null;
                  }
                  if (
                    acceptedActions.length > 0
                    && !acceptedActions.some((label) => actionLabels.includes(label))
                  ) {
                    return null;
                  }
                  return true;
                }
                """,
                arg={
                    "heading": self._switcher_heading,
                    "displayName": display_name,
                    "targetPath": target_path,
                    "targetTypeLabel": target_type_label,
                    "expectedStateLabel": expected_state_label,
                    "acceptedActions": list(accepted_action_labels),
                },
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError:
            pass
        return self.observe_open_switcher(timeout_ms=min(timeout_ms, 5_000))

    def click_saved_workspace_row_surface(
        self,
        display_name: str,
        *,
        timeout_ms: int = 10_000,
    ) -> None:
        rows = self.observe_saved_workspace_rows(timeout_ms=timeout_ms)
        row = next((candidate for candidate in rows if candidate.display_name == display_name), None)
        if row is None:
            raise AssertionError(
                f'The open workspace switcher did not expose a saved workspace row for "{display_name}".\n'
                f"Observed body text:\n{self.current_body_text()}",
            )
        self._session.mouse_click(
            row.left + min(40.0, row.width * 0.15),
            row.top + min(28.0, row.height * 0.25),
        )

    def click_saved_workspace_action_button(
        self,
        action_label: str,
        *,
        timeout_ms: int = 10_000,
    ) -> None:
        escaped_action_label = (
            action_label.replace("\\", "\\\\").replace('"', '\\"')
        )
        payload = self._session.evaluate(
            """
            (targetLabel) => {
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
              const match = Array.from(
                document.querySelectorAll(
                  'button[aria-label],flt-semantics[role="button"][aria-label],[role="button"][aria-label]'
                )
              )
                .filter((element) => isVisible(element))
                .find((element) => normalize(element.getAttribute('aria-label') || '') === targetLabel);
              if (!match) {
                return null;
              }
              match.click();
              return {
                clicked: true,
                tagName: match.tagName,
                ariaLabel: normalize(match.getAttribute('aria-label') || ''),
              };
            }
            """,
            arg=action_label,
        )
        if isinstance(payload, dict) and bool(payload.get("clicked")):
            return
        try:
            self._session.click(
                'flt-semantics[role="button"],button,[role="button"]',
                has_text=action_label,
                timeout_ms=timeout_ms,
            )
            return
        except WebAppTimeoutError as error:
            text_match_error = error

        try:
            self._session.click(
                (
                    'flt-semantics[role="button"][aria-label="'
                    f'{escaped_action_label}'
                    '"],button[aria-label="'
                    f'{escaped_action_label}'
                    '"],[role="button"][aria-label="'
                    f'{escaped_action_label}'
                    '"]'
                ),
                timeout_ms=timeout_ms,
            )
            return
        except WebAppTimeoutError:
            pass

        payload = self._session.evaluate(
            """
            (targetLabel) => {
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
              const match = Array.from(
                document.querySelectorAll(
                  'flt-semantics[role="button"],button,[role="button"],[aria-label]'
                )
              )
                .filter((element) => isVisible(element))
                .find((element) => normalize(element.getAttribute('aria-label') || '') === targetLabel);
              if (!match) {
                return null;
              }
              const rect = match.getBoundingClientRect();
              return {
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height,
              };
            }
            """,
            arg=action_label,
        )
        if isinstance(payload, dict):
            self._session.mouse_click(
                float(payload["left"]) + float(payload["width"]) / 2,
                float(payload["top"]) + float(payload["height"]) / 2,
            )
            return

        raise AssertionError(
            "The open workspace switcher did not expose the expected saved workspace "
            f"action button {action_label!r}.\n"
            f"Observed body text:\n{self.current_body_text()}",
        ) from text_match_error

    def wait_for_active_saved_workspace(
        self,
        display_name: str,
        *,
        timeout_ms: int = 10_000,
    ) -> WorkspaceSwitcherSavedWorkspaceRowObservation:
        try:
            self._session.wait_for_function(
                """
                ({ displayName }) => {
                  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                  const bodyText = normalize(document.body?.innerText || document.body?.textContent || '');
                  const activeMarker = `Active Delete: ${displayName}`;
                  const activeIndex = bodyText.indexOf(activeMarker);
                  if (activeIndex < 0) {
                    return null;
                  }
                  const displayIndex = bodyText.lastIndexOf(displayName, activeIndex);
                  return displayIndex >= 0
                    ? bodyText.slice(displayIndex, activeIndex + activeMarker.length)
                    : activeMarker;
                }
                """,
                arg={
                    "displayName": display_name,
                },
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'The open workspace switcher never marked "{display_name}" as the active '
                "saved workspace within the expected wait window.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        rows = self.observe_saved_workspace_rows(timeout_ms=timeout_ms)
        active_row = next((row for row in rows if row.selected), None)
        if active_row is None:
            raise AssertionError(
                "The open workspace switcher did not expose an active saved workspace row "
                "after waiting for the selection change.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return active_row
    def workspace_trigger_reached(
        self,
        sequence: tuple[FocusNavigationStep, ...],
    ) -> bool:
        return any(self._is_workspace_trigger_label(step.after_label) for step in sequence)

    def observe_trigger_focusability(
        self,
        *,
        timeout_ms: int = 30_000,
    ) -> WorkspaceTriggerFocusabilityObservation:
        payload = self._session.wait_for_function(
            """
            ({ triggerLabelPrefix }) => {
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
                normalize(element?.getAttribute?.('aria-label') || element?.innerText || '');
              const trigger = Array.from(
                document.querySelectorAll('flt-semantics[role="button"],[role="button"]'),
              )
                .filter(isVisible)
                .find((element) => labelFor(element).startsWith(triggerLabelPrefix));
              if (!trigger) {
                return null;
              }
              const tabindex = trigger.getAttribute('tabindex');
              return {
                label: labelFor(trigger),
                role: trigger.getAttribute('role'),
                tagName: trigger.tagName,
                tabindex,
                keyboardFocusable: tabindex !== null && tabindex !== '-1',
                outerHtml: trigger.outerHTML?.slice?.(0, 400) || '',
              };
            }
            """,
            arg={"triggerLabelPrefix": self._trigger_label_prefix},
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The live app did not expose a visible workspace switcher trigger for "
                "keyboard-focus inspection.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceTriggerFocusabilityObservation(
            label=str(payload.get("label", "")),
            role=str(payload.get("role")) if payload.get("role") is not None else None,
            tag_name=str(payload.get("tagName", "")),
            tabindex=(
                str(payload.get("tabindex"))
                if payload.get("tabindex") is not None
                else None
            ),
            keyboard_focusable=bool(payload.get("keyboardFocusable")),
            outer_html=str(payload.get("outerHtml", "")),
        )

    def observe_trigger_aria_expanded(
        self,
        *,
        expected_value: str | None = None,
        timeout_ms: int = 30_000,
    ) -> WorkspaceTriggerAriaExpandedObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({ triggerLabelPrefix, expectedValue }) => {
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
                    normalize(element?.getAttribute?.('aria-label') || element?.innerText || '');
                  const trigger = Array.from(
                    document.querySelectorAll('flt-semantics[role="button"],[role="button"]'),
                  )
                    .filter(isVisible)
                    .find((element) => labelFor(element).startsWith(triggerLabelPrefix));
                  if (!trigger) {
                    return null;
                  }
                  const ariaExpanded = trigger.getAttribute('aria-expanded');
                  if (expectedValue !== null && ariaExpanded !== expectedValue) {
                    return null;
                  }
                  const tabindex = trigger.getAttribute('tabindex');
                  return {
                    label: labelFor(trigger),
                    role: trigger.getAttribute('role'),
                    tagName: trigger.tagName,
                    tabindex,
                    keyboardFocusable: tabindex !== null && tabindex !== '-1',
                    ariaExpanded,
                    outerHtml: trigger.outerHTML?.slice?.(0, 400) || '',
                  };
                }
                """,
                arg={
                    "triggerLabelPrefix": self._trigger_label_prefix,
                    "expectedValue": expected_value,
                },
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            expected_description = (
                f" with aria-expanded={expected_value!r}" if expected_value is not None else ""
            )
            raise AssertionError(
                "The live app did not expose a visible workspace switcher trigger"
                f"{expected_description} for ARIA inspection.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "The live app did not expose a readable workspace switcher trigger for "
                "ARIA inspection.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceTriggerAriaExpandedObservation(
            label=str(payload.get("label", "")),
            role=str(payload.get("role")) if payload.get("role") is not None else None,
            tag_name=str(payload.get("tagName", "")),
            tabindex=(
                str(payload.get("tabindex"))
                if payload.get("tabindex") is not None
                else None
            ),
            keyboard_focusable=bool(payload.get("keyboardFocusable")),
            aria_expanded=(
                str(payload.get("ariaExpanded"))
                if payload.get("ariaExpanded") is not None
                else None
            ),
            outer_html=str(payload.get("outerHtml", "")),
        )

    def observe_trigger_aria_controls(
        self,
        *,
        timeout_ms: int = 30_000,
    ) -> WorkspaceTriggerAriaControlsObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({ triggerLabelPrefix }) => {
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
                    normalize(element?.getAttribute?.('aria-label') || element?.innerText || '');
                  const trigger = Array.from(
                    document.querySelectorAll('flt-semantics[role="button"],[role="button"]'),
                  )
                    .filter(isVisible)
                    .find((element) => labelFor(element).startsWith(triggerLabelPrefix));
                  if (!trigger) {
                    return null;
                  }
                  const tabindex = trigger.getAttribute('tabindex');
                  return {
                    label: labelFor(trigger),
                    role: trigger.getAttribute('role'),
                    tagName: trigger.tagName,
                    tabindex,
                    keyboardFocusable: tabindex !== null && tabindex !== '-1',
                    ariaControls: trigger.getAttribute('aria-controls'),
                    outerHtml: trigger.outerHTML?.slice?.(0, 400) || '',
                  };
                }
                """,
                arg={"triggerLabelPrefix": self._trigger_label_prefix},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "The live app did not expose a visible workspace switcher trigger for "
                "aria-controls inspection.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "The live app did not expose a readable workspace switcher trigger for "
                "aria-controls inspection.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceTriggerAriaControlsObservation(
            label=str(payload.get("label", "")),
            role=str(payload.get("role")) if payload.get("role") is not None else None,
            tag_name=str(payload.get("tagName", "")),
            tabindex=(
                str(payload.get("tabindex"))
                if payload.get("tabindex") is not None
                else None
            ),
            keyboard_focusable=bool(payload.get("keyboardFocusable")),
            aria_controls=(
                str(payload.get("ariaControls"))
                if payload.get("ariaControls") is not None
                else None
            ),
            outer_html=str(payload.get("outerHtml", "")),
        )

    def observe_trigger_aria_controls_target(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> WorkspaceTriggerAriaControlsTargetObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({ triggerLabelPrefix }) => {
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
                    normalize(element?.getAttribute?.('aria-label') || element?.innerText || '');
                  const trigger = Array.from(
                    document.querySelectorAll('flt-semantics[role="button"],[role="button"]'),
                  )
                    .filter(isVisible)
                    .find((element) => labelFor(element).startsWith(triggerLabelPrefix));
                  if (!trigger) {
                    return null;
                  }

                  const triggerAriaControls = trigger.getAttribute('aria-controls');
                  const controlledElement = triggerAriaControls
                    ? document.getElementById(triggerAriaControls)
                    : null;
                  return {
                    triggerLabel: labelFor(trigger),
                    triggerAriaControls,
                    controlledElementFound: Boolean(controlledElement),
                    controlledElementVisible: Boolean(controlledElement) && isVisible(controlledElement),
                    controlledElementId: controlledElement?.id || null,
                    controlledElementRole: controlledElement?.getAttribute?.('role') || null,
                    controlledElementTagName: controlledElement?.tagName || null,
                    controlledElementText: normalize(
                      controlledElement?.innerText || controlledElement?.textContent || '',
                    ),
                    triggerOuterHtml: trigger.outerHTML?.slice?.(0, 400) || '',
                    controlledElementOuterHtml: controlledElement?.outerHTML?.slice?.(0, 400) || '',
                  };
                }
                """,
                arg={"triggerLabelPrefix": self._trigger_label_prefix},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "The live app did not expose a visible workspace switcher trigger for "
                "aria-controls target inspection.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "The live app did not expose a readable workspace switcher trigger for "
                "aria-controls target inspection.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceTriggerAriaControlsTargetObservation(
            trigger_label=str(payload.get("triggerLabel", "")),
            trigger_aria_controls=(
                str(payload.get("triggerAriaControls"))
                if payload.get("triggerAriaControls") is not None
                else None
            ),
            controlled_element_found=bool(payload.get("controlledElementFound")),
            controlled_element_visible=bool(payload.get("controlledElementVisible")),
            controlled_element_id=(
                str(payload.get("controlledElementId"))
                if payload.get("controlledElementId") is not None
                else None
            ),
            controlled_element_role=(
                str(payload.get("controlledElementRole"))
                if payload.get("controlledElementRole") is not None
                else None
            ),
            controlled_element_tag_name=(
                str(payload.get("controlledElementTagName"))
                if payload.get("controlledElementTagName") is not None
                else None
            ),
            controlled_element_text=str(payload.get("controlledElementText", "")),
            trigger_outer_html=str(payload.get("triggerOuterHtml", "")),
            controlled_element_outer_html=str(payload.get("controlledElementOuterHtml", "")),
        )

    def observe_surface_reference(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> WorkspaceSwitcherSurfaceReferenceObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({ triggerLabelPrefix }) => {
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
                    normalize(element?.getAttribute?.('aria-label') || element?.innerText || '');
                  const trigger = Array.from(
                    document.querySelectorAll('flt-semantics[role="button"],[role="button"]'),
                  )
                    .filter(isVisible)
                    .find((element) => labelFor(element).startsWith(triggerLabelPrefix));
                  if (!trigger) {
                    return null;
                  }

                  const visibleDialogs = Array.from(
                    document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
                  ).filter(isVisible);
                  let switcher = visibleDialogs.find((candidate) =>
                    normalize(candidate.innerText || candidate.textContent).includes('Workspace switcher'),
                  );
                  if (!switcher) {
                    const headings = Array.from(document.querySelectorAll('*'))
                      .filter(isVisible)
                      .map((element) => ({
                        element,
                        label: normalize(element.getAttribute?.('aria-label') || ''),
                        text: normalize(element.innerText || element.textContent || ''),
                        area: (() => {
                          const rect = element.getBoundingClientRect();
                          return rect.width * rect.height;
                        })(),
                      }))
                      .filter((candidate) =>
                        candidate.label === 'Workspace switcher'
                        || candidate.text === 'Workspace switcher'
                        || (
                          candidate.text.includes('Workspace switcher')
                          && (
                            candidate.text.includes('Saved workspaces')
                            || candidate.text.includes('Save and switch')
                            || candidate.text.includes('Hosted Local')
                            || candidate.text.includes('Add workspace')
                          )
                        )
                      )
                      .sort((left, right) => left.area - right.area);
                    for (const headingCandidate of headings) {
                      let current = headingCandidate.element;
                      while (current && current !== document.body) {
                        const text = normalize(current.innerText || current.textContent || '');
                        if (
                          text.includes('Workspace switcher')
                          && (
                            text.includes('Saved workspaces')
                            || text.includes('Save and switch')
                            || text.includes('Hosted Local')
                            || text.includes('Add workspace')
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

                  const triggerAriaControls = trigger.getAttribute('aria-controls');
                  const controlledSurface = triggerAriaControls
                    ? document.getElementById(triggerAriaControls)
                    : null;
                  const controlledVisible = Boolean(controlledSurface) && isVisible(controlledSurface);
                  return {
                    triggerLabel: labelFor(trigger),
                    triggerAriaControls,
                    controlledSurfaceFound: Boolean(controlledSurface),
                    controlledSurfaceVisible: controlledVisible,
                    controlledSurfaceId: controlledSurface?.id || null,
                    controlledSurfaceRole: controlledSurface?.getAttribute?.('role') || null,
                    controlledSurfaceTagName: controlledSurface?.tagName || null,
                    controlledSurfaceText: normalize(
                      controlledSurface?.innerText || controlledSurface?.textContent || '',
                    ),
                    visibleSurfaceId: switcher.id || null,
                    visibleSurfaceRole: switcher.getAttribute?.('role') || null,
                    visibleSurfaceTagName: switcher.tagName || null,
                    visibleSurfaceText: normalize(switcher.innerText || switcher.textContent || ''),
                    triggerOuterHtml: trigger.outerHTML?.slice?.(0, 400) || '',
                    visibleSurfaceOuterHtml: switcher.outerHTML?.slice?.(0, 400) || '',
                  };
                }
                """,
                arg={"triggerLabelPrefix": self._trigger_label_prefix},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "The deployed app did not expose a readable visible workspace switcher "
                "surface for aria-controls linkage inspection.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "The deployed app did not expose a readable workspace switcher trigger "
                "and surface reference for aria-controls linkage inspection.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceSwitcherSurfaceReferenceObservation(
            trigger_label=str(payload.get("triggerLabel", "")),
            trigger_aria_controls=(
                str(payload.get("triggerAriaControls"))
                if payload.get("triggerAriaControls") is not None
                else None
            ),
            controlled_surface_found=bool(payload.get("controlledSurfaceFound")),
            controlled_surface_visible=bool(payload.get("controlledSurfaceVisible")),
            controlled_surface_id=(
                str(payload.get("controlledSurfaceId"))
                if payload.get("controlledSurfaceId") is not None
                else None
            ),
            controlled_surface_role=(
                str(payload.get("controlledSurfaceRole"))
                if payload.get("controlledSurfaceRole") is not None
                else None
            ),
            controlled_surface_tag_name=(
                str(payload.get("controlledSurfaceTagName"))
                if payload.get("controlledSurfaceTagName") is not None
                else None
            ),
            controlled_surface_text=str(payload.get("controlledSurfaceText", "")),
            visible_surface_id=(
                str(payload.get("visibleSurfaceId"))
                if payload.get("visibleSurfaceId") is not None
                else None
            ),
            visible_surface_role=(
                str(payload.get("visibleSurfaceRole"))
                if payload.get("visibleSurfaceRole") is not None
                else None
            ),
            visible_surface_tag_name=(
                str(payload.get("visibleSurfaceTagName"))
                if payload.get("visibleSurfaceTagName") is not None
                else None
            ),
            visible_surface_text=str(payload.get("visibleSurfaceText", "")),
            trigger_outer_html=str(payload.get("triggerOuterHtml", "")),
            visible_surface_outer_html=str(payload.get("visibleSurfaceOuterHtml", "")),
        )

    def focus_trigger_via_keyboard(
        self,
        *,
        max_tabs: int = 12,
        timeout_ms: int = 30_000,
    ) -> tuple[FocusNavigationStep, ...]:
        self.focus_search_field(timeout_ms=timeout_ms)
        return self._focus_trigger_via_keyboard_after_current_focus(
            max_tabs=max_tabs,
            timeout_ms=timeout_ms,
            start_description="the visible top-bar search field",
        )

    def focus_trigger_via_keyboard_from_current_focus(
        self,
        *,
        max_tabs: int = 12,
        timeout_ms: int = 30_000,
    ) -> tuple[FocusNavigationStep, ...]:
        return self._focus_trigger_via_keyboard_after_current_focus(
            max_tabs=max_tabs,
            timeout_ms=timeout_ms,
            start_description="the current active element",
        )

    def _focus_trigger_via_keyboard_after_current_focus(
        self,
        *,
        max_tabs: int,
        timeout_ms: int,
        start_description: str,
    ) -> tuple[FocusNavigationStep, ...]:
        steps: list[FocusNavigationStep] = []
        for step_index in range(1, max_tabs + 1):
            before = self._session.active_element()
            self._session.press_key("Tab", timeout_ms=timeout_ms)
            after = self._session.active_element()
            step = FocusNavigationStep(
                step=step_index,
                before_label=before.accessible_name,
                before_role=before.role,
                after_label=after.accessible_name,
                after_role=after.role,
                after_tag_name=after.tag_name,
                after_outer_html=after.outer_html,
            )
            steps.append(step)
            if self._is_workspace_trigger_label(after.accessible_name):
                return tuple(steps)
        raise AssertionError(
            f"Keyboard Tab navigation from {start_description} never reached the "
            "workspace switcher trigger.\n"
            + "Observed focus sequence: "
            + " -> ".join(
                self._describe_focus_step_target(
                    step.after_label,
                    step.after_tag_name,
                )
                for step in steps
            )
        )

    @staticmethod
    def _describe_focus_step_target(label: str | None, tag_name: str | None) -> str:
        normalized = re.sub(r"\s+", " ", label or "").strip()
        if not normalized:
            return f"<{tag_name or 'unknown'}>"
        if len(normalized) > 96:
            return normalized[:93] + "..."
        return normalized

    def press_enter_on_active_element_and_wait_for_surface(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> None:
        self._session.press_key("Enter", timeout_ms=timeout_ms)
        self._wait_for_surface(timeout_ms=timeout_ms)

    def press_space_on_active_element_and_wait_for_surface(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> None:
        self._session.press_key("Space", timeout_ms=timeout_ms)
        self._wait_for_surface(timeout_ms=timeout_ms)

    def press_space_on_active_element_and_wait_for_dismissal(
        self,
        *,
        timeout_ms: int = 4_000,
        stability_window_ms: int = 400,
    ) -> WorkspaceSwitcherTriggerDismissObservation:
        self._session.press_key("Space", timeout_ms=timeout_ms)
        try:
            payload = self._wait_for_dismissal_payload(
                timeout_ms=timeout_ms,
                stability_window_ms=stability_window_ms,
            )
        except WebAppTimeoutError as error:
            active = self._session.active_element()
            raise AssertionError(
                "Pressing Space on the active element did not dismiss the workspace "
                "switcher surface.\n"
                f"Observed active element label: {active.accessible_name!r}\n"
                f"Observed active element role: {active.role!r}\n"
                f"Observed active element HTML: {active.outer_html}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher Space-key dismissal did not return a readable "
                "observation."
            )
        return WorkspaceSwitcherTriggerDismissObservation(
            body_text=str(payload.get("bodyText", "")),
            dashboard_visible=bool(payload.get("dashboardVisible")),
            trigger_visible=bool(payload.get("triggerVisible")),
            trigger_label=(
                str(payload.get("triggerLabel"))
                if payload.get("triggerLabel") is not None
                else None
            ),
        )

    def press_enter_on_active_element_and_wait_for_dismissal(
        self,
        *,
        timeout_ms: int = 4_000,
        stability_window_ms: int = 400,
    ) -> WorkspaceSwitcherTriggerDismissObservation:
        self._session.press_key("Enter", timeout_ms=timeout_ms)
        try:
            payload = self._wait_for_dismissal_payload(
                timeout_ms=timeout_ms,
                stability_window_ms=stability_window_ms,
            )
        except WebAppTimeoutError as error:
            active = self._session.active_element()
            raise AssertionError(
                "Pressing Enter on the active element did not dismiss the workspace "
                "switcher surface.\n"
                f"Observed active element label: {active.accessible_name!r}\n"
                f"Observed active element role: {active.role!r}\n"
                f"Observed active element HTML: {active.outer_html}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher Enter-key dismissal did not return a readable "
                "observation."
            )
        return WorkspaceSwitcherTriggerDismissObservation(
            body_text=str(payload.get("bodyText", "")),
            dashboard_visible=bool(payload.get("dashboardVisible")),
            trigger_visible=bool(payload.get("triggerVisible")),
            trigger_label=(
                str(payload.get("triggerLabel"))
                if payload.get("triggerLabel") is not None
                else None
            ),
        )

    def wait_for_dismissal_after_trigger_space(
        self,
        *,
        timeout_ms: int = 4_000,
        stability_window_ms: int = 400,
    ) -> WorkspaceSwitcherTriggerDismissObservation:
        try:
            payload = self._wait_for_dismissal_payload(
                timeout_ms=timeout_ms,
                stability_window_ms=stability_window_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 6 failed: pressing Space on the already-open workspace switcher "
                "trigger did not dismiss the surface.\n"
                f"Observed body text after pressing Space again:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher Space-key dismissal did not return a readable "
                "observation."
            )
        return WorkspaceSwitcherTriggerDismissObservation(
            body_text=str(payload.get("bodyText", "")),
            dashboard_visible=bool(payload.get("dashboardVisible")),
            trigger_visible=bool(payload.get("triggerVisible")),
            trigger_label=(
                str(payload.get("triggerLabel"))
                if payload.get("triggerLabel") is not None
                else None
            ),
        )

    def wait_for_dismissal_after_trigger_enter(
        self,
        *,
        timeout_ms: int = 4_000,
        stability_window_ms: int = 400,
    ) -> WorkspaceSwitcherTriggerDismissObservation:
        try:
            payload = self._wait_for_dismissal_payload(
                timeout_ms=timeout_ms,
                stability_window_ms=stability_window_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 6 failed: pressing Enter on the already-open workspace switcher "
                "trigger did not dismiss the surface.\n"
                f"Observed body text after pressing Enter again:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher Enter-key dismissal did not return a readable "
                "observation."
            )
        return WorkspaceSwitcherTriggerDismissObservation(
            body_text=str(payload.get("bodyText", "")),
            dashboard_visible=bool(payload.get("dashboardVisible")),
            trigger_visible=bool(payload.get("triggerVisible")),
            trigger_label=(
                str(payload.get("triggerLabel"))
                if payload.get("triggerLabel") is not None
                else None
            ),
        )
    def open_surface_with_click(self, *, timeout_ms: int = 30_000) -> None:
        self._click_trigger(timeout_ms=timeout_ms)
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
              let switcher = visibleDialogs.find((candidate) =>
                normalize(candidate.innerText || candidate.textContent).includes('Workspace switcher'),
              );
              if (!switcher) {
                const headings = Array.from(document.querySelectorAll('*'))
                  .filter(isVisible)
                  .map((element) => ({
                    element,
                    label: normalize(element.getAttribute?.('aria-label') || ''),
                    text: normalize(element.innerText || element.textContent || ''),
                    area: (() => {
                      const rect = element.getBoundingClientRect();
                      return rect.width * rect.height;
                    })(),
                  }))
                  .filter((candidate) =>
                    candidate.label === 'Workspace switcher'
                    || candidate.text === 'Workspace switcher'
                    || (
                      candidate.text.includes('Workspace switcher')
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
                    const text = normalize(current.innerText || current.textContent || '');
                    if (
                      text.includes('Workspace switcher')
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
              const interactiveSelector = [
                'flt-semantics[role="button"]',
                'button',
                '[role="button"]',
                'input',
                'textarea',
              ].join(',');
              const panelScopedControls = Array.from(
                document.querySelectorAll('flt-semantics[role="button"],button,[role="button"]'),
              )
                .filter(isVisible)
                .filter((element) =>
                  element.getAttribute('data-trackstate-browser-focus-panel-id') === 'trackstate-workspace-switcher',
                );
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
                switcher.querySelectorAll(interactiveSelector),
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
              const panelScopedControlElements = panelScopedControls
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
                }))
                .filter((element) => element.label.length > 0);
              const missingInteractiveLabels = interactiveElements
                .filter((element) => element.label.length === 0)
                .map((element, index) =>
                  `${element.tagName}[${index}] role=${element.role ?? '<none>'}`,
                );
              const semanticsCandidates = [switcher, ...Array.from(switcher.querySelectorAll(semanticsSelector))]
                .filter(isVisible)
                .filter((element, index, all) => all.indexOf(element) === index);
              const semanticsNodes = semanticsCandidates
                .filter((element) => {
                  if (element === switcher) {
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
                .filter((node) =>
                  node.label.length === 0
                  && node.visibleText.length > 0
                )
                .map((node, index) =>
                  `${node.tagName}[${index}] role=${node.role ?? '<none>'} text=${node.visibleText || '<none>'}`,
                );
              const interactiveTextElements = Array.from(switcher.querySelectorAll(interactiveSelector))
                .filter(isVisible)
                .map((element) => {
                  const visibleText = visibleTextFor(element);
                  const backgroundColor = resolveBackgroundColor(
                    element,
                    toHex(window.getComputedStyle(switcher).backgroundColor),
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
              const deleteButtons = panelScopedControls
                .map((element) => {
                  const label = labelFor(element);
                  if (!label.startsWith('Delete:')) {
                    return null;
                  }
                  const backgroundColor = resolveBackgroundColor(
                    element,
                    toHex(window.getComputedStyle(switcher).backgroundColor),
                  );
                  const foregroundColor = resolveForegroundColor(element);
                  return {
                    label,
                    visibleText: label,
                    role: element.getAttribute('role'),
                    foregroundColor,
                    backgroundColor,
                    contrastRatio: contrastRatio(foregroundColor, backgroundColor),
                    ...rectPayload(element),
                  };
                })
                .filter((element) => element !== null);
              const interactiveTexts = [...interactiveTextElements];
              for (const candidate of deleteButtons) {
                if (interactiveTexts.some((element) =>
                  element.label === candidate.label
                  && Math.abs(element.x - candidate.x) < 1
                  && Math.abs(element.y - candidate.y) < 1
                  && Math.abs(element.width - candidate.width) < 1
                  && Math.abs(element.height - candidate.height) < 1
                )) {
                  continue;
                }
                interactiveTexts.push(candidate);
              }
              const panelScopedControlTexts = panelScopedControls
                .map((element) => {
                  const label = labelFor(element);
                  const visibleText = visibleTextFor(element) || label;
                  if (!label && !visibleText) {
                    return null;
                  }
                  const backgroundColor = resolveBackgroundColor(
                    element,
                    toHex(window.getComputedStyle(switcher).backgroundColor),
                  );
                  const foregroundColor = resolveForegroundColor(element);
                  return {
                    label,
                    visibleText,
                    role: element.getAttribute('role'),
                    foregroundColor,
                    backgroundColor,
                    contrastRatio: contrastRatio(foregroundColor, backgroundColor),
                    ...rectPayload(element),
                    tagName: element.tagName.toLowerCase(),
                  };
                })
                .filter((element) => element !== null);
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
              const dialogBackground = toHex(window.getComputedStyle(switcher).backgroundColor);
              const badgeElements = Array.from(switcher.querySelectorAll('*'))
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
              const triggerCandidates = [
                ...Array.from(document.querySelectorAll('button')),
                ...Array.from(document.querySelectorAll('flt-semantics[role="button"]')),
              ].filter((element, index, all) => all.indexOf(element) === index);
              const workspaceTrigger = triggerCandidates.find((candidate) =>
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
                ...Array.from(switcher.querySelectorAll(interactiveSelector)).filter(isVisible),
                ...panelScopedControls,
              ];
              const interactiveIcons = triggerAndDialogControls.flatMap((element) => {
                const icons = Array.from(element.querySelectorAll(iconSelector)).filter(isVisible);
                const label = labelFor(element);
                if (
                  !icons.length
                  && !label.startsWith('Workspace switcher:')
                  && !label.startsWith('Delete')
                ) {
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
                headingText: normalize(switcher.innerText || switcher.textContent).split(' ')[0] === 'Workspace'
                  ? 'Workspace switcher'
                  : normalize(switcher.innerText || switcher.textContent),
                interactiveElements,
                panelScopedControls: panelScopedControlElements,
                semanticsNodes,
                missingInteractiveLabels,
                missingSemanticsLabels,
                badges,
                interactiveIcons,
                interactiveTexts,
                panelScopedControlTexts,
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
        interactive_elements_payload = _merge_surface_payload_items(
            list(payload.get("interactiveElements", [])),
            list(payload.get("panelScopedControls", [])),
        )
        interactive_texts_payload = _merge_surface_payload_items(
            list(payload.get("interactiveTexts", [])),
            list(payload.get("panelScopedControlTexts", [])),
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
                for item in interactive_elements_payload
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
                for item in interactive_texts_payload
            ),
        )

    def open_and_observe(
        self,
        *,
        timeout_ms: int = 60_000,
    ) -> WorkspaceSwitcherObservation:
        self._click_trigger(timeout_ms=timeout_ms)
        return self.observe_open_switcher(timeout_ms=timeout_ms)

    def switch_to_workspace(
        self,
        *,
        display_name: str,
        target_type_label: str,
        detail_contains: str | None = None,
        expected_state_label: str | None = None,
        timeout_ms: int = 60_000,
    ) -> WorkspaceSwitcherTriggerObservation:
        try:
            switcher = self.observe_open_switcher(timeout_ms=min(timeout_ms, 5_000))
        except AssertionError:
            switcher = self.open_and_observe(timeout_ms=timeout_ms)
        open_labels = (
            f"Open: {display_name}",
            f"Open workspace: {display_name}",
        )
        clicked_open_label = self._session.evaluate(
            """
            ({ openLabels, displayName, targetTypeLabel, detailContains }) => {
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
                normalize(
                  element.getAttribute?.('aria-label')
                  || element.innerText
                  || element.textContent
                  || '',
                );
              const matchesRow = (element) => {
                let current = element;
                while (current && current !== document.body) {
                  const text = normalize(current.innerText || current.textContent || '');
                  if (
                    text.includes(displayName)
                    && text.includes(targetTypeLabel)
                    && (!detailContains || text.includes(detailContains))
                  ) {
                    return true;
                  }
                  current = current.parentElement;
                }
                return false;
              };
              const candidates = Array.from(document.querySelectorAll('*'))
                .filter(isVisible)
                .map((element) => ({
                  element,
                  label: labelFor(element),
                }))
                .filter((candidate) => openLabels.includes(candidate.label));
              const match =
                candidates.find((candidate) => matchesRow(candidate.element))
                ?? candidates[0]
                ?? null;
              if (!match) {
                return null;
              }
              match.element.click();
              return match.label;
            }
            """,
            arg={
                "openLabels": open_labels,
                "displayName": display_name,
                "targetTypeLabel": target_type_label,
                "detailContains": detail_contains,
            },
        )
        if clicked_open_label is None:
            raise AssertionError(
                f'The workspace switcher did not expose a selectable "{display_name}" '
                f'{target_type_label} workspace row.\n'
                f"Observed switcher text:\n{switcher.switcher_text}\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
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
                  return Array.from(document.querySelectorAll('*'))
                    .filter(isVisible)
                    .some((candidate) =>
                      normalize(candidate.innerText || candidate.textContent || '')
                        === 'Save and switch'
                    );
                }
                """,
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Selecting workspace "{display_name}" exposed `{clicked_open_label}`, '
                "but the follow-up `Save and switch` control never became visible.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        clicked_save = self._session.evaluate(
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
              const save = Array.from(document.querySelectorAll('*'))
                .filter((candidate) => isVisible(candidate))
                .find((candidate) =>
                  normalize(candidate.innerText || candidate.textContent || '') === 'Save and switch'
                );
              if (!save) {
                return false;
              }
              save.click();
              return true;
            }
            """,
        )
        if clicked_save is not True:
            raise AssertionError(
                f'Selecting workspace "{display_name}" exposed `{clicked_open_label}`, '
                "but the follow-up `Save and switch` control did not appear or could not "
                "be activated.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        try:
            self._session.wait_for_function(
                """
                ({ displayName, targetTypeLabel, expectedStateLabel }) => {
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
                  )
                    .filter(isVisible)
                    .find((element) =>
                      normalize(element.getAttribute('aria-label') || element.innerText || '')
                        .startsWith('Workspace switcher:'),
                    );
                  if (!trigger) {
                    return null;
                  }
                  const label = normalize(
                    trigger.getAttribute('aria-label') || trigger.innerText || '',
                  );
                  if (!label.includes(`Workspace switcher: ${displayName}, ${targetTypeLabel},`)) {
                    return null;
                  }
                  if (expectedStateLabel && !label.endsWith(expectedStateLabel)) {
                    return null;
                  }
                  return label;
                }
                """,
                arg={
                    "displayName": display_name,
                    "targetTypeLabel": target_type_label,
                    "expectedStateLabel": expected_state_label,
                },
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Switching to workspace "{display_name}" did not update the workspace '
                "switcher trigger to the expected active state.\n"
                f"Observed open action: {clicked_open_label!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        return self.observe_trigger(timeout_ms=timeout_ms)

    def observe_open_switcher(
        self,
        *,
        timeout_ms: int = 60_000,
    ) -> WorkspaceSwitcherObservation:
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

              const actionLabels = [
                'Open',
                'Open workspace',
                'Retry',
                'Re-authenticate',
                'Reauthenticate',
                'Active',
                'Delete',
              ];
              const stateLabels = [
                'Local Git',
                'Sync issue',
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
                  && (
                    candidate.text.includes('Open')
                    || candidate.text.includes('Retry')
                    || candidate.text.includes('Re-authenticate')
                    || candidate.text.includes('Reauthenticate')
                    || candidate.text.includes('Active')
                  )
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

              if (rows.length === 0) {
                const summaryPattern = new RegExp(
                  `^(.*?),\\s*(Hosted|Local),\\s*(${stateLabels.join('|')}),\\s*(.+Branch:.+)$`,
                );
                const accessibleRows = visibleElements(
                  document,
                  'button[aria-label],[role="button"][aria-label],flt-semantics[aria-label]',
                )
                  .map((element) => {
                    const summaryLabel = accessibleLabel(element);
                    const summaryMatch = summaryLabel.match(summaryPattern);
                    if (!summaryMatch) {
                      return null;
                    }
                    let rowElement = element;
                    let current = element.parentElement;
                    while (current && current !== switcher) {
                      const labels = visibleElements(
                        current,
                        'flt-semantics[role="button"],[role="button"],button',
                      )
                        .map((candidate) => accessibleLabel(candidate))
                        .filter((label) => label.length > 0);
                      if (
                        labels.some((label) => label.startsWith('Delete:'))
                        && labels.some((label) =>
                          label === 'Active'
                          || label.startsWith('Retry:')
                          || label.startsWith('Open:')
                          || label.startsWith('Re-authenticate:')
                          || label.startsWith('Reauthenticate:')
                        )
                      ) {
                        rowElement = current;
                        break;
                      }
                      current = current.parentElement;
                    }
                    const buttonLabels = visibleElements(
                      rowElement,
                      'flt-semantics[role="button"],[role="button"],button',
                    )
                      .map((candidate) => accessibleLabel(candidate))
                      .filter((label) => label.length > 0);
                    return {
                      displayName: summaryMatch[1],
                      targetTypeLabel: summaryMatch[2],
                      stateLabel: summaryMatch[3],
                      detailText: summaryMatch[4],
                      visibleText: [summaryLabel, ...buttonLabels].join(' ').trim(),
                      selected: buttonLabels.includes('Active'),
                      semanticsLabel: summaryLabel,
                      iconAccessibilityLabel: null,
                      actionLabels: buttonLabels.filter((label) =>
                        label === 'Active'
                        || label.startsWith('Retry:')
                        || label.startsWith('Open:')
                        || label.startsWith('Re-authenticate:')
                        || label.startsWith('Reauthenticate:')
                      ),
                      buttonLabels,
                    };
                  })
                  .filter((candidate) => candidate !== null);
                return {
                  bodyText,
                  switcherText: normalize(switcher.innerText || ''),
                  rows: accessibleRows,
                };
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
        if not rows:
            rows = tuple(
                WorkspaceSwitcherRowObservation(
                    display_name=row["display_name"],
                    target_type_label=row["target_type_label"],
                    state_label=row["state_label"],
                    detail_text=row["detail_text"],
                    visible_text=row["visible_text"],
                    selected=row["selected"],
                    semantics_label=row["semantics_label"],
                    icon_accessibility_label=None,
                    action_labels=row["action_labels"],
                    button_labels=row["button_labels"],
                )
                for row in self._accessible_saved_workspace_row_payloads(
                    timeout_ms=timeout_ms,
                )
            )
        return WorkspaceSwitcherObservation(
            body_text=str(payload.get("bodyText", "")),
            switcher_text=str(payload.get("switcherText", "")),
            row_count=len(rows),
            rows=rows,
        )

    def close(
        self,
        *,
        timeout_ms: int = 15_000,
    ) -> WorkspaceSwitcherEscapeDismissObservation:
        self._session.press_key("Escape")
        try:
            payload = self._wait_for_switcher_surface_hidden(timeout_ms=timeout_ms)
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Closing the visible Workspace switcher surface with Escape did not "
                "dismiss the panel.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        return WorkspaceSwitcherEscapeDismissObservation(
            body_text=str(payload.get("bodyText", "")),
            dashboard_visible=bool(payload.get("dashboardVisible")),
            trigger_visible=bool(payload.get("triggerVisible")),
        )

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
                normalize(element.getAttribute('aria-label') || element.innerText || element.textContent || '');
              const visibleText = (element) =>
                normalize(element.innerText || element.textContent || '');
              const buttons = Array.from(
                document.querySelectorAll(
                  'button, flt-semantics[role="button"], [role="button"], [aria-label^="Workspace switcher:"]',
                ),
              ).filter(isVisible);
              const trigger = buttons
                .filter((element) => {
                  const label = labelFor(element);
                  const text = visibleText(element);
                  return label.includes('Workspace switcher:') || text.includes('Workspace switcher:');
                })
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
                visibleText: visibleText(trigger),
                rawTextLines,
                iconCount,
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height,
                topButtonLabels: buttons
                  .filter((element) => element.getBoundingClientRect().top < 160)
                  .map((element) => labelFor(element) || visibleText(element))
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
            self._click_trigger(timeout_ms=timeout_ms)
        except WebAppTimeoutError as error:
            raise AssertionError(
                "The live app did not expose a clickable workspace switcher trigger.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def toggle_switcher_via_trigger(self, *, timeout_ms: int = 30_000) -> None:
        try:
            self._click_trigger(timeout_ms=timeout_ms)
        except WebAppTimeoutError as error:
            raise AssertionError(
                "The live app did not expose the workspace switcher trigger needed "
                "for the toggle interaction.\n"
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

    def observe_open_panel(
        self,
        *,
        expected_container_kinds: tuple[str, ...] = (),
        timeout_ms: int = 30_000,
    ) -> WorkspaceSwitcherPanelObservation:
        payload = self._session.wait_for_function(
            """
            ({ heading, expectedKinds }) => {
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
              const visibleElements = (root, selector = '*') =>
                Array.from(root.querySelectorAll(selector)).filter((candidate) => isVisible(candidate));
              const visibleText = (element) =>
                normalize(element.innerText || element.textContent || '');
              const parseAlpha = (value) => {
                if (!value) {
                  return 0;
                }
                const rgba = value.match(
                  /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([0-9.]+))?\\)/i,
                );
                if (!rgba) {
                  return 0;
                }
                if (rgba[4] === undefined) {
                  return 1;
                }
                return Number.parseFloat(rgba[4]);
              };

              const viewportWidth = window.innerWidth;
              const viewportHeight = window.innerHeight;
              const viewportArea = viewportWidth * viewportHeight;
              const isWorkspaceRow = (text) =>
                text.includes('Branch:')
                && text.includes('Delete')
                && (text.includes('Hosted') || text.includes('Local'))
                && (text.includes('Open') || text.includes('Active'));
              const isSwitcherSignal = (text, aria) =>
                text.includes(heading)
                || aria.startsWith('Workspace switcher:')
                || text.includes('Saved workspaces')
                || text.includes('Add workspace')
                || text.includes('Save and switch')
                || isWorkspaceRow(text);
              const rowCandidates = visibleElements(document)
                .map((element) => {
                  const rect = element.getBoundingClientRect();
                  return {
                    element,
                    text: visibleText(element),
                    area: rect.width * rect.height,
                    rect,
                  };
                })
                .filter((candidate) => isWorkspaceRow(candidate.text))
                .sort((left, right) => left.area - right.area);
              const surfaceCandidates = visibleElements(document)
                .map((element) => {
                  const rect = element.getBoundingClientRect();
                  return {
                    element,
                    text: visibleText(element),
                    aria: normalize(element.getAttribute('aria-label') || ''),
                    area: rect.width * rect.height,
                    rect,
                  };
                })
                .filter((candidate) =>
                  candidate.area > 0
                  && candidate.area < viewportArea * 0.9
                  && isSwitcherSignal(candidate.text, candidate.aria),
                )
                .sort((left, right) => left.area - right.area);
              if (surfaceCandidates.length === 0) {
                return null;
              }
              const switcherRect = {
                left: Math.min(...surfaceCandidates.map((candidate) => candidate.rect.left)),
                top: Math.min(...surfaceCandidates.map((candidate) => candidate.rect.top)),
                right: Math.max(...surfaceCandidates.map((candidate) => candidate.rect.right)),
                bottom: Math.max(...surfaceCandidates.map((candidate) => candidate.rect.bottom)),
              };
              switcherRect.width = switcherRect.right - switcherRect.left;
              switcherRect.height = switcherRect.bottom - switcherRect.top;
              const buttons = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              ).filter(isVisible);
              const trigger = buttons
                .filter((element) =>
                  normalize(element.getAttribute('aria-label') || element.innerText || '')
                    .startsWith('Workspace switcher:'),
                )
                .sort((left, right) => {
                  const leftRect = left.getBoundingClientRect();
                  const rightRect = right.getBoundingClientRect();
                  return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                })[0] ?? null;
              const triggerRect = trigger ? trigger.getBoundingClientRect() : null;
              const triggerBottom = triggerRect ? triggerRect.top + triggerRect.height : 0;
              const triggerRight = triggerRect ? triggerRect.left + triggerRect.width : 0;
              const anchoredByTrigger = triggerRect !== null
                && switcherRect.top >= (triggerBottom - 12)
                && switcherRect.top <= (triggerBottom + 96)
                && (
                  Math.abs(switcherRect.left - triggerRect.left) <= 56
                  || Math.abs((switcherRect.left + switcherRect.width) - triggerRight) <= 96
                  || Math.abs(
                    (switcherRect.left + (switcherRect.width / 2))
                    - (triggerRect.left + (triggerRect.width / 2)),
                  ) <= 120
                  )
                && switcherRect.width <= Math.min(760, viewportWidth * 0.8);
              const anchoredByGeometry = (
                switcherRect.top >= 40
                && switcherRect.top <= 160
                && switcherRect.width <= Math.min(760, viewportWidth * 0.8)
                && switcherRect.right >= viewportWidth * 0.6
              );
              const detectedDimmedOverlay = visibleElements(document.body)
                .some((element) => {
                  const rect = element.getBoundingClientRect();
                  if (
                    rect.width < viewportWidth * 0.75
                    || rect.height < viewportHeight * 0.75
                  ) {
                    return false;
                  }
                  const style = window.getComputedStyle(element);
                  return (
                    (style.position === 'fixed' || style.position === 'absolute')
                    && parseAlpha(style.backgroundColor) >= 0.08
                      && visibleText(element).length === 0
                    );
                  });
              const compactSheetLike = (
                switcherRect.left <= Math.max(48, viewportWidth * 0.12)
                && switcherRect.width >= viewportWidth * 0.8
                && switcherRect.height >= viewportHeight * 0.45
              );
              const fullScreenLike = compactSheetLike && switcherRect.top <= 40;
              const bottomAligned = compactSheetLike;
              const anchoredToTrigger = anchoredByTrigger || (!compactSheetLike && anchoredByGeometry);
              const centeredDialog = (
                Math.abs((switcherRect.left + (switcherRect.width / 2)) - (viewportWidth / 2))
                  <= viewportWidth * 0.12
                && switcherRect.top >= 40
                && (switcherRect.top + switcherRect.height) <= (viewportHeight - 40)
                && switcherRect.width >= viewportWidth * 0.3
                && switcherRect.width <= viewportWidth * 0.85
                && switcherRect.height >= viewportHeight * 0.25
              );
              const backgroundDimmed = detectedDimmedOverlay || compactSheetLike || centeredDialog;
              let containerKind = 'surface';
              if (fullScreenLike) {
                containerKind = 'full-screen-sheet';
              } else if (
                bottomAligned
              ) {
                containerKind = 'bottom-sheet';
              } else if (centeredDialog) {
                containerKind = 'dialog';
              } else if (anchoredToTrigger) {
                containerKind = 'anchored-panel';
              }
              if (
                Array.isArray(expectedKinds)
                && expectedKinds.length > 0
                && !expectedKinds.includes(containerKind)
              ) {
                return null;
              }
              return {
                viewportWidth,
                viewportHeight,
                titleText: heading,
                containerKind,
                containerRole: null,
                containerText: Array.from(
                  new Set(
                    surfaceCandidates
                      .map((candidate) => candidate.text || candidate.aria)
                      .filter((text) => text.length > 0),
                  ),
                ).join(' | '),
                left: switcherRect.left,
                top: switcherRect.top,
                width: switcherRect.width,
                height: switcherRect.height,
                anchoredToTrigger,
                bottomAligned,
                fullScreenLike,
                backgroundDimmed,
              };
            }
            """,
            arg={
                "heading": self._switcher_heading,
                "expectedKinds": list(expected_container_kinds),
            },
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The live app did not expose the expected open workspace switcher layout.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceSwitcherPanelObservation(
            viewport_width=float(payload.get("viewportWidth", 0.0)),
            viewport_height=float(payload.get("viewportHeight", 0.0)),
            title_text=str(payload.get("titleText", "")),
            container_kind=str(payload.get("containerKind", "surface")),
            container_role=(
                str(payload.get("containerRole"))
                if payload.get("containerRole") is not None
                else None
            ),
            container_text=str(payload.get("containerText", "")),
            bright_change_pixels=0,
            left=float(payload.get("left", 0.0)),
            top=float(payload.get("top", 0.0)),
            width=float(payload.get("width", 0.0)),
            height=float(payload.get("height", 0.0)),
            anchored_to_trigger=bool(payload.get("anchoredToTrigger")),
            bottom_aligned=bool(payload.get("bottomAligned")),
            full_screen_like=bool(payload.get("fullScreenLike")),
            background_dimmed=bool(payload.get("backgroundDimmed")),
        )

    def click_blank_area_inside_open_panel(
        self,
        *,
        timeout_ms: int = 30_000,
        stability_ms: int = 1_000,
    ) -> WorkspaceSwitcherInternalClickObservation:
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
              const visibleElements = (root, selector = '*') =>
                Array.from(root.querySelectorAll(selector)).filter((candidate) => isVisible(candidate));
              const visibleText = (element) =>
                normalize(element.innerText || element.textContent || '');
              const labelFor = (element) =>
                normalize(
                  element?.getAttribute?.('aria-label')
                  || element?.getAttribute?.('placeholder')
                  || element?.getAttribute?.('title')
                  || visibleText(element)
                  || '',
                );
              const isWorkspaceRow = (text) =>
                text.includes('Branch:')
                && text.includes('Delete')
                && (text.includes('Hosted') || text.includes('Local'))
                && (text.includes('Open') || text.includes('Active'));
              const signalsSwitcher = (text, aria) =>
                text.includes(heading)
                || aria.startsWith('Workspace switcher:')
                || text.includes('Saved workspaces')
                || text.includes('Add workspace')
                || text.includes('Save and switch')
                || isWorkspaceRow(text);
              const interactiveSelector = [
                'flt-semantics[role="button"]',
                'button',
                '[role="button"]',
                'a[href]',
                'input',
                'textarea',
                'select',
                '[tabindex]:not([tabindex="-1"])',
              ].join(',');
              let switcher = null;
              const dialogCandidates = visibleElements(
                document,
                'flt-semantics[role="dialog"],[role="dialog"]',
              )
                .map((element) => ({
                  element,
                  text: visibleText(element),
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
                    text: visibleText(element),
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
                    ),
                  )
                  .sort((left, right) => left.area - right.area);
                for (const headingCandidate of headings) {
                  let current = headingCandidate.element;
                  while (current && current !== document.body) {
                    const text = visibleText(current);
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
              const rect = switcher.getBoundingClientRect();
              const interactiveRects = visibleElements(switcher, interactiveSelector).map((element) => {
                const box = element.getBoundingClientRect();
                return {
                  left: box.left - 4,
                  top: box.top - 4,
                  right: box.right + 4,
                  bottom: box.bottom + 4,
                };
              });
              const centerX = rect.left + (rect.width / 2);
              const centerY = rect.top + (rect.height / 2);
              const insetX = Math.min(24, Math.max(12, rect.width * 0.06));
              const insetY = Math.min(24, Math.max(12, rect.height * 0.06));
              const minX = rect.left + insetX;
              const maxX = rect.right - insetX;
              const minY = rect.top + insetY;
              const maxY = rect.bottom - insetY;
              const step = 18;
              const points = [];
              for (let y = minY; y <= maxY; y += step) {
                for (let x = minX; x <= maxX; x += step) {
                  const blocked = interactiveRects.some((box) =>
                    x >= box.left
                    && x <= box.right
                    && y >= box.top
                    && y <= box.bottom,
                  );
                  if (blocked) {
                    continue;
                  }
                  const target = document.elementFromPoint(x, y);
                  if (!target || !(target instanceof Element) || !switcher.contains(target)) {
                    continue;
                  }
                  const interactiveAncestor = target.closest(interactiveSelector);
                  if (interactiveAncestor && switcher.contains(interactiveAncestor)) {
                    continue;
                  }
                  const label = labelFor(target);
                  const text = visibleText(target);
                  points.push({
                    x,
                    y,
                    targetTagName: target.tagName.toLowerCase(),
                    targetRole: target.getAttribute('role'),
                    targetLabel: label,
                    targetText: text,
                    prefersBlank: label.length === 0 && text.length === 0 ? 0 : 1,
                    distanceFromCenter: Math.hypot(x - centerX, y - centerY),
                  });
                }
              }
              if (points.length === 0) {
                return null;
              }
              points.sort((left, right) => {
                if (left.prefersBlank !== right.prefersBlank) {
                  return left.prefersBlank - right.prefersBlank;
                }
                return left.distanceFromCenter - right.distanceFromCenter;
              });
              const point = points[0];
              return {
                clickX: point.x,
                clickY: point.y,
                panelLeft: rect.left,
                panelTop: rect.top,
                panelWidth: rect.width,
                panelHeight: rect.height,
                targetTagName: point.targetTagName,
                targetRole: point.targetRole,
                targetLabel: point.targetLabel,
                targetText: point.targetText,
                clickedAtMs: window.performance.now(),
              };
            }
            """,
            arg={"heading": self._switcher_heading},
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The open workspace switcher did not expose a non-interactive internal "
                "area suitable for the inside-click probe.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        observation = WorkspaceSwitcherInternalClickObservation(
            click_x=float(payload.get("clickX", 0.0)),
            click_y=float(payload.get("clickY", 0.0)),
            panel_left=float(payload.get("panelLeft", 0.0)),
            panel_top=float(payload.get("panelTop", 0.0)),
            panel_width=float(payload.get("panelWidth", 0.0)),
            panel_height=float(payload.get("panelHeight", 0.0)),
            target_tag_name=str(payload.get("targetTagName", "")),
            target_role=(
                str(payload.get("targetRole"))
                if payload.get("targetRole") is not None
                else None
            ),
            target_label=str(payload.get("targetLabel", "")),
            target_text=str(payload.get("targetText", "")),
        )
        self._session.mouse_click(observation.click_x, observation.click_y)
        clicked_at_ms = float(payload.get("clickedAtMs", 0.0))
        try:
            self._session.wait_for_function(
                """
                ({ heading, clickedAtMs, stabilityMs }) => {
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
                  const visibleText = (element) =>
                    normalize(element.innerText || element.textContent || '');
                  const isWorkspaceRow = (text) =>
                    text.includes('Branch:')
                    && text.includes('Delete')
                    && (text.includes('Hosted') || text.includes('Local'))
                    && (text.includes('Open') || text.includes('Active'));
                  const stillVisible = Array.from(document.querySelectorAll('*'))
                    .filter((candidate) => isVisible(candidate))
                    .some((candidate) => {
                      const text = visibleText(candidate);
                      const aria = normalize(candidate.getAttribute?.('aria-label') || '');
                      return text.includes(heading)
                        || text.includes('Saved workspaces')
                        || text.includes('Add workspace')
                        || text.includes('Save and switch')
                        || aria.startsWith('Workspace switcher:')
                        || isWorkspaceRow(text);
                    });
                  return stillVisible
                    && (window.performance.now() - clickedAtMs) >= stabilityMs;
                }
                """,
                arg={
                    "heading": self._switcher_heading,
                    "clickedAtMs": clicked_at_ms,
                    "stabilityMs": stability_ms,
                },
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Clicking the non-interactive area inside the open workspace switcher "
                "dismissed the panel or made it unreadable before the observation "
                "window elapsed.\n"
                f"Clicked point: ({observation.click_x:.1f}, {observation.click_y:.1f})\n"
                f"Target tag: {observation.target_tag_name}\n"
                f"Target role: {observation.target_role}\n"
                f"Target label: {observation.target_label!r}\n"
                f"Target text: {observation.target_text!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        return observation

    def start_transition_monitor(self) -> None:
        self._session.evaluate(
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
              const visibleElements = (root, selector = '*') =>
                Array.from(root.querySelectorAll(selector)).filter((candidate) => isVisible(candidate));
              const visibleText = (element) =>
                normalize(element.innerText || element.textContent || '');
              const parseAlpha = (value) => {
                if (!value) {
                  return 0;
                }
                const rgba = value.match(
                  /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([0-9.]+))?\\)/i,
                );
                if (!rgba) {
                  return 0;
                }
                if (rgba[4] === undefined) {
                  return 1;
                }
                return Number.parseFloat(rgba[4]);
              };
              const classify = () => {
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                const viewportArea = viewportWidth * viewportHeight;
                const isWorkspaceRow = (text) =>
                  text.includes('Branch:')
                  && text.includes('Delete')
                  && (text.includes('Hosted') || text.includes('Local'))
                  && (text.includes('Open') || text.includes('Active'));
                const isPanelSignal = (text) =>
                  text.includes(heading)
                  || text.includes('Saved workspaces')
                  || text.includes('Add workspace')
                  || text.includes('Save and switch')
                  || isWorkspaceRow(text);
                const buttons = Array.from(
                  document.querySelectorAll('flt-semantics[role="button"]'),
                ).filter(isVisible);
                const trigger = buttons
                  .filter((element) =>
                    normalize(element.getAttribute('aria-label') || element.innerText || '')
                      .startsWith('Workspace switcher:'),
                  )
                  .sort((left, right) => {
                    const leftRect = left.getBoundingClientRect();
                    const rightRect = right.getBoundingClientRect();
                    return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                  })[0] ?? null;
                const rowCandidates = visibleElements(document)
                  .map((element) => {
                    const rect = element.getBoundingClientRect();
                    return {
                      text: visibleText(element),
                      area: rect.width * rect.height,
                    };
                  })
                  .filter((candidate) => isWorkspaceRow(candidate.text))
                  .sort((left, right) => left.area - right.area);
                const surfaceCandidates = visibleElements(document)
                  .map((element) => {
                    const rect = element.getBoundingClientRect();
                    return {
                      element,
                      text: visibleText(element),
                      area: rect.width * rect.height,
                      rect,
                    };
                  })
                  .filter((candidate) =>
                    candidate.element !== trigger
                    && candidate.area > 0
                    && candidate.area < viewportArea * 0.9
                    && isPanelSignal(candidate.text),
                  )
                  .sort((left, right) => left.area - right.area);
                if (surfaceCandidates.length === 0) {
                  return {
                    visible: false,
                    containerKind: null,
                    rowCount: null,
                    activeWorkspaceName: null,
                  };
                }
                const switcherRect = {
                  left: Math.min(...surfaceCandidates.map((candidate) => candidate.rect.left)),
                  top: Math.min(...surfaceCandidates.map((candidate) => candidate.rect.top)),
                  right: Math.max(...surfaceCandidates.map((candidate) => candidate.rect.right)),
                  bottom: Math.max(...surfaceCandidates.map((candidate) => candidate.rect.bottom)),
                };
                switcherRect.width = switcherRect.right - switcherRect.left;
                switcherRect.height = switcherRect.bottom - switcherRect.top;
                const triggerRect = trigger ? trigger.getBoundingClientRect() : null;
                const triggerBottom = triggerRect ? triggerRect.top + triggerRect.height : 0;
                const triggerRight = triggerRect ? triggerRect.left + triggerRect.width : 0;
                const anchoredByTrigger = triggerRect !== null
                  && switcherRect.top >= (triggerBottom - 12)
                  && switcherRect.top <= (triggerBottom + 96)
                  && (
                    Math.abs(switcherRect.left - triggerRect.left) <= 56
                    || Math.abs((switcherRect.left + switcherRect.width) - triggerRight) <= 96
                    || Math.abs(
                      (switcherRect.left + (switcherRect.width / 2))
                      - (triggerRect.left + (triggerRect.width / 2)),
                    ) <= 120
                    )
                  && switcherRect.width <= Math.min(760, viewportWidth * 0.8);
                const anchoredByGeometry = (
                  switcherRect.top >= 40
                  && switcherRect.top <= 160
                  && switcherRect.width <= Math.min(760, viewportWidth * 0.8)
                  && switcherRect.right >= viewportWidth * 0.6
                );
                const detectedDimmedOverlay = visibleElements(document.body)
                  .some((element) => {
                    const rect = element.getBoundingClientRect();
                    if (
                      rect.width < viewportWidth * 0.75
                      || rect.height < viewportHeight * 0.75
                    ) {
                      return false;
                    }
                    const style = window.getComputedStyle(element);
                    return (
                      (style.position === 'fixed' || style.position === 'absolute')
                      && parseAlpha(style.backgroundColor) >= 0.08
                        && visibleText(element).length === 0
                      );
                    });
                const compactSheetLike = (
                  switcherRect.left <= Math.max(48, viewportWidth * 0.12)
                  && switcherRect.width >= viewportWidth * 0.8
                  && switcherRect.height >= viewportHeight * 0.45
                );
                const fullScreenLike = compactSheetLike && switcherRect.top <= 40;
                const bottomAligned = compactSheetLike;
                const anchoredToTrigger = anchoredByTrigger || (!compactSheetLike && anchoredByGeometry);
                const centeredDialog = (
                  Math.abs((switcherRect.left + (switcherRect.width / 2)) - (viewportWidth / 2))
                    <= viewportWidth * 0.12
                  && switcherRect.top >= 40
                  && (switcherRect.top + switcherRect.height) <= (viewportHeight - 40)
                  && switcherRect.width >= viewportWidth * 0.3
                  && switcherRect.width <= viewportWidth * 0.85
                  && switcherRect.height >= viewportHeight * 0.25
                );
                const backgroundDimmed = detectedDimmedOverlay || compactSheetLike || centeredDialog;
                let containerKind = 'surface';
                if (fullScreenLike) {
                  containerKind = 'full-screen-sheet';
                } else if (bottomAligned) {
                  containerKind = 'bottom-sheet';
                } else if (centeredDialog) {
                  containerKind = 'dialog';
                } else if (anchoredToTrigger) {
                  containerKind = 'anchored-panel';
                }
                const activeRow = rowCandidates.find((candidate) => candidate.text.includes('Active'));
                const activeWorkspaceName = activeRow
                  ? activeRow.text
                    .split('Branch:')[0]
                    .replace('Hosted', '')
                    .replace('Local', '')
                    .replace('Active', '')
                    .trim()
                  : null;
                return {
                  visible: true,
                  containerKind,
                  rowCount: rowCandidates.length,
                  activeWorkspaceName,
                };
              };

              const existing = window.__tsWorkspaceSwitcherTransitionMonitor;
              if (existing && typeof existing.stop === 'function') {
                existing.stop();
              }
              const monitor = {
                running: true,
                samples: [],
                stop() {
                  this.running = false;
                },
              };
              const sample = () => {
                if (!monitor.running) {
                  return;
                }
                const snapshot = classify();
                monitor.samples.push({
                  timestamp: window.performance.now(),
                  visible: snapshot.visible,
                  containerKind: snapshot.containerKind,
                  rowCount: snapshot.rowCount,
                  activeWorkspaceName: snapshot.activeWorkspaceName,
                });
                if (monitor.samples.length > 600) {
                  monitor.samples.shift();
                }
                window.requestAnimationFrame(sample);
              };
              window.__tsWorkspaceSwitcherTransitionMonitor = monitor;
              sample();
              return true;
            }
            """,
            arg={"heading": self._switcher_heading},
        )

    def read_transition_monitor(
        self,
        *,
        clear: bool = False,
    ) -> WorkspaceSwitcherTransitionMonitorObservation:
        payload = self._session.evaluate(
            """
            ({ clear }) => {
              const monitor = window.__tsWorkspaceSwitcherTransitionMonitor;
              if (!monitor || !Array.isArray(monitor.samples)) {
                return {
                  sampleCount: 0,
                  visibleSampleCount: 0,
                  hiddenSampleCount: 0,
                  everHiddenAfterVisible: false,
                  observedContainerKinds: [],
                  observedRowCounts: [],
                  observedActiveWorkspaceNames: [],
                  latestVisibleContainerKind: null,
                  latestVisibleRowCount: null,
                  latestVisibleActiveWorkspaceName: null,
                };
              }
              const samples = clear ? monitor.samples.splice(0, monitor.samples.length) : [...monitor.samples];
              let sawVisible = false;
              let everHiddenAfterVisible = false;
              let latestVisibleContainerKind = null;
              let latestVisibleRowCount = null;
              let latestVisibleActiveWorkspaceName = null;
              const kinds = [];
              const rowCounts = [];
              const activeWorkspaceNames = [];
              for (const sample of samples) {
                if (sample.visible) {
                  sawVisible = true;
                  latestVisibleContainerKind = sample.containerKind ?? null;
                  latestVisibleRowCount = sample.rowCount ?? null;
                  latestVisibleActiveWorkspaceName = sample.activeWorkspaceName ?? null;
                  if (sample.containerKind && !kinds.includes(sample.containerKind)) {
                    kinds.push(sample.containerKind);
                  }
                  if (
                    sample.rowCount !== null
                    && sample.rowCount !== undefined
                    && !rowCounts.includes(sample.rowCount)
                  ) {
                    rowCounts.push(sample.rowCount);
                  }
                  if (
                    sample.activeWorkspaceName
                    && !activeWorkspaceNames.includes(sample.activeWorkspaceName)
                  ) {
                    activeWorkspaceNames.push(sample.activeWorkspaceName);
                  }
                } else if (sawVisible) {
                  everHiddenAfterVisible = true;
                }
              }
              return {
                sampleCount: samples.length,
                visibleSampleCount: samples.filter((sample) => sample.visible).length,
                hiddenSampleCount: samples.filter((sample) => !sample.visible).length,
                everHiddenAfterVisible,
                observedContainerKinds: kinds,
                observedRowCounts: rowCounts,
                observedActiveWorkspaceNames: activeWorkspaceNames,
                latestVisibleContainerKind,
                latestVisibleRowCount,
                latestVisibleActiveWorkspaceName,
              };
            }
            """,
            arg={"clear": clear},
        )
        if not isinstance(payload, dict):
            raise AssertionError("The workspace switcher transition monitor did not return data.")
        return WorkspaceSwitcherTransitionMonitorObservation(
            sample_count=int(payload.get("sampleCount", 0)),
            visible_sample_count=int(payload.get("visibleSampleCount", 0)),
            hidden_sample_count=int(payload.get("hiddenSampleCount", 0)),
            ever_hidden_after_visible=bool(payload.get("everHiddenAfterVisible")),
            observed_container_kinds=tuple(
                str(item) for item in payload.get("observedContainerKinds", [])
            ),
            observed_row_counts=tuple(
                int(item) for item in payload.get("observedRowCounts", [])
            ),
            observed_active_workspace_names=tuple(
                str(item) for item in payload.get("observedActiveWorkspaceNames", [])
            ),
            latest_visible_container_kind=(
                str(payload.get("latestVisibleContainerKind"))
                if payload.get("latestVisibleContainerKind") is not None
                else None
            ),
            latest_visible_row_count=(
                int(payload.get("latestVisibleRowCount"))
                if payload.get("latestVisibleRowCount") is not None
                else None
            ),
            latest_visible_active_workspace_name=(
                str(payload.get("latestVisibleActiveWorkspaceName"))
                if payload.get("latestVisibleActiveWorkspaceName") is not None
                else None
            ),
        )

    def stop_transition_monitor(self) -> None:
        self._session.evaluate(
            """
            () => {
              const monitor = window.__tsWorkspaceSwitcherTransitionMonitor;
              if (monitor && typeof monitor.stop === 'function') {
                monitor.stop();
              }
              return true;
            }
            """,
        )

    def close_switcher(self) -> None:
        try:
            self._session.press_key("Escape", timeout_ms=10_000)
        except WebAppTimeoutError:
            return

    def dismiss_by_clicking_outside(
        self,
        panel: WorkspaceSwitcherPanelObservation,
        *,
        timeout_ms: int = 4_000,
    ) -> WorkspaceSwitcherOutsideDismissObservation:
        click_target = self.click_neutral_content_outside_panel(panel=panel)
        return self.wait_for_dismissal_after_outside_click(
            click_target=click_target,
            timeout_ms=timeout_ms,
        )

    def click_neutral_content_outside_panel(
        self,
        *,
        panel: WorkspaceSwitcherPanelObservation,
    ) -> ElementBoundingBox:
        click_target = self._neutral_content_click_target(panel=panel)
        self._session.mouse_click(click_target.x, click_target.y)
        return click_target

    def wait_for_dismissal_after_outside_click(
        self,
        *,
        click_target: ElementBoundingBox,
        timeout_ms: int = 4_000,
    ) -> WorkspaceSwitcherOutsideDismissObservation:
        try:
            payload = self._wait_for_dismissal_payload(
                timeout_ms=timeout_ms,
                stability_window_ms=0,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 4 failed: clicking a neutral area outside the workspace switcher "
                "did not dismiss the panel.\n"
                f"Observed click target: x={click_target.x:.1f}, y={click_target.y:.1f}\n"
                f"Observed body text after the outside click:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher outside-click dismissal did not return an observation."
            )
        return WorkspaceSwitcherOutsideDismissObservation(
            click_x=click_target.x,
            click_y=click_target.y,
            body_text=str(payload.get("bodyText", "")),
            dashboard_visible=bool(payload.get("dashboardVisible")),
            trigger_visible=bool(payload.get("triggerVisible")),
        )

    def observe_blur_dismissal_after_tab(
        self,
        *,
        panel: WorkspaceSwitcherPanelObservation,
        focus_timeout_ms: int = 2_000,
        dismissal_timeout_ms: int = 6_000,
    ) -> WorkspaceSwitcherBlurDismissObservation:
        before = self._session.active_element()
        before_payload = self._probe_blur_focus_state(panel)
        if not isinstance(before_payload, dict):
            raise AssertionError(
                "The workspace switcher blur-dismissal pre-focus probe did not return "
                "an observation.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        if not bool(before_payload.get("focusOwnedBySwitcher")):
            try:
                self.focus_workspace_trigger(panel=panel, timeout_ms=focus_timeout_ms)
            except AssertionError:
                before = self._session.active_element()
                before_payload = self._probe_blur_focus_state(panel)
                if not isinstance(before_payload, dict):
                    raise AssertionError(
                        "The workspace switcher blur-dismissal pre-focus probe did not "
                        "return an observation after focusing the trigger failed.\n"
                        f"Observed body text:\n{self.current_body_text()}",
                    ) from None
                current_body_text = self.current_body_text()
                return WorkspaceSwitcherBlurDismissObservation(
                    before_focus_label=before.accessible_name,
                    before_focus_role=before.role,
                    before_focus_tag_name=before.tag_name,
                    before_focus_outer_html=before.outer_html,
                    before_focus_visible=bool(before_payload.get("activeVisible")),
                    before_focus_in_viewport=bool(
                        before_payload.get("activeInViewport"),
                    ),
                    before_focus_within_switcher=bool(
                        before_payload.get("activeWithinSwitcher"),
                    ),
                    before_focus_on_trigger=bool(before_payload.get("activeOnTrigger")),
                    before_focus_owned_by_switcher=bool(
                        before_payload.get("focusOwnedBySwitcher"),
                    ),
                    after_focus_label=before.accessible_name,
                    after_focus_role=before.role,
                    after_focus_tag_name=before.tag_name,
                    after_focus_outer_html=before.outer_html,
                    after_focus_visible=bool(before_payload.get("activeVisible")),
                    after_focus_in_viewport=bool(
                        before_payload.get("activeInViewport"),
                    ),
                    after_focus_different_from_before=False,
                    after_focus_within_switcher=bool(
                        before_payload.get("activeWithinSwitcher"),
                    ),
                    external_focus_reached=False,
                    panel_visible_after_wait="Workspace switcher" in current_body_text,
                    panel_text_after_wait=current_body_text,
                    dashboard_visible_after_wait="Dashboard" in current_body_text,
                    trigger_visible_after_wait=(
                        self._trigger_label_prefix in current_body_text
                    ),
                    waited_ms=0,
                )
            before = self._session.active_element()
            before_payload = self._probe_blur_focus_state(panel)
            if not isinstance(before_payload, dict):
                raise AssertionError(
                    "The workspace switcher blur-dismissal pre-focus probe did not return "
                    "an observation after focusing the trigger.\n"
                    f"Observed body text:\n{self.current_body_text()}",
                )
        self._session.press_key("Tab", timeout_ms=focus_timeout_ms)
        try:
            self._session.wait_for_function(
                """
                ({
                  heading,
                  triggerLabelPrefix,
                  panelLeft,
                  panelTop,
                  panelRight,
                  panelBottom,
                  beforeFocusLabel,
                  beforeFocusRole,
                  beforeFocusTagName,
                  beforeFocusOuterHtml,
                }) => {
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
                  const isInViewport = (element) => {
                    if (!element) {
                      return false;
                    }
                    const rect = element.getBoundingClientRect();
                    return rect.width > 0
                      && rect.height > 0
                      && rect.right > 0
                      && rect.bottom > 0
                      && rect.left < window.innerWidth
                      && rect.top < window.innerHeight;
                  };
                  const visibleElements = (root, selector = '*') =>
                    Array.from(root.querySelectorAll(selector)).filter((candidate) => isVisible(candidate));
                  const visibleText = (element) =>
                    normalize(element?.innerText || element?.textContent || '');
                  const labelFor = (element) =>
                    normalize(
                      element?.getAttribute?.('aria-label')
                      || element?.getAttribute?.('placeholder')
                      || element?.getAttribute?.('title')
                      || element?.innerText
                      || element?.textContent
                      || '',
                    );
                  const isWorkspaceRow = (text) =>
                    text.includes('Branch:')
                    && text.includes('Delete')
                    && (text.includes('Hosted') || text.includes('Local'))
                    && (text.includes('Open') || text.includes('Active'));
                  let switcher = null;
                  const dialogCandidates = visibleElements(
                    document,
                    'flt-semantics[role="dialog"],[role="dialog"]',
                  )
                    .map((element) => ({
                      element,
                      text: visibleText(element),
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
                        text: visibleText(element),
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
                        const text = visibleText(current);
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
                  const active = document.activeElement;
                  const activeLabel = labelFor(active);
                  const activeRole = active?.getAttribute?.('role') || null;
                  const activeTagName = active?.tagName || '';
                  const activeOuterHtml = active?.outerHTML?.slice?.(0, 400) || '';
                  const activeRect = active?.getBoundingClientRect?.() || null;
                  const activeCenterX = activeRect
                    ? activeRect.left + (activeRect.width / 2)
                    : null;
                  const activeCenterY = activeRect
                    ? activeRect.top + (activeRect.height / 2)
                    : null;
                  const activeWithinSwitcher = Boolean(
                    activeRect
                    && activeCenterX !== null
                    && activeCenterY !== null
                    && activeCenterX >= panelLeft
                    && activeCenterX <= panelRight
                    && activeCenterY >= panelTop
                    && activeCenterY <= panelBottom
                  );
                  const activeIsInteractive = Boolean(
                    active && (
                      active.matches?.('input,textarea,button,a[href],[contenteditable="true"]')
                      || activeRole === 'button'
                      || active?.getAttribute?.('tabindex') === '0'
                    ),
                  );
                  const activeDifferentFromBefore = Boolean(
                    active
                    && (
                      (beforeFocusOuterHtml && activeOuterHtml && activeOuterHtml !== beforeFocusOuterHtml)
                      || activeTagName !== beforeFocusTagName
                      || activeRole !== beforeFocusRole
                      || activeLabel !== beforeFocusLabel
                    ),
                  );
                  return Boolean(
                    active
                    && isVisible(active)
                    && isInViewport(active)
                    && activeIsInteractive
                    && activeDifferentFromBefore
                    && !activeWithinSwitcher
                    && !activeLabel.startsWith(triggerLabelPrefix)
                    && activeTagName !== 'BODY'
                    && activeTagName !== 'HTML'
                    && activeTagName !== 'FLUTTER-VIEW'
                  );
                }
                """,
                arg={
                    "heading": self._switcher_heading,
                    "triggerLabelPrefix": self._trigger_label_prefix,
                    "panelLeft": panel.left,
                    "panelTop": panel.top,
                    "panelRight": panel.left + panel.width,
                    "panelBottom": panel.top + panel.height,
                    "beforeFocusLabel": before.accessible_name or "",
                    "beforeFocusRole": before.role,
                    "beforeFocusTagName": before.tag_name,
                    "beforeFocusOuterHtml": before.outer_html,
                },
                timeout_ms=focus_timeout_ms,
            )
        except WebAppTimeoutError:
            pass
        after = self._session.active_element()
        try:
            self._session.wait_for_function(
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
                  const visibleText = (element) =>
                    normalize(element.innerText || element.textContent || '');
                  const isWorkspaceRow = (text) =>
                    text.includes('Branch:')
                    && text.includes('Delete')
                    && (text.includes('Hosted') || text.includes('Local'))
                    && (text.includes('Open') || text.includes('Active'));
                  return !Array.from(document.querySelectorAll('*'))
                    .filter(isVisible)
                    .some((element) => {
                      const text = visibleText(element);
                      return text.includes(heading)
                        && (
                          text.includes('Saved workspaces')
                          || text.includes('Save and switch')
                          || text.includes('Add workspace')
                          || text.includes('Hosted Local')
                          || isWorkspaceRow(text)
                        );
                    });
                }
                """,
                arg={"heading": self._switcher_heading},
                timeout_ms=dismissal_timeout_ms,
            )
        except WebAppTimeoutError:
            pass
        payload = self._session.evaluate(
            self._blur_dismissal_probe_script(),
            arg={
                "heading": self._switcher_heading,
                "triggerLabelPrefix": self._trigger_label_prefix,
                "panelLeft": panel.left,
                "panelTop": panel.top,
                "panelRight": panel.left + panel.width,
                "panelBottom": panel.top + panel.height,
                "beforeFocusLabel": before.accessible_name or "",
                "beforeFocusRole": before.role,
                "beforeFocusTagName": before.tag_name,
                "beforeFocusOuterHtml": before.outer_html,
            },
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher blur-dismissal probe did not return an observation.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return WorkspaceSwitcherBlurDismissObservation(
            before_focus_label=before.accessible_name,
            before_focus_role=before.role,
            before_focus_tag_name=before.tag_name,
            before_focus_outer_html=before.outer_html,
            before_focus_visible=bool(before_payload.get("activeVisible")),
            before_focus_in_viewport=bool(before_payload.get("activeInViewport")),
            before_focus_within_switcher=bool(before_payload.get("activeWithinSwitcher")),
            before_focus_on_trigger=bool(before_payload.get("activeOnTrigger")),
            before_focus_owned_by_switcher=bool(
                before_payload.get("focusOwnedBySwitcher"),
            ),
            after_focus_label=(
                str(payload.get("activeLabel"))
                if payload.get("activeLabel") is not None
                else after.accessible_name
            ),
            after_focus_role=(
                str(payload.get("activeRole"))
                if payload.get("activeRole") is not None
                else after.role
            ),
            after_focus_tag_name=str(
                payload.get("activeTagName") or after.tag_name,
            ),
            after_focus_outer_html=str(
                payload.get("activeOuterHtml") or after.outer_html,
            ),
            after_focus_visible=bool(payload.get("activeVisible")),
            after_focus_in_viewport=bool(payload.get("activeInViewport")),
            after_focus_different_from_before=bool(
                payload.get("activeDifferentFromBefore"),
            ),
            after_focus_within_switcher=bool(payload.get("activeWithinSwitcher")),
            external_focus_reached=bool(payload.get("externalFocusReached")),
            panel_visible_after_wait=bool(payload.get("panelVisible")),
            panel_text_after_wait=str(payload.get("panelText", "")),
            dashboard_visible_after_wait=bool(payload.get("dashboardVisible")),
            trigger_visible_after_wait=bool(payload.get("triggerVisible")),
            waited_ms=dismissal_timeout_ms,
        )

    def wait_for_dismissal_after_trigger_click(
        self,
        *,
        timeout_ms: int = 4_000,
        stability_window_ms: int = 400,
    ) -> WorkspaceSwitcherTriggerDismissObservation:
        try:
            payload = self._wait_for_dismissal_payload(
                timeout_ms=timeout_ms,
                stability_window_ms=stability_window_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 4 failed: clicking the workspace switcher trigger a second time "
                "did not dismiss the panel.\n"
                f"Observed body text after the second trigger click:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher trigger-toggle dismissal did not return an observation."
            )
        return WorkspaceSwitcherTriggerDismissObservation(
            body_text=str(payload.get("bodyText", "")),
            dashboard_visible=bool(payload.get("dashboardVisible")),
            trigger_visible=bool(payload.get("triggerVisible")),
            trigger_label=(
                str(payload.get("triggerLabel"))
                if payload.get("triggerLabel") is not None
                else None
            ),
        )

    def wait_for_escape_dismissal(
        self,
        *,
        timeout_ms: int = 4_000,
    ) -> WorkspaceSwitcherEscapeDismissObservation:
        return self.close(timeout_ms=timeout_ms)

    def observe_internal_focus_after_tab(
        self,
        *,
        panel: WorkspaceSwitcherPanelObservation,
        timeout_ms: int = 4_000,
    ) -> WorkspaceSwitcherInternalFocusObservation:
        before = self._session.active_element()
        before_payload = self._probe_blur_focus_state(panel)
        if not isinstance(before_payload, dict):
            raise AssertionError(
                "The workspace switcher internal-focus pre-Tab probe did not return an observation.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        self._session.press_key("Tab", timeout_ms=timeout_ms)

        probe_script = """
            ({
              triggerLabelPrefix,
              panelLeft,
              panelTop,
              panelRight,
              panelBottom,
              beforeFocusLabel,
              beforeFocusRole,
              beforeFocusTagName,
              beforeFocusOuterHtml,
            }) => {
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
              const isInViewport = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                return rect.width > 0
                  && rect.height > 0
                  && rect.right > 0
                  && rect.bottom > 0
                  && rect.left < window.innerWidth
                  && rect.top < window.innerHeight;
              };
              const labelFor = (element) =>
                normalize(
                  element?.getAttribute?.('aria-label')
                  || element?.getAttribute?.('placeholder')
                  || element?.getAttribute?.('title')
                  || element?.innerText
                  || element?.textContent
                  || '',
                );
              const buttons = Array.from(
                document.querySelectorAll('flt-semantics[role="button"],[role="button"]'),
              ).filter(isVisible);
              const trigger = buttons.find((element) =>
                labelFor(element).startsWith(triggerLabelPrefix),
              ) || null;
              const active = document.activeElement;
              const activeLabel = labelFor(active);
              const activeRole = active?.getAttribute?.('role') || null;
              const activeTagName = active?.tagName || '';
              const activeOuterHtml = active?.outerHTML?.slice?.(0, 400) || '';
              const activeRect = active?.getBoundingClientRect?.() || null;
              const activeCenterX = activeRect
                ? activeRect.left + (activeRect.width / 2)
                : null;
              const activeCenterY = activeRect
                ? activeRect.top + (activeRect.height / 2)
                : null;
              const activeWithinSwitcher = Boolean(
                activeRect
                && activeCenterX !== null
                && activeCenterY !== null
                && activeCenterX >= panelLeft
                && activeCenterX <= panelRight
                && activeCenterY >= panelTop
                && activeCenterY <= panelBottom
              );
              const activeOnTrigger = Boolean(
                active
                && trigger
                && (active === trigger || trigger.contains(active))
              );
              const activeVisible = isVisible(active);
              const activeInViewport = isInViewport(active);
              const activeDifferentFromBefore = Boolean(
                active
                && (
                  (beforeFocusOuterHtml && activeOuterHtml && activeOuterHtml !== beforeFocusOuterHtml)
                  || activeTagName !== beforeFocusTagName
                  || activeRole !== beforeFocusRole
                  || activeLabel !== beforeFocusLabel
                )
              );
              const payload = {
                activeLabel,
                activeRole,
                activeTagName,
                activeOuterHtml,
                activeVisible,
                activeInViewport,
                activeWithinSwitcher,
                activeOnTrigger,
                activeOwnedBySwitcher: Boolean(
                  active
                  && activeVisible
                  && activeInViewport
                  && (activeWithinSwitcher || activeOnTrigger)
                ),
                activeDifferentFromBefore,
              };
              return payload;
            }
        """
        wait_script = f"""
            (args) => {{
              const payload = ({probe_script})(args);
              if (!payload) {{
                return null;
              }}
              if (
                payload.activeVisible
                && payload.activeInViewport
                && payload.activeWithinSwitcher
                && !payload.activeOnTrigger
                && payload.activeDifferentFromBefore
              ) {{
                return payload;
              }}
              return null;
            }}
        """
        probe_args = {
            "triggerLabelPrefix": self._trigger_label_prefix,
            "panelLeft": panel.left,
            "panelTop": panel.top,
            "panelRight": panel.left + panel.width,
            "panelBottom": panel.top + panel.height,
            "beforeFocusLabel": before.accessible_name or "",
            "beforeFocusRole": before.role,
            "beforeFocusTagName": before.tag_name,
            "beforeFocusOuterHtml": before.outer_html,
        }
        payload: object
        try:
            payload = self._session.wait_for_function(
                wait_script,
                arg=probe_args,
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError:
            payload = self._session.evaluate(probe_script, arg=probe_args)
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher internal-focus probe did not return an observation.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        after = self._session.active_element()
        return WorkspaceSwitcherInternalFocusObservation(
            before_label=before.accessible_name,
            before_role=before.role,
            before_tag_name=before.tag_name,
            before_outer_html=before.outer_html,
            before_visible=bool(before_payload.get("activeVisible")),
            before_in_viewport=bool(before_payload.get("activeInViewport")),
            before_within_switcher=bool(before_payload.get("activeWithinSwitcher")),
            before_on_trigger=bool(before_payload.get("activeOnTrigger")),
            before_owned_by_switcher=bool(before_payload.get("focusOwnedBySwitcher")),
            after_label=after.accessible_name,
            after_role=after.role,
            after_tag_name=after.tag_name,
            after_outer_html=after.outer_html,
            after_visible=bool(payload.get("activeVisible")),
            after_in_viewport=bool(payload.get("activeInViewport")),
            after_within_switcher=bool(payload.get("activeWithinSwitcher")),
            after_on_trigger=bool(payload.get("activeOnTrigger")),
            after_owned_by_switcher=bool(payload.get("activeOwnedBySwitcher")),
            after_different_from_before=bool(payload.get("activeDifferentFromBefore")),
        )

    def observe_mobile_trigger_focus(
        self,
        *,
        tab_count: int = 24,
        timeout_ms: int = 10_000,
    ) -> MobileTriggerFocusObservation:
        observation = self.observe_trigger_keyboard_focus(
            tab_count=tab_count,
            timeout_ms=timeout_ms,
        )
        return MobileTriggerFocusObservation(
            trigger_label=observation.trigger_label,
            trigger_text=observation.trigger_text,
            trigger_x=observation.trigger_x,
            trigger_y=observation.trigger_y,
            trigger_width=observation.trigger_width,
            trigger_height=observation.trigger_height,
            before_outline=observation.before_outline,
            before_outline_color=observation.before_outline_color,
            before_outline_width=observation.before_outline_width,
            before_box_shadow=observation.before_box_shadow,
            after_outline=observation.after_outline,
            after_outline_color=observation.after_outline_color,
            after_outline_width=observation.after_outline_width,
            after_box_shadow=observation.after_box_shadow,
            active_label_after_focus=observation.active_label_after_focus,
            active_role_after_focus=observation.active_role_after_focus,
            active_tag_name_after_focus=observation.active_tag_name_after_focus,
            active_outer_html_after_focus=observation.active_outer_html_after_focus,
            focus_sequence=observation.focus_sequence,
        )

    def observe_trigger_keyboard_focus(
        self,
        *,
        tab_count: int = 24,
        timeout_ms: int = 10_000,
    ) -> WorkspaceTriggerKeyboardFocusObservation:
        before = self._trigger_snapshot(timeout_ms=timeout_ms)
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
        after = self._trigger_snapshot(timeout_ms=timeout_ms)
        active = self._session.active_element()
        return WorkspaceTriggerKeyboardFocusObservation(
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

    def observe_desktop_trigger_focus_state(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> WorkspaceTriggerFocusStateObservation:
        snapshot = self._desktop_trigger_snapshot(timeout_ms=timeout_ms)
        return WorkspaceTriggerFocusStateObservation(
            trigger_label=str(snapshot.get("triggerLabel", "")),
            trigger_text=str(snapshot.get("triggerText", "")),
            outline=str(snapshot.get("outline", "")),
            outline_color=str(snapshot.get("outlineColor", "")),
            outline_width=str(snapshot.get("outlineWidth", "")),
            box_shadow=str(snapshot.get("boxShadow", "")),
            focus_visible=bool(snapshot.get("focusVisible")),
            is_focused=bool(snapshot.get("isFocused")),
        )

    def observe_forward_focus_from_trigger(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> WorkspaceTriggerForwardFocusObservation:
        starting_focus = self._session.active_element()
        if not self._is_workspace_trigger_label(starting_focus.accessible_name) and not self._is_workspace_trigger_label(
            starting_focus.text,
        ):
            raise AssertionError(
                "Forward keyboard navigation must start with the workspace switcher "
                "trigger focused.\n"
                f"Observed active element: label={starting_focus.accessible_name!r}, "
                f"role={starting_focus.role!r}, tag={starting_focus.tag_name!r}, "
                f"text={starting_focus.text!r}",
            )

        trigger_snapshot = self._desktop_trigger_snapshot(timeout_ms=timeout_ms)
        try:
            self._session.press_key("Tab", timeout_ms=timeout_ms)
            next_focus = self._session.active_element()
            next_focus_visibility = self._active_element_visibility_snapshot()
        except WebAppTimeoutError as error:
            active = self._session.active_element()
            raise AssertionError(
                "Pressing Tab from the focused workspace switcher trigger did not move "
                "keyboard focus to a visible subsequent interactive element.\n"
                f"Observed active element after Tab: label={active.accessible_name!r}, "
                f"role={active.role!r}, tag={active.tag_name!r}, text={active.text!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

        return WorkspaceTriggerForwardFocusObservation(
            trigger_label=str(trigger_snapshot.get("triggerLabel", "")),
            trigger_text=str(trigger_snapshot.get("triggerText", "")),
            starting_focus_label=starting_focus.accessible_name,
            starting_focus_role=starting_focus.role,
            starting_focus_tag_name=starting_focus.tag_name,
            next_focus_label=next_focus.accessible_name,
            next_focus_role=next_focus.role,
            next_focus_tag_name=next_focus.tag_name,
            next_focus_outer_html=next_focus.outer_html,
            next_focus_visible=bool(next_focus_visibility.get("visible")),
            next_focus_in_viewport=bool(next_focus_visibility.get("inViewport")),
        )

    def observe_reverse_focus_return_to_trigger(
        self,
        *,
        timeout_ms: int = 10_000,
    ) -> WorkspaceTriggerReverseFocusObservation:
        starting_focus = self._session.active_element()
        if self._is_workspace_trigger_label(starting_focus.accessible_name) or self._is_workspace_trigger_label(
            starting_focus.text,
        ):
            raise AssertionError(
                "Reverse keyboard navigation must start from the control after the "
                "workspace switcher trigger, not from the trigger itself.\n"
                f"Observed active element: label={starting_focus.accessible_name!r}, "
                f"role={starting_focus.role!r}, tag={starting_focus.tag_name!r}, "
                f"text={starting_focus.text!r}",
            )

        before_reverse = self._desktop_trigger_snapshot(timeout_ms=timeout_ms)

        try:
            self._session.press_key("Shift+Tab", timeout_ms=timeout_ms)
            self._session.wait_for_function(
                """
                ({ triggerLabelPrefix }) => {
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
                    normalize(element?.getAttribute?.('aria-label') || element?.innerText || element?.textContent || '');
                  const trigger = Array.from(
                    document.querySelectorAll('flt-semantics[role="button"],[role="button"]'),
                  )
                    .filter(isVisible)
                    .find((element) => labelFor(element).startsWith(triggerLabelPrefix));
                  const active = document.activeElement;
                  if (!trigger || !active || !isVisible(trigger)) {
                    return null;
                  }
                  return active === trigger || trigger.contains(active) ? true : null;
                }
                """,
                arg={"triggerLabelPrefix": self._trigger_label_prefix},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            active = self._session.active_element()
            raise AssertionError(
                "Pressing Shift+Tab from the subsequent focused element did not return "
                "keyboard focus to the workspace switcher trigger.\n"
                f"Observed active element after Shift+Tab: label={active.accessible_name!r}, "
                f"role={active.role!r}, tag={active.tag_name!r}, text={active.text!r}\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

        after_reverse = self._desktop_trigger_snapshot(timeout_ms=timeout_ms)
        restored_focus = self._session.active_element()
        return WorkspaceTriggerReverseFocusObservation(
            trigger_label=str(before_reverse.get("triggerLabel", "")),
            trigger_text=str(before_reverse.get("triggerText", "")),
            starting_focus_label=starting_focus.accessible_name,
            starting_focus_role=starting_focus.role,
            starting_focus_tag_name=starting_focus.tag_name,
            starting_focus_outer_html=starting_focus.outer_html,
            before_reverse_outline=str(before_reverse.get("outline", "")),
            before_reverse_outline_color=str(before_reverse.get("outlineColor", "")),
            before_reverse_outline_width=str(before_reverse.get("outlineWidth", "")),
            before_reverse_box_shadow=str(before_reverse.get("boxShadow", "")),
            before_reverse_focus_visible=bool(before_reverse.get("focusVisible")),
            before_reverse_trigger_focused=bool(before_reverse.get("isFocused")),
            after_reverse_outline=str(after_reverse.get("outline", "")),
            after_reverse_outline_color=str(after_reverse.get("outlineColor", "")),
            after_reverse_outline_width=str(after_reverse.get("outlineWidth", "")),
            after_reverse_box_shadow=str(after_reverse.get("boxShadow", "")),
            after_reverse_focus_visible=bool(after_reverse.get("focusVisible")),
            after_reverse_trigger_focused=bool(after_reverse.get("isFocused")),
            restored_focus_label=restored_focus.accessible_name,
            restored_focus_role=restored_focus.role,
            restored_focus_tag_name=restored_focus.tag_name,
            restored_focus_outer_html=restored_focus.outer_html,
        )

    def screenshot(self, path: str, *, full_page: bool = True) -> None:
        self._tracker_page.screenshot(path, full_page=full_page)

    def body_text(self) -> str:
        return self.current_body_text()

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def _wait_for_switcher_surface_hidden(
        self,
        *,
        timeout_ms: int,
    ) -> dict[str, object]:
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
              const visibleText = (element) =>
                normalize(element.innerText || element.textContent || '');
              const isWorkspaceRow = (text) =>
                text.includes('Branch:')
                && text.includes('Delete')
                && (text.includes('Hosted') || text.includes('Local'))
                && (text.includes('Open') || text.includes('Active'));
              const surfaceStillVisible = Array.from(document.querySelectorAll('*'))
                .filter(isVisible)
                .some((element) => {
                  const text = visibleText(element);
                  return text.includes(heading)
                    && (
                      text.includes('Saved workspaces')
                      || text.includes('Save and switch')
                      || text.includes('Add workspace')
                      || text.includes('Hosted Local')
                      || isWorkspaceRow(text)
                    );
                });
              if (surfaceStillVisible) {
                return null;
              }
              const bodyText = document.body?.innerText ?? '';
              const triggerVisible = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter(isVisible)
                .some((element) =>
                  normalize(element.getAttribute('aria-label') || element.innerText || '')
                    .startsWith('Workspace switcher:'),
                );
              const dashboardVisible = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter(isVisible)
                .some((element) => normalize(element.innerText || '') === 'Dashboard');
              return {
                bodyText,
                triggerVisible,
                dashboardVisible,
              };
            }
            """,
            arg={"heading": self._switcher_heading},
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher dismissal probe did not return an observation."
            )
        return payload

    def _trigger_snapshot(
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
                document.querySelectorAll('button,[role="button"],flt-semantics[role="button"],[aria-label]'),
              )
                .filter((candidate) =>
                  isVisible(candidate)
                  && normalize(candidate.getAttribute('aria-label') || candidate.innerText || candidate.textContent)
                    .startsWith('Workspace switcher:')
                )
                .sort((left, right) => {
                  const leftRect = left.getBoundingClientRect();
                  const rightRect = right.getBoundingClientRect();
                  return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                })[0] ?? null;
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
                "The live app did not expose the workspace switcher trigger.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return payload

    def _desktop_trigger_snapshot(
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
                document.querySelectorAll('button,[role="button"],flt-semantics[role="button"],[aria-label]'),
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
              const active = document.activeElement;
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
                focusVisible: Boolean(
                  typeof trigger.matches === 'function' && trigger.matches(':focus-visible'),
                ),
                isFocused: Boolean(active && (active === trigger || trigger.contains(active))),
              };
            }
            """,
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The desktop layout did not expose the workspace switcher trigger for "
                "focus-style inspection.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return payload

    def _active_element_visibility_snapshot(self) -> dict[str, object]:
        payload = self._session.evaluate(
            """
            () => {
              const active = document.activeElement;
              if (!active) {
                return null;
              }
              const rect = active.getBoundingClientRect();
              const style = window.getComputedStyle(active);
              return {
                visible: rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none',
                inViewport: rect.width > 0
                  && rect.height > 0
                  && rect.right > 0
                  && rect.bottom > 0
                  && rect.left < window.innerWidth
                  && rect.top < window.innerHeight,
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The active-element visibility probe did not return an observation.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return payload

    def _collect_tab_sequence(
        self,
        *,
        tab_count: int,
        timeout_ms: int,
        stop_when_workspace_trigger_reached: bool = False,
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
            if (
                stop_when_workspace_trigger_reached
                and self._is_workspace_trigger_label(after.accessible_name)
            ):
                break
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
                  const visibleDialogs = Array.from(
                    document.querySelectorAll('flt-semantics[role="dialog"],[role="dialog"]'),
                  ).filter(isVisible);
                  if (
                    visibleDialogs.some((dialog) =>
                      normalize(dialog.innerText || dialog.textContent).includes('Workspace switcher'),
                    )
                  ) {
                    return true;
                  }
                  const headings = Array.from(document.querySelectorAll('*'))
                    .filter(isVisible)
                    .map((element) => normalize(
                      element.getAttribute?.('aria-label')
                      || element.innerText
                      || element.textContent
                      || '',
                    ));
                  return headings.some((text) =>
                    text.includes('Workspace switcher')
                    && (
                      text.includes('Saved workspaces')
                      || text.includes('Save and switch')
                      || text.includes('Hosted Local')
                    )
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

    def _wait_for_dismissal_payload(
        self,
        *,
        timeout_ms: int,
        stability_window_ms: int = 0,
    ) -> dict[str, object]:
        payload = self._session.wait_for_function(
            """
            ({ heading, stabilityWindowMs }) => {
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
              const visibleText = (element) =>
                normalize(element.innerText || element.textContent || '');
              const isWorkspaceRow = (text) =>
                text.includes('Branch:')
                && text.includes('Delete')
                && (text.includes('Hosted') || text.includes('Local'))
                && (text.includes('Open') || text.includes('Active'));
              const surfaceStillVisible = Array.from(document.querySelectorAll('*'))
                .filter(isVisible)
                .some((element) => {
                  const text = visibleText(element);
                  return text.includes(heading)
                    && (
                      text.includes('Saved workspaces')
                      || text.includes('Save and switch')
                      || text.includes('Add workspace')
                      || text.includes('Hosted Local')
                        || isWorkspaceRow(text)
                     );
                 });
              window.__tsWorkspaceSwitcherDismissalState ??= {
                hiddenSinceMs: null,
              };
              const dismissalState = window.__tsWorkspaceSwitcherDismissalState;
              if (surfaceStillVisible) {
                dismissalState.hiddenSinceMs = null;
                return null;
              }
              const now = window.performance.now();
              if (typeof dismissalState.hiddenSinceMs !== 'number') {
                dismissalState.hiddenSinceMs = now;
                return null;
              }
              const hiddenForMs = now - dismissalState.hiddenSinceMs;
              if (hiddenForMs < stabilityWindowMs) {
                return null;
              }
              const bodyText = document.body?.innerText ?? '';
              const trigger = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter(isVisible)
                .find((element) =>
                  normalize(element.getAttribute('aria-label') || element.innerText || '')
                    .startsWith('Workspace switcher:'),
                );
              const dashboardVisible = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter(isVisible)
                .some((element) => normalize(element.innerText || '') === 'Dashboard');
              return {
                bodyText,
                triggerVisible: !!trigger,
                triggerLabel: trigger
                  ? normalize(trigger.getAttribute('aria-label') || trigger.innerText || '')
                  : null,
                dashboardVisible,
                hiddenForMs,
                stabilityWindowMs,
              };
            }
            """,
            arg={
                "heading": self._switcher_heading,
                "stabilityWindowMs": stability_window_ms,
            },
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The workspace switcher dismissal did not return a readable observation."
            )
        return payload

    @staticmethod
    def _is_workspace_trigger_label(label: str | None) -> bool:
        return (label or "").startswith("Workspace switcher:")

    def _accessible_saved_workspace_rows(
        self,
        *,
        timeout_ms: int,
    ) -> tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...]:
        return tuple(
            WorkspaceSwitcherSavedWorkspaceRowObservation(
                display_name=row["display_name"],
                target_type_label=row["target_type_label"],
                state_label=row["state_label"],
                detail_text=row["detail_text"],
                selected=row["selected"],
                action_labels=row["action_labels"],
                left=row["left"],
                top=row["top"],
                width=row["width"],
                height=row["height"],
            )
            for row in self._accessible_saved_workspace_row_payloads(
                timeout_ms=timeout_ms,
            )
        )

    def _accessible_saved_workspace_row_payloads(
        self,
        *,
        timeout_ms: int,
    ) -> tuple[dict[str, object], ...]:
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
              const labelFor = (element) =>
                normalize(
                  element?.getAttribute?.('aria-label')
                  || element?.innerText
                  || element?.textContent
                  || '',
                );
              const unique = (values) => {
                const seen = new Set();
                const result = [];
                for (const value of values) {
                  const normalized = normalize(value);
                  if (!normalized || seen.has(normalized)) {
                    continue;
                  }
                  seen.add(normalized);
                  result.push(normalized);
                }
                return result;
              };
              const switcher = Array.from(document.querySelectorAll('*'))
                .filter(isVisible)
                .map((element) => ({
                  element,
                  label: labelFor(element),
                  area: element.getBoundingClientRect().width * element.getBoundingClientRect().height,
                }))
                .filter((candidate) =>
                  candidate.label.includes(heading)
                  && candidate.label.includes('Saved workspaces'),
                )
                .sort((left, right) => left.area - right.area)[0]
                ?.element;
              if (!switcher) {
                return [];
              }
              const rowPattern = /^(.*?),\\s*(Hosted|Local),\\s*([^,]+),\\s*(.+Branch:\\s*.+)$/;
              const actionPattern = /^(Active|Open:|Retry:|Re-authenticate:|Reauthenticate:|Delete:)/;
              const visibleElements = Array.from(switcher.querySelectorAll('*')).filter(isVisible);
              const rowButtons = visibleElements
                .filter((element) =>
                  element.matches?.('flt-semantics[role="button"],button,[role="button"]'),
                )
                .map((element) => ({
                  element,
                  label: labelFor(element),
                  rect: element.getBoundingClientRect(),
                }))
                .filter((candidate) => rowPattern.test(candidate.label))
                .sort((left, right) => left.rect.top - right.rect.top);
              return rowButtons.map((candidate, index) => {
                const match = candidate.label.match(rowPattern);
                const nextTop = index + 1 < rowButtons.length
                  ? rowButtons[index + 1].rect.top - 4
                  : switcher.getBoundingClientRect().bottom + 4;
                const scopedElements = visibleElements.filter((element) => {
                  const rect = element.getBoundingClientRect();
                  return rect.top >= candidate.rect.top - 4
                    && rect.top <= nextTop
                    && rect.left >= candidate.rect.left - 32
                    && rect.right <= candidate.rect.right + 96;
                });
                const actionLabels = unique(
                  scopedElements
                    .map((element) => labelFor(element))
                    .filter((label) => actionPattern.test(label)),
                );
                const rects = scopedElements.map((element) => element.getBoundingClientRect());
                const left = Math.min(...rects.map((rect) => rect.left));
                const top = Math.min(...rects.map((rect) => rect.top));
                const right = Math.max(...rects.map((rect) => rect.right));
                const bottom = Math.max(...rects.map((rect) => rect.bottom));
                return {
                  displayName: match?.[1]?.trim() || '',
                  targetTypeLabel: match?.[2]?.trim() || '',
                  stateLabel: match?.[3]?.trim() || '',
                  detailText: match?.[4]?.trim() || '',
                  visibleText: unique([candidate.label, ...actionLabels]).join(' '),
                  selected: actionLabels.includes('Active'),
                  semanticsLabel: candidate.label,
                  actionLabels,
                  buttonLabels: actionLabels,
                  left,
                  top,
                  width: Math.max(0, right - left),
                  height: Math.max(0, bottom - top),
                };
              });
            }
            """,
            arg={"heading": self._switcher_heading},
            timeout_ms=timeout_ms,
        )
        if not isinstance(payload, list):
            return ()
        rows: list[dict[str, object]] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            rows.append(
                {
                    "display_name": str(row.get("displayName", "")),
                    "target_type_label": str(row.get("targetTypeLabel", "")),
                    "state_label": str(row.get("StateLabel", row.get("stateLabel", ""))),
                    "detail_text": str(row.get("detailText", "")),
                    "visible_text": str(row.get("visibleText", "")),
                    "selected": bool(row.get("selected")),
                    "semantics_label": (
                        None
                        if row.get("semanticsLabel") is None
                        else str(row.get("semanticsLabel"))
                    ),
                    "action_labels": tuple(
                        str(label) for label in row.get("actionLabels", [])
                    ),
                    "button_labels": tuple(
                        str(label) for label in row.get("buttonLabels", [])
                    ),
                    "left": float(row.get("left", 0.0)),
                    "top": float(row.get("top", 0.0)),
                    "width": float(row.get("width", 0.0)),
                    "height": float(row.get("height", 0.0)),
                },
            )
        return tuple(rows)

    def _click_trigger(self, *, timeout_ms: int) -> None:
        try:
            self._session.click(
                self._workspace_trigger_selector,
                timeout_ms=timeout_ms,
            )
            return
        except WebAppTimeoutError:
            pass
        try:
            self._session.click(
                self._button_selector,
                has_text=self._trigger_label_prefix,
                timeout_ms=timeout_ms,
            )
            return
        except WebAppTimeoutError as original_error:
            try:
                clicked = self._session.wait_for_function(
                    """
                    ({ triggerLabelPrefix }) => {
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
                        normalize(
                          element?.getAttribute?.('aria-label')
                          || element?.innerText
                          || element?.textContent
                          || '',
                        );
                      const trigger = Array.from(
                        document.querySelectorAll(
                          'button, flt-semantics[role="button"], [role="button"], [aria-label^="Workspace switcher:"]',
                        ),
                      )
                        .filter((candidate) => isVisible(candidate) && labelFor(candidate).startsWith(triggerLabelPrefix))
                        .sort((left, right) => {
                          const leftRect = left.getBoundingClientRect();
                          const rightRect = right.getBoundingClientRect();
                          return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                        })[0] ?? null;
                      if (!trigger) {
                        return null;
                      }
                      trigger.click();
                      return labelFor(trigger);
                    }
                    """,
                    arg={"triggerLabelPrefix": self._trigger_label_prefix},
                    timeout_ms=timeout_ms,
                )
                if isinstance(clicked, str) and clicked.startswith(self._trigger_label_prefix):
                    return
            except WebAppTimeoutError:
                pass
            try:
                self._session.click(
                    'button[aria-label^="Workspace switcher:"], [role="button"][aria-label^="Workspace switcher:"]',
                    timeout_ms=timeout_ms,
                )
                return
            except WebAppTimeoutError as fallback_error:
                raise AssertionError(
                    "The live app did not expose a clickable workspace switcher trigger.\n"
                    f"Observed body text:\n{self.current_body_text()}",
                ) from fallback_error

    @staticmethod
    def _blur_dismissal_probe_script() -> str:
        return """
        ({
          heading,
          triggerLabelPrefix,
          panelLeft,
          panelTop,
          panelRight,
          panelBottom,
          beforeFocusLabel,
          beforeFocusRole,
          beforeFocusTagName,
          beforeFocusOuterHtml,
        }) => {
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
          const isInViewport = (element) => {
            if (!element) {
              return false;
            }
            const rect = element.getBoundingClientRect();
            return rect.width > 0
              && rect.height > 0
              && rect.right > 0
              && rect.bottom > 0
              && rect.left < window.innerWidth
              && rect.top < window.innerHeight;
          };
          const visibleElements = (root, selector = '*') =>
            Array.from(root.querySelectorAll(selector)).filter((candidate) => isVisible(candidate));
          const visibleText = (element) =>
            normalize(element?.innerText || element?.textContent || '');
          const active = document.activeElement;
          const labelFor = (element) =>
            normalize(
              element?.getAttribute?.('aria-label')
              || element?.getAttribute?.('placeholder')
              || element?.getAttribute?.('title')
              || element?.innerText
              || element?.textContent
              || '',
            );
          const isWorkspaceRow = (text) =>
            text.includes('Branch:')
            && text.includes('Delete')
            && (text.includes('Hosted') || text.includes('Local'))
            && (text.includes('Open') || text.includes('Active'));
          let switcher = null;
          const dialogCandidates = visibleElements(
            document,
            'flt-semantics[role="dialog"],[role="dialog"]',
          )
            .map((element) => ({
              element,
              text: visibleText(element),
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
                text: visibleText(element),
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
                const text = visibleText(current);
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
          const activeLabel = labelFor(active);
          const activeRole = active?.getAttribute?.('role') || null;
          const activeTagName = active?.tagName || '';
          const activeOuterHtml = active?.outerHTML?.slice?.(0, 400) || '';
          const activeRect = active?.getBoundingClientRect?.() || null;
          const activeCenterX = activeRect
            ? activeRect.left + (activeRect.width / 2)
            : null;
          const activeCenterY = activeRect
            ? activeRect.top + (activeRect.height / 2)
            : null;
          const activeWithinSwitcher = Boolean(
            activeRect
            && activeCenterX !== null
            && activeCenterY !== null
            && activeCenterX >= panelLeft
            && activeCenterX <= panelRight
            && activeCenterY >= panelTop
            && activeCenterY <= panelBottom
          );
          const activeIsInteractive = Boolean(
            active && (
              active.matches?.('input,textarea,button,a[href],[contenteditable="true"]')
              || activeRole === 'button'
              || active?.getAttribute?.('tabindex') === '0'
            ),
          );
          const activeVisible = isVisible(active);
          const activeInViewport = isInViewport(active);
          const activeDifferentFromBefore = Boolean(
            active
            && (
              (beforeFocusOuterHtml && activeOuterHtml && activeOuterHtml !== beforeFocusOuterHtml)
              || activeTagName !== beforeFocusTagName
              || activeRole !== beforeFocusRole
              || activeLabel !== beforeFocusLabel
            ),
          );
          const externalFocusReached = Boolean(
            active
            && activeVisible
            && activeInViewport
            && activeIsInteractive
            && activeDifferentFromBefore
            && !activeWithinSwitcher
            && !activeLabel.startsWith(triggerLabelPrefix)
            && activeTagName !== 'BODY'
            && activeTagName !== 'HTML'
            && activeTagName !== 'FLUTTER-VIEW'
          );
          const triggerVisible = Array.from(
            document.querySelectorAll('flt-semantics[role="button"]'),
          )
            .filter(isVisible)
            .some((element) =>
              normalize(element.getAttribute('aria-label') || element.innerText || '')
                .startsWith(triggerLabelPrefix),
            );
          const dashboardVisible = Array.from(
            document.querySelectorAll('flt-semantics[role="button"]'),
          )
            .filter(isVisible)
            .some((element) => normalize(element.innerText || '') === 'Dashboard');
          return {
            activeLabel,
            activeRole,
            activeTagName,
            activeOuterHtml,
            activeVisible,
            activeInViewport,
            activeDifferentFromBefore,
            activeWithinSwitcher,
            externalFocusReached,
            panelVisible: Boolean(switcher),
            panelText: switcher ? visibleText(switcher) : '',
            dashboardVisible,
            triggerVisible,
          };
        }
        """

    def _probe_blur_focus_state(
        self,
        panel: WorkspaceSwitcherPanelObservation,
    ) -> object:
        return self._session.evaluate(
            """
            ({
              heading,
              triggerLabelPrefix,
              panelLeft,
              panelTop,
              panelRight,
              panelBottom,
            }) => {
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
              const isInViewport = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                return rect.width > 0
                  && rect.height > 0
                  && rect.right > 0
                  && rect.bottom > 0
                  && rect.left < window.innerWidth
                  && rect.top < window.innerHeight;
              };
              const visibleElements = (root, selector = '*') =>
                Array.from(root.querySelectorAll(selector)).filter((candidate) => isVisible(candidate));
              const visibleText = (element) =>
                normalize(element?.innerText || element?.textContent || '');
              let switcher = null;
              const dialogCandidates = visibleElements(
                document,
                'flt-semantics[role="dialog"],[role="dialog"]',
              )
                .map((element) => ({
                  element,
                  text: visibleText(element),
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
                    text: visibleText(element),
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
                    const text = visibleText(current);
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
              const buttons = visibleElements(document, 'flt-semantics[role="button"],[role="button"]');
              const trigger = buttons.find((element) =>
                normalize(element.getAttribute?.('aria-label') || element.innerText || '')
                  .startsWith(triggerLabelPrefix),
              ) || null;
              const active = document.activeElement;
              const activeRect = active?.getBoundingClientRect?.() || null;
              const activeCenterX = activeRect
                ? activeRect.left + (activeRect.width / 2)
                : null;
              const activeCenterY = activeRect
                ? activeRect.top + (activeRect.height / 2)
                : null;
              const switcherFocusWithin = Boolean(
                switcher?.matches?.(':focus-within'),
              );
              const activeWithinSwitcher = Boolean(
                activeRect
                && activeCenterX !== null
                && activeCenterY !== null
                && (
                  switcherFocusWithin
                  || (switcher && switcher.contains(active))
                  || (
                    activeCenterX >= panelLeft
                    && activeCenterX <= panelRight
                    && activeCenterY >= panelTop
                    && activeCenterY <= panelBottom
                  )
                )
              );
              const activeOnTrigger = Boolean(
                active
                && trigger
                && (active === trigger || trigger.contains(active))
              );
              const activeVisible = isVisible(active);
              const activeInViewport = isInViewport(active);
              return {
                activeVisible,
                activeInViewport,
                switcherFocusWithin,
                activeWithinSwitcher,
                activeOnTrigger,
                focusOwnedBySwitcher: Boolean(
                  active
                  && activeVisible
                  && activeInViewport
                  && (activeWithinSwitcher || activeOnTrigger)
                ),
              };
            }
            """,
            arg={
                "heading": self._switcher_heading,
                "triggerLabelPrefix": self._trigger_label_prefix,
                "panelLeft": panel.left,
                "panelTop": panel.top,
                "panelRight": panel.left + panel.width,
                "panelBottom": panel.top + panel.height,
            },
        )
    def _neutral_content_click_target(
        self,
        *,
        panel: WorkspaceSwitcherPanelObservation,
    ) -> ElementBoundingBox:
        payload = self._session.evaluate(
            """
            ({ left, top, width, height }) => {
              const viewportWidth = window.innerWidth;
              const viewportHeight = window.innerHeight;
              const panelRight = left + width;
              const panelBottom = top + height;
              const minimumHeaderBottom = 170;
              const candidates = [
                {
                  x: 96,
                  y: Math.min(viewportHeight - 64, Math.max(panelBottom + 40, minimumHeaderBottom + 40)),
                },
                {
                  x: Math.max(48, Math.min((left / 2), viewportWidth - 48)),
                  y: Math.max(minimumHeaderBottom + 24, Math.min(top + (height / 2), viewportHeight - 48)),
                },
                {
                  x: Math.min(viewportWidth - 48, Math.max(panelRight + 48, viewportWidth * 0.8)),
                  y: Math.max(minimumHeaderBottom + 24, Math.min(top + (height / 2), viewportHeight - 48)),
                },
                {
                  x: Math.max(64, Math.min(viewportWidth / 2, viewportWidth - 64)),
                  y: Math.min(viewportHeight - 48, Math.max(panelBottom + 48, minimumHeaderBottom + 48)),
                },
              ];
              const outsidePanel = (point) =>
                point.x < (left - 24)
                || point.x > (panelRight + 24)
                || point.y < (top - 24)
                || point.y > (panelBottom + 24);
              const outsideHeader = (point) => point.y >= minimumHeaderBottom;
              const point = candidates.find((candidate) => outsidePanel(candidate) && outsideHeader(candidate))
                ?? { x: Math.max(64, Math.min(viewportWidth / 2, viewportWidth - 64)), y: Math.max(minimumHeaderBottom + 48, Math.min(viewportHeight - 64, panelBottom + 48)) };
              return {
                x: point.x,
                y: point.y,
                width: 0,
                height: 0,
              };
            }
            """,
            arg={
                "left": panel.left,
                "top": panel.top,
                "width": panel.width,
                "height": panel.height,
            },
        )
        if not isinstance(payload, dict):
            raise AssertionError("Unable to calculate a neutral outside-click target.")
        return ElementBoundingBox(
            x=float(payload.get("x", 0.0)),
            y=float(payload.get("y", 0.0)),
            width=float(payload.get("width", 0.0)),
            height=float(payload.get("height", 0.0)),
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
    rows = _rows_from_structured_switcher_text(normalized)
    if rows:
        return rows
    return _rows_from_linear_switcher_text(normalized)


def _rows_from_structured_switcher_text(
    normalized: str,
) -> tuple[WorkspaceSwitcherRowObservation, ...]:
    states = (
        "Attachments limited",
        "Saved hosted workspace",
        "Sync issue",
        "Needs sign-in",
        "Read-only",
        "Connected",
        "Unavailable",
        "Local Git",
    )
    escaped_states = "|".join(re.escape(state) for state in states)
    detail_pattern = re.compile(
        r"(?P<detail>\S+\s+•\s+Branch:\s+\S+(?:\s+•\s+Write\s+Branch:\s+\S+)?)",
    )
    open_pattern = re.compile(
        r"^(?P<action>Open(?:\s+workspace)?|Retry|Re-authenticate|Reauthenticate):\s+"
        r"(?P<display>.+?)\s+Delete:\s+(?P<delete>.+)$",
    )
    detail_matches = list(detail_pattern.finditer(normalized))
    if not detail_matches:
        return ()
    rows: list[WorkspaceSwitcherRowObservation | None] = [None] * len(detail_matches)
    next_prefix_start = len(normalized)
    for index in range(len(detail_matches) - 1, -1, -1):
        detail_match = detail_matches[index]
        detail_text = detail_match.group("detail").strip()
        tail = normalized[detail_match.end() : next_prefix_start].strip()
        if tail.startswith("Active Delete: "):
            prefix_match = re.search(
                rf"(?P<display>[^,:•]+), "
                rf"(?P<target_type>Hosted|Local), "
                rf"(?P<state>{escaped_states}),\s*$",
                normalized[: detail_match.start()],
            )
            if prefix_match is None:
                return ()
            display_name = prefix_match.group("display").strip()
            action_label = "Active"
            selected = True
        else:
            open_match = open_pattern.match(tail)
            if open_match is None:
                return ()
            display_name = open_match.group("display").strip()
            prefix_match = re.search(
                rf"{re.escape(display_name)}, "
                rf"(?P<target_type>Hosted|Local), "
                rf"(?P<state>{escaped_states}),\s*$",
                normalized[: detail_match.start()],
            )
            if prefix_match is None:
                return ()
            action_label = _workspace_row_action_label(open_match.group("action").strip())
            selected = False
        target_type = prefix_match.group("target_type").strip()
        state_label = prefix_match.group("state").strip()
        next_prefix_start = prefix_match.start()
        delete_text = f"Delete: {display_name}"
        visible_action = (
            "Active"
            if action_label == "Active"
            else f"{action_label}: {display_name}"
        )
        button_labels = (
            ("Delete",)
            if action_label == "Active"
            else (action_label, "Delete")
        )
        rows[index] = WorkspaceSwitcherRowObservation(
            display_name=display_name,
            target_type_label=target_type,
            state_label=state_label,
            detail_text=detail_text,
            visible_text=(
                f"{display_name} {detail_text} {target_type} "
                f"{state_label} {visible_action} {delete_text}"
            ),
            selected=selected,
            semantics_label=None,
            icon_accessibility_label=None,
            action_labels=(action_label,),
            button_labels=button_labels,
        )
    return tuple(row for row in rows if row is not None)


def _rows_from_linear_switcher_text(
    normalized: str,
) -> tuple[WorkspaceSwitcherRowObservation, ...]:
    states = (
        "Attachments limited",
        "Saved hosted workspace",
        "Sync issue",
        "Needs sign-in",
        "Read-only",
        "Connected",
        "Unavailable",
        "Local Git",
    )
    escaped_states = "|".join(re.escape(state) for state in states)
    detail_pattern = re.compile(
        r"(?P<detail>\S+\s+•\s+Branch:\s+\S+(?:\s+•\s+Write\s+Branch:\s+\S+)?)",
    )
    metadata_pattern = re.compile(
        rf"^(?P<target_type>Hosted|Local)\s+(?P<state>{escaped_states})\s+(?P<tail>.+)$",
    )
    open_pattern = re.compile(
        r"^(?P<action>Open(?:\s+workspace)?|Retry|Re-authenticate|Reauthenticate):\s+"
        r"(?P<display>.+?)\s+Delete:\s+(?P<delete>.+)$",
    )
    detail_matches = list(detail_pattern.finditer(normalized))
    rows: list[WorkspaceSwitcherRowObservation] = []
    for index, detail_match in enumerate(detail_matches):
        next_detail_start = (
            detail_matches[index + 1].start()
            if index + 1 < len(detail_matches)
            else len(normalized)
        )
        prefix_text = normalized[: detail_match.start()].strip()
        detail_text = detail_match.group("detail").strip()
        trailing_text = normalized[detail_match.end() : next_detail_start].strip()
        metadata_match = metadata_pattern.match(trailing_text)
        if metadata_match is None:
            continue
        target_type = metadata_match.group("target_type").strip()
        state_label = metadata_match.group("state").strip()
        tail = metadata_match.group("tail").strip()
        if tail.startswith("Active Delete: "):
            display_name = _shared_display_name(
                prefix_text=prefix_text,
                candidate_text=tail.removeprefix("Active Delete: ").strip(),
            )
            if not display_name:
                continue
            action_label = "Active"
            selected = True
        else:
            open_match = open_pattern.match(tail)
            if open_match is None:
                continue
            display_name = open_match.group("display").strip()
            delete_target = open_match.group("delete").strip()
            if not delete_target.startswith(display_name):
                display_name = _shared_display_name(
                    prefix_text=prefix_text,
                    candidate_text=delete_target,
                )
                if not display_name:
                    continue
            action_label = _workspace_row_action_label(open_match.group("action").strip())
            selected = False
        visible_action = (
            "Active"
            if selected
            else f"{action_label}: {display_name}"
        )
        delete_text = f"Delete: {display_name}"
        rows.append(
            WorkspaceSwitcherRowObservation(
                display_name=display_name,
                target_type_label=target_type,
                state_label=state_label,
                detail_text=detail_text,
                visible_text=(
                    f"{display_name} {detail_text} {target_type} "
                    f"{state_label} {visible_action} {delete_text}"
                ).strip(),
                selected=selected,
                semantics_label=None,
                icon_accessibility_label=None,
                action_labels=(action_label,),
                button_labels=(
                    ("Delete",)
                    if selected
                    else (action_label, "Delete")
                ),
            ),
        )
    return tuple(rows)


def _shared_display_name(*, prefix_text: str, candidate_text: str) -> str | None:
    prefix_tokens = prefix_text.split()
    candidate_tokens = candidate_text.split()
    for token_count in range(
        min(len(prefix_tokens), len(candidate_tokens)),
        0,
        -1,
    ):
        candidate = " ".join(candidate_tokens[:token_count]).strip()
        if candidate and prefix_text.endswith(candidate):
            return candidate
    return None


def _workspace_row_action_label(action_text: str) -> str:
    normalized = action_text.strip()
    if normalized.startswith("Open workspace"):
        return "Open workspace"
    if normalized.startswith("Open"):
        return "Open"
    if normalized.startswith("Re-authenticate"):
        return "Re-authenticate"
    if normalized.startswith("Reauthenticate"):
        return "Reauthenticate"
    if normalized.startswith("Retry"):
        return "Retry"
    return "Active"


def _is_saved_workspace_action_line(action_text: str) -> bool:
    normalized = action_text.strip()
    if normalized == "Active":
        return True
    return bool(
        re.match(
            r"^(Open(?:\s+workspace)?|Retry|Re-authenticate|Reauthenticate):\s+.+$",
            normalized,
        ),
    )
