from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from testing.components.pages.live_issue_detail_collaboration_page import ScreenRect
from testing.core.utils.color_contrast import RgbColor, color_distance, contrast_ratio, rgb_to_hex


@dataclass(frozen=True)
class LocaleWarningVisualObservation:
    background_hex: str
    expected_background_hex: str
    foreground_hex: str
    foreground_contrast_ratio: float
    screenshot_path: str
    crop_box: tuple[int, int, int, int]
    warning_box: tuple[int, int, int, int]

    def describe(self) -> str:
        return (
            f"background={self.background_hex}, "
            f"expectedBackground={self.expected_background_hex}, "
            f"foreground={self.foreground_hex}, "
            f"contrast={self.foreground_contrast_ratio:.2f}:1, "
            f"screenshot={self.screenshot_path}, "
            f"cropBox={self.crop_box}, "
            f"warningBox={self.warning_box}"
        )


class LiveLocaleWarningVisualProbe:
    _background_tolerance = 6.0

    def __init__(self) -> None:
        self._surface_alt_palettes = (
            (0xF1, 0xE4, 0xD5),
            (0x24, 0x28, 0x27),
        )

    def observe(
        self,
        *,
        screenshot_path: Path,
        input_rect: ScreenRect,
    ) -> LocaleWarningVisualObservation:
        image = Image.open(screenshot_path).convert("RGB")
        crop_box = self._crop_box(image, input_rect)
        crop = image.crop(crop_box)
        expected_background = self._expected_background(crop)
        warning_box = self._warning_box(crop, expected_background)
        warning_crop = crop.crop(warning_box)
        background = self._dominant_color(warning_crop)
        if color_distance(background, expected_background) > self._background_tolerance:
            raise AssertionError(
                "The visible locale warning pill did not render on the expected TrackState "
                "surfaceAlt token.\n"
                f"Observed background: {rgb_to_hex(background)}\n"
                f"Expected background: {rgb_to_hex(expected_background)}\n"
                f"Screenshot: {screenshot_path}",
            )
        foreground = self._sample_rendered_foreground(
            warning_crop,
            background=background,
        )
        return LocaleWarningVisualObservation(
            background_hex=rgb_to_hex(background),
            expected_background_hex=rgb_to_hex(expected_background),
            foreground_hex=rgb_to_hex(foreground),
            foreground_contrast_ratio=contrast_ratio(foreground, background),
            screenshot_path=str(screenshot_path),
            crop_box=crop_box,
            warning_box=warning_box,
        )

    @staticmethod
    def _crop_box(image: Image.Image, input_rect: ScreenRect) -> tuple[int, int, int, int]:
        left = max(int(input_rect.left - 20), 0)
        top = max(int(input_rect.top - 10), 0)
        right = min(int(input_rect.left + input_rect.width + 40), image.width)
        bottom = min(int(input_rect.top + input_rect.height + 140), image.height)
        return (left, top, right, bottom)

    def _expected_background(self, image: Image.Image) -> RgbColor:
        observed = self._dominant_color(image)
        return min(
            self._surface_alt_palettes,
            key=lambda palette: color_distance(observed, palette),
        )

    def _warning_box(
        self,
        image: Image.Image,
        expected_background: RgbColor,
    ) -> tuple[int, int, int, int]:
        mask = [
            [
                color_distance(image.getpixel((x, y)), expected_background)
                <= self._background_tolerance
                for x in range(image.width)
            ]
            for y in range(image.height)
        ]
        visited = [[False for _ in range(image.width)] for _ in range(image.height)]
        components: list[tuple[int, int, int, int, int]] = []
        for y in range(image.height):
            for x in range(image.width):
                if visited[y][x] or not mask[y][x]:
                    continue
                points = self._component(mask, visited, start=(x, y))
                xs = [point[0] for point in points]
                ys = [point[1] for point in points]
                components.append(
                    (len(points), min(xs), min(ys), max(xs), max(ys)),
                )
        viable_components = [
            component
            for component in components
            if component[0] >= 800 and component[2] >= 40
        ]
        if not viable_components:
            raise AssertionError(
                "The visible locale warning pill did not render a user-facing warning "
                "background below the translation field.",
            )
        _, left, top, right, bottom = max(viable_components)
        return (left, top, right + 1, bottom + 1)

    @staticmethod
    def _component(
        mask: list[list[bool]],
        visited: list[list[bool]],
        *,
        start: tuple[int, int],
    ) -> list[tuple[int, int]]:
        points: list[tuple[int, int]] = []
        queue = deque([start])
        visited[start[1]][start[0]] = True
        while queue:
            x, y = queue.popleft()
            points.append((x, y))
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (
                    0 <= ny < len(mask)
                    and 0 <= nx < len(mask[ny])
                    and not visited[ny][nx]
                    and mask[ny][nx]
                ):
                    visited[ny][nx] = True
                    queue.append((nx, ny))
        return points

    @staticmethod
    def _dominant_color(image: Image.Image) -> RgbColor:
        counts = Counter(image.getdata())
        color, _ = counts.most_common(1)[0]
        return color

    @staticmethod
    def _sample_rendered_foreground(
        image: Image.Image,
        *,
        background: RgbColor,
    ) -> RgbColor:
        counts = Counter(image.getdata())
        samples = [
            (color, count)
            for color, count in counts.items()
            if color_distance(color, background) > 20
            and contrast_ratio(color, background) >= 2.0
        ]
        if not samples:
            raise AssertionError(
                "The visible locale warning pill did not contain any rendered foreground "
                "pixels beyond the background surface.",
            )
        samples.sort(
            key=lambda sample: (
                sample[1],
                contrast_ratio(sample[0], background),
                color_distance(sample[0], background),
            ),
            reverse=True,
        )
        return samples[0][0]
