from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from testing.components.pages.live_project_settings_page import LiveProjectSettingsPage
from testing.core.utils.color_contrast import color_distance
from testing.core.utils.png_image import RgbImage
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
    bright_change_pixels: int
    left: float
    top: float
    width: float
    height: float
    anchored_to_trigger: bool
    bottom_aligned: bool
    full_screen_like: bool
    background_dimmed: bool


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

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()


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
