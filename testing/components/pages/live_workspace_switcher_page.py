from __future__ import annotations

from dataclasses import dataclass
import re

from testing.components.pages.live_project_settings_page import LiveProjectSettingsPage
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


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
    left: float
    top: float
    width: float
    height: float
    anchored_to_trigger: bool
    bottom_aligned: bool
    full_screen_like: bool


class LiveWorkspaceSwitcherPage:
    _settings_page = LiveProjectSettingsPage

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
        timeout_ms: int = 30_000,
    ) -> WorkspaceSwitcherPanelObservation:
        try:
            payload = self._session.wait_for_function(
                """
                ({ displayName }) => {
                  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                  const dedupeRepeatedLine = (value) => {
                    const normalized = normalize(value);
                    const match = normalized.match(/^(.+)\\s+\\1$/);
                    return match ? match[1] : normalized;
                  };
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
                  const visibleElements = Array.from(document.querySelectorAll('body *')).filter(isVisible);
                  const textFor = (element) => dedupeRepeatedLine(element.innerText || '');
                  const accessibleLabel = (element) =>
                    dedupeRepeatedLine(element.getAttribute('aria-label') || '');
                  const sortByArea = (elements) =>
                    elements.sort((left, right) => {
                      const leftRect = left.getBoundingClientRect();
                      const rightRect = right.getBoundingClientRect();
                      return (leftRect.width * leftRect.height) - (rightRect.width * rightRect.height);
                    });
                  const dedupeNestedElements = (elements) => {
                    const deduped = [];
                    for (const candidate of elements) {
                      if (deduped.some((accepted) => accepted.contains(candidate))) {
                        continue;
                      }
                      deduped.push(candidate);
                    }
                    return deduped;
                  };
                  const titleElement = sortByArea(
                    visibleElements.filter((element) => {
                      const text = textFor(element);
                      return text === 'Workspace switcher';
                    }),
                  )[0] ?? null;
                  const controlLabels = new Set(['Delete', 'Hosted', 'Local', 'Save and switch']);
                  const surfaceElements = dedupeNestedElements(
                    sortByArea(
                      visibleElements.filter((element) => {
                        const text = textFor(element);
                        if (!text) {
                          return false;
                        }
                        const rect = element.getBoundingClientRect();
                        if (
                          rect.width <= 0
                          || rect.height <= 0
                          || (rect.width * rect.height) >= (window.innerWidth * window.innerHeight * 0.9)
                        ) {
                          return false;
                        }
                        return (
                          text === 'Workspace switcher'
                          || text === 'Saved workspaces'
                          || controlLabels.has(text)
                          || (displayName && text.includes(displayName))
                          || text.includes('Branch:')
                          || text.includes('Needs sign-in')
                          || text === 'Active'
                        );
                      }),
                    ),
                  );
                  if (!titleElement) {
                    return null;
                  }
                  const surfaceTextValues = Array.from(
                    new Set(
                      [titleElement, ...surfaceElements]
                        .map((element) => textFor(element))
                        .filter((text) => text.length > 0),
                    ),
                  );
                  const hasWorkspaceSummary =
                    surfaceTextValues.some((text) => displayName && text.includes(displayName))
                    && surfaceTextValues.some((text) => text.includes('Branch:') || text.includes('Needs sign-in'));
                  const hasPanelControls = surfaceTextValues.some((text) => text === 'Save and switch')
                    && surfaceTextValues.some((text) => text === 'Hosted')
                    && surfaceTextValues.some((text) => text === 'Local');
                  if (!hasWorkspaceSummary || !hasPanelControls) {
                    return null;
                  }
                  const boundsElements = [titleElement, ...surfaceElements];
                  const rects = boundsElements.map((element) => element.getBoundingClientRect());
                  const left = Math.min(...rects.map((rect) => rect.left));
                  const top = Math.min(...rects.map((rect) => rect.top));
                  const right = Math.max(...rects.map((rect) => rect.right));
                  const bottom = Math.max(...rects.map((rect) => rect.bottom));
                  let current = titleElement;
                  let containerRole = null;
                  while (current && current !== document.body) {
                    const role = normalize(current.getAttribute('role') || '').toLowerCase();
                    const ariaLabel = normalize(current.getAttribute('aria-label') || '').toLowerCase();
                    const containerText = textFor(current);
                    if (
                      containerText.includes('Workspace switcher')
                      && (
                        role === 'dialog'
                        || ariaLabel === 'dialog'
                      )
                    ) {
                      containerRole = role || ariaLabel;
                      break;
                    }
                    current = current.parentElement;
                  }
                  if (!containerRole) {
                    const floatingDialog = visibleElements.find((element) => {
                      const role = normalize(element.getAttribute('role') || '').toLowerCase();
                      const ariaLabel = normalize(element.getAttribute('aria-label') || '').toLowerCase();
                      const text = textFor(element);
                      return text.includes('Workspace switcher') && (role === 'dialog' || ariaLabel === 'dialog');
                    }) ?? null;
                    if (floatingDialog) {
                      const role = normalize(floatingDialog.getAttribute('role') || '').toLowerCase();
                      const ariaLabel = normalize(floatingDialog.getAttribute('aria-label') || '').toLowerCase();
                      containerRole = role || ariaLabel;
                    }
                  }
                  return {
                    viewportWidth: window.innerWidth,
                    viewportHeight: window.innerHeight,
                    titleText: textFor(titleElement),
                    containerRole,
                    containerText: surfaceTextValues.join(' | '),
                    left,
                    top,
                    width: right - left,
                    height: bottom - top,
                  };
                }
                """,
                arg={"displayName": trigger.display_name},
                timeout_ms=timeout_ms,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Activating the workspace switcher did not render any visible switcher "
                "surface.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error
        if not isinstance(payload, dict):
            raise AssertionError(
                "Activating the workspace switcher did not render any visible switcher panel.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        left = float(payload["left"])
        top = float(payload["top"])
        width = float(payload["width"])
        height = float(payload["height"])
        viewport_width = float(payload["viewportWidth"])
        viewport_height = float(payload["viewportHeight"])
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
            and left <= 24
            and width >= viewport_width * 0.85
            and height >= viewport_height * 0.75
        )
        if full_screen_like:
            container_kind = "full-screen-sheet"
        elif bottom_aligned and top >= viewport_height * 0.25:
            container_kind = "bottom-sheet"
        elif anchored_to_trigger:
            container_kind = "anchored-panel"
        else:
            container_kind = "dialog"
        return WorkspaceSwitcherPanelObservation(
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            title_text=str(payload["titleText"]),
            container_kind=container_kind,
            container_role=(
                str(payload["containerRole"]) if payload["containerRole"] is not None else None
            ),
            container_text=str(payload["containerText"]),
            left=left,
            top=top,
            width=width,
            height=height,
            anchored_to_trigger=anchored_to_trigger,
            bottom_aligned=bottom_aligned,
            full_screen_like=full_screen_like,
        )

    def close_switcher(self) -> None:
        try:
            self._session.press_key("Escape", timeout_ms=10_000)
        except WebAppTimeoutError:
            return

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()
