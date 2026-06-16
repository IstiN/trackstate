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
    expected_foreground_hex: str
    foreground_distance: float
    border_hex: str
    expected_border_hex: str
    border_distance: float
    foreground_contrast_ratio: float
    screenshot_path: str
    crop_box: tuple[int, int, int, int]
    warning_box: tuple[int, int, int, int]

    def describe(self) -> str:
        return (
            f"background={self.background_hex}, "
            f"expectedBackground={self.expected_background_hex}, "
            f"foreground={self.foreground_hex}, "
            f"expectedForeground={self.expected_foreground_hex}, "
            f"foregroundDistance={self.foreground_distance:.2f}, "
            f"border={self.border_hex}, "
            f"expectedBorder={self.expected_border_hex}, "
            f"borderDistance={self.border_distance:.2f}, "
            f"contrast={self.foreground_contrast_ratio:.2f}:1, "
            f"screenshot={self.screenshot_path}, "
            f"cropBox={self.crop_box}, "
            f"warningBox={self.warning_box}"
        )


class LiveLocaleWarningVisualProbe:
    _background_tolerance = 6.0

    def __init__(self) -> None:
        self._palettes = (
            {"surface_alt": (0xF1, 0xE4, 0xD5), "warning": (0x7A, 0x65, 0x11)},
            {"surface_alt": (0x24, 0x28, 0x27), "warning": (0xF7, 0xC9, 0x66)},
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
        expected_warning = self._expected_warning(expected_background)
        foreground = self._sample_rendered_foreground(
            warning_crop,
            background=background,
        )
        border = self._sample_border_color(
            crop.crop(self._expand_box(crop, warning_box, pixels=3)),
            background=background,
        )
        return LocaleWarningVisualObservation(
            background_hex=rgb_to_hex(background),
            expected_background_hex=rgb_to_hex(expected_background),
            foreground_hex=rgb_to_hex(foreground),
            expected_foreground_hex=rgb_to_hex(expected_warning),
            foreground_distance=color_distance(foreground, expected_warning),
            border_hex=rgb_to_hex(border),
            expected_border_hex=rgb_to_hex(expected_warning),
            border_distance=color_distance(border, expected_warning),
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
        palette = min(
            self._palettes,
            key=lambda candidate: color_distance(observed, candidate["surface_alt"]),
        )
        return palette["surface_alt"]

    def _expected_warning(self, expected_background: RgbColor) -> RgbColor:
        for palette in self._palettes:
            if palette["surface_alt"] == expected_background:
                return palette["warning"]
        raise AssertionError(
            "Could not determine the expected TrackState warning token for the sampled warning pill.",
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
    def _expand_box(
        image: Image.Image,
        box: tuple[int, int, int, int],
        *,
        pixels: int,
    ) -> tuple[int, int, int, int]:
        left, top, right, bottom = box
        return (
            max(left - pixels, 0),
            max(top - pixels, 0),
            min(right + pixels, image.width),
            min(bottom + pixels, image.height),
        )

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

    @staticmethod
    def _sample_border_color(
        image: Image.Image,
        *,
        background: RgbColor,
    ) -> RgbColor:
        edge_width = max(2, min(6, image.width // 30, image.height // 12))
        edge_pixels = [
            *image.crop((0, 0, image.width, min(edge_width, image.height))).getdata(),
            *image.crop((0, max(image.height - edge_width, 0), image.width, image.height)).getdata(),
            *image.crop((0, 0, min(edge_width, image.width), image.height)).getdata(),
            *image.crop((max(image.width - edge_width, 0), 0, image.width, image.height)).getdata(),
        ]
        contrasting = [
            color for color in edge_pixels if color_distance(color, background) > 10
        ]
        if contrasting:
            counts = Counter(contrasting)
            color, _ = counts.most_common(1)[0]
            return color
        counts = Counter(edge_pixels)
        color, _ = counts.most_common(1)[0]
        return color
