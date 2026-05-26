from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path

from testing.components.pages.live_workspace_switcher_page import (
    WorkspaceSwitcherTriggerObservation,
)
from testing.core.utils.color_contrast import color_distance, rgb_to_hex
from testing.core.utils.png_image import RgbImage


@dataclass(frozen=True)
class WorkspaceSwitcherTriggerVisualObservation:
    icon_visible: bool
    icon_pixel_count: int
    icon_box: tuple[int, int, int, int] | None
    background_hex: str
    icon_gap_pixels: int
    text_band_count: int
    text_band_boxes: tuple[tuple[int, int, int, int], ...]


class LiveWorkspaceSwitcherVisualProbe:
    _foreground_threshold = 20.0
    _minimum_icon_pixels = 40

    def observe_trigger(
        self,
        *,
        screenshot_path: Path,
        trigger: WorkspaceSwitcherTriggerObservation,
    ) -> WorkspaceSwitcherTriggerVisualObservation:
        image = RgbImage.open(screenshot_path)
        crop_box = self._crop_box(image=image, trigger=trigger)
        crop = image.crop(crop_box)
        background = Counter(crop.getdata()).most_common(1)[0][0]
        mask = self._foreground_mask(crop=crop, background=background)
        component, gap_pixels = self._leading_icon_component(mask=mask)
        text_bands = self._text_band_boxes(mask=mask, icon_box=component[1] if component else None)
        return WorkspaceSwitcherTriggerVisualObservation(
            icon_visible=component is not None,
            icon_pixel_count=component[0] if component is not None else 0,
            icon_box=component[1] if component is not None else None,
            background_hex=rgb_to_hex(background).lower(),
            icon_gap_pixels=gap_pixels,
            text_band_count=len(text_bands),
            text_band_boxes=tuple(text_bands),
        )

    @staticmethod
    def _crop_box(
        *,
        image: RgbImage,
        trigger: WorkspaceSwitcherTriggerObservation,
    ) -> tuple[int, int, int, int]:
        left = max(int(trigger.left), 0)
        top = max(int(trigger.top), 0)
        right = min(int(trigger.left + trigger.width), image.width)
        bottom = min(int(trigger.top + trigger.height), image.height)
        return (left, top, right, bottom)

    def _foreground_mask(
        self,
        *,
        crop: RgbImage,
        background: tuple[int, int, int],
    ) -> list[list[bool]]:
        width = crop.width
        height = crop.height
        return [
            [
                color_distance(crop.pixels[(y * width) + x], background)
                > self._foreground_threshold
                for x in range(width)
            ]
            for y in range(height)
        ]

    def _leading_icon_component(
        self,
        *,
        mask: list[list[bool]],
    ) -> tuple[tuple[int, tuple[int, int, int, int]] | None, int]:
        components = self._components(mask=mask)
        width = len(mask[0])
        height = len(mask)
        candidates: list[tuple[int, tuple[int, int, int, int], int]] = []
        for pixel_count, box in components:
            left, top, right, bottom = box
            component_width = right - left
            component_height = bottom - top
            aspect_ratio = component_width / component_height if component_height else 0
            gap_pixels = self._gap_after_component(mask=mask, box=box)
            center_y = top + (component_height / 2)
            if pixel_count < self._minimum_icon_pixels:
                continue
            if left > min(int(width * 0.12), 24):
                continue
            if right > min(int(width * 0.18), 36):
                continue
            if component_width < 8 or component_width > 20:
                continue
            if component_height < 8 or component_height > 20:
                continue
            if aspect_ratio < 0.6 or aspect_ratio > 1.4:
                continue
            if center_y < (height * 0.2) or center_y > (height * 0.8):
                continue
            if gap_pixels < 6:
                continue
            candidates.append((pixel_count, box, gap_pixels))
        if not candidates:
            return None, 0
        pixel_count, box, gap_pixels = max(candidates, key=lambda candidate: candidate[0])
        return (pixel_count, box), gap_pixels

    @staticmethod
    def _components(
        *,
        mask: list[list[bool]],
    ) -> list[tuple[int, tuple[int, int, int, int]]]:
        width = len(mask[0])
        height = len(mask)
        visited = [[False for _ in range(width)] for _ in range(height)]
        components: list[tuple[int, tuple[int, int, int, int]]] = []
        for y in range(height):
            for x in range(width):
                if visited[y][x] or not mask[y][x]:
                    continue
                component = LiveWorkspaceSwitcherVisualProbe._component(
                    mask=mask,
                    visited=visited,
                    start=(x, y),
                )
                pixel_count = len(component)
                xs = [point[0] for point in component]
                ys = [point[1] for point in component]
                left = min(xs)
                top = min(ys)
                right = max(xs)
                bottom = max(ys)
                components.append((pixel_count, (left, top, right + 1, bottom + 1)))
        return components

    @staticmethod
    def _gap_after_component(
        *,
        mask: list[list[bool]],
        box: tuple[int, int, int, int],
    ) -> int:
        left, top, right, bottom = box
        width = len(mask[0])
        gap = width - right
        for y in range(max(top - 1, 0), min(bottom + 1, len(mask))):
            for x in range(right, width):
                if mask[y][x]:
                    gap = min(gap, x - right)
                    break
        return gap

    @staticmethod
    def _text_band_boxes(
        *,
        mask: list[list[bool]],
        icon_box: tuple[int, int, int, int] | None,
    ) -> list[tuple[int, int, int, int]]:
        width = len(mask[0])
        height = len(mask)
        text_start = (icon_box[2] + 6) if icon_box is not None else max(8, int(width * 0.08))
        row_threshold = max(4, int((width - text_start) * 0.02))
        active_rows: list[tuple[int, int, int]] = []
        for y in range(height):
            xs = [x for x in range(text_start, width) if mask[y][x]]
            if len(xs) < row_threshold:
                continue
            active_rows.append((y, min(xs), max(xs) + 1))
        if not active_rows:
            return []
        bands: list[tuple[int, int, int, int]] = []
        minimum_band_width = max(24, int((width - text_start) * 0.12))
        band_top = active_rows[0][0]
        band_bottom = active_rows[0][0] + 1
        band_left = active_rows[0][1]
        band_right = active_rows[0][2]
        previous_y = active_rows[0][0]
        for y, left, right in active_rows[1:]:
            if y <= (previous_y + 1):
                band_bottom = y + 1
                band_left = min(band_left, left)
                band_right = max(band_right, right)
            else:
                if (band_bottom - band_top) >= 2 and (band_right - band_left) >= minimum_band_width:
                    bands.append((band_left, band_top, band_right, band_bottom))
                band_top = y
                band_bottom = y + 1
                band_left = left
                band_right = right
            previous_y = y
        if (band_bottom - band_top) >= 2 and (band_right - band_left) >= minimum_band_width:
            bands.append((band_left, band_top, band_right, band_bottom))
        return bands

    @staticmethod
    def _component(
        *,
        mask: list[list[bool]],
        visited: list[list[bool]],
        start: tuple[int, int],
    ) -> list[tuple[int, int]]:
        width = len(mask[0])
        height = len(mask)
        queue: deque[tuple[int, int]] = deque([start])
        visited[start[1]][start[0]] = True
        points: list[tuple[int, int]] = []
        while queue:
            x, y = queue.popleft()
            points.append((x, y))
            for next_x, next_y in (
                (x + 1, y),
                (x - 1, y),
                (x, y + 1),
                (x, y - 1),
            ):
                if (
                    0 <= next_x < width
                    and 0 <= next_y < height
                    and not visited[next_y][next_x]
                    and mask[next_y][next_x]
                ):
                    visited[next_y][next_x] = True
                    queue.append((next_x, next_y))
        return points
