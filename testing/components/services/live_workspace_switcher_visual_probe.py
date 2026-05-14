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
        component = self._leading_icon_component(crop=crop, background=background)
        return WorkspaceSwitcherTriggerVisualObservation(
            icon_visible=component is not None,
            icon_pixel_count=component[0] if component is not None else 0,
            icon_box=component[1] if component is not None else None,
            background_hex=rgb_to_hex(background).lower(),
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

    def _leading_icon_component(
        self,
        *,
        crop: RgbImage,
        background: tuple[int, int, int],
    ) -> tuple[int, tuple[int, int, int, int]] | None:
        width = crop.width
        height = crop.height
        mask = [
            [
                color_distance(crop.pixels[(y * width) + x], background)
                > self._foreground_threshold
                for x in range(width)
            ]
            for y in range(height)
        ]
        visited = [[False for _ in range(width)] for _ in range(height)]
        candidates: list[tuple[int, tuple[int, int, int, int]]] = []
        for y in range(height):
            for x in range(width):
                if visited[y][x] or not mask[y][x]:
                    continue
                component = self._component(mask=mask, visited=visited, start=(x, y))
                pixel_count = len(component)
                xs = [point[0] for point in component]
                ys = [point[1] for point in component]
                left = min(xs)
                top = min(ys)
                right = max(xs)
                bottom = max(ys)
                component_width = right - left + 1
                component_height = bottom - top + 1
                if pixel_count < self._minimum_icon_pixels:
                    continue
                if left > min(int(width * 0.25), 48):
                    continue
                if component_width < 8 or component_width > 32:
                    continue
                if component_height < 8 or component_height > 28:
                    continue
                if right >= min(int(width * 0.35), 72):
                    continue
                candidates.append((pixel_count, (left, top, right + 1, bottom + 1)))
        if not candidates:
            return None
        return max(candidates, key=lambda candidate: candidate[0])

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
