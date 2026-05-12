from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from testing.components.pages.live_project_settings_page import (
    RepositoryAccessCalloutObservation,
)
from testing.core.utils.color_contrast import RgbColor, color_distance, rgb_to_hex
from testing.core.utils.png_image import RgbImage


@dataclass(frozen=True)
class AccessCalloutColorObservation:
    background_rgb: RgbColor
    background_hex: str
    border_rgb: RgbColor
    border_hex: str
    screenshot_path: str
    crop_box: tuple[int, int, int, int]


class LiveAccessCalloutColorProbe:
    def observe(
        self,
        *,
        screenshot_path: Path,
        callout: RepositoryAccessCalloutObservation,
    ) -> AccessCalloutColorObservation:
        image = RgbImage.open(screenshot_path)
        crop_box = self._callout_box(image, callout)
        background_box = self._inset_box(crop_box, horizontal=24, vertical=20)
        background = self._dominant_color(image.crop(background_box))
        border = self._edge_color(image, crop_box, background=background)
        return AccessCalloutColorObservation(
            background_rgb=background,
            background_hex=rgb_to_hex(background),
            border_rgb=border,
            border_hex=rgb_to_hex(border),
            screenshot_path=str(screenshot_path),
            crop_box=crop_box,
        )

    @staticmethod
    def _callout_box(
        image: RgbImage,
        callout: RepositoryAccessCalloutObservation,
    ) -> tuple[int, int, int, int]:
        left = max(int(callout.left), 0)
        top = max(int(callout.top), 0)
        right = min(int(callout.left + callout.width), image.width)
        bottom = min(int(callout.top + callout.height), image.height)
        return (left, top, right, bottom)

    @staticmethod
    def _inset_box(
        crop_box: tuple[int, int, int, int],
        *,
        horizontal: int,
        vertical: int,
    ) -> tuple[int, int, int, int]:
        left, top, right, bottom = crop_box
        inset_left = min(left + horizontal, right - 1)
        inset_top = min(top + vertical, bottom - 1)
        inset_right = max(right - horizontal, inset_left + 1)
        inset_bottom = max(bottom - vertical, inset_top + 1)
        return (inset_left, inset_top, inset_right, inset_bottom)

    def _edge_color(
        self,
        image: RgbImage,
        crop_box: tuple[int, int, int, int],
        *,
        background: RgbColor,
    ) -> RgbColor:
        left, top, right, bottom = crop_box
        edge_width = max(2, min(6, (right - left) // 40, (bottom - top) // 20))
        edge_pixels = [
            *image.crop((left, top, right, min(top + edge_width, bottom))).getdata(),
            *image.crop((left, max(bottom - edge_width, top), right, bottom)).getdata(),
            *image.crop((left, top, min(left + edge_width, right), bottom)).getdata(),
            *image.crop((max(right - edge_width, left), top, right, bottom)).getdata(),
        ]
        contrasting = [
            color
            for color in edge_pixels
            if color_distance(color, background) > 10
        ]
        if contrasting:
            return self._dominant_color_from_pixels(contrasting)
        return self._dominant_color_from_pixels(edge_pixels)

    @staticmethod
    def _dominant_color(image: RgbImage) -> RgbColor:
        return LiveAccessCalloutColorProbe._dominant_color_from_pixels(image.getdata())

    @staticmethod
    def _dominant_color_from_pixels(pixels) -> RgbColor:
        counts = Counter(pixels)
        color, _ = counts.most_common(1)[0]
        return color
