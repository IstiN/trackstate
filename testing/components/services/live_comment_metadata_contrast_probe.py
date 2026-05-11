from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from testing.components.pages.live_issue_detail_collaboration_page import ScreenRect
from testing.core.utils.color_contrast import (
    RgbColor,
    color_distance,
    contrast_ratio,
    rgb_to_hex,
)


@dataclass(frozen=True)
class ThemePalette:
    name: str
    surface_alt: RgbColor
    text: RgbColor
    muted: RgbColor


@dataclass(frozen=True)
class CommentMetadataContrastObservation:
    theme_name: str
    row_background_hex: str
    expected_background_hex: str
    inferred_token_name: str
    inferred_foreground_hex: str
    contrast_ratio: float
    screenshot_path: str
    timestamp_crop_box: tuple[int, int, int, int]

    def describe(self) -> str:
        return (
            f"theme={self.theme_name}, background={self.row_background_hex}, "
            f"expectedBackground={self.expected_background_hex}, "
            f"metadataToken={self.inferred_token_name} ({self.inferred_foreground_hex}), "
            f"contrast={self.contrast_ratio:.2f}:1, screenshot={self.screenshot_path}, "
            f"timestampCrop={self.timestamp_crop_box}"
        )


class LiveCommentMetadataContrastProbe:
    _background_tolerance = 4.0

    def __init__(self) -> None:
        self._palettes = {
            "light": ThemePalette(
                name="light",
                surface_alt=(0xF1, 0xE4, 0xD5),
                text=(0x2D, 0x2A, 0x26),
                muted=(0x6B, 0x6D, 0x63),
            ),
            "dark": ThemePalette(
                name="dark",
                surface_alt=(0x24, 0x28, 0x27),
                text=(0xFA, 0xF8, 0xF4),
                muted=(0xB5, 0xA4, 0x98),
            ),
        }

    def observe(
        self,
        *,
        screenshot_path: Path,
        row_rect: ScreenRect,
        theme_name: str,
    ) -> CommentMetadataContrastObservation:
        palette = self._palettes[theme_name]
        image = Image.open(screenshot_path).convert("RGB")
        row_box = self._row_box(image, row_rect)
        row_background = self._dominant_color(image.crop(row_box))
        if color_distance(row_background, palette.surface_alt) > self._background_tolerance:
            raise AssertionError(
                "Step 2 failed: the visible comment row did not render on the expected "
                f"{theme_name} collaboration surface token.\n"
                f"Observed background: {rgb_to_hex(row_background)}\n"
                f"Expected background: {rgb_to_hex(palette.surface_alt)}\n"
                f"Screenshot: {screenshot_path}",
            )

        timestamp_box = self._comment_timestamp_box(image, row_rect)
        timestamp_crop = image.crop(timestamp_box)
        inferred_name, inferred_color = self._infer_foreground_token(
            timestamp_crop,
            background=row_background,
            palette=palette,
        )
        return CommentMetadataContrastObservation(
            theme_name=theme_name,
            row_background_hex=rgb_to_hex(row_background),
            expected_background_hex=rgb_to_hex(palette.surface_alt),
            inferred_token_name=inferred_name,
            inferred_foreground_hex=rgb_to_hex(inferred_color),
            contrast_ratio=contrast_ratio(inferred_color, row_background),
            screenshot_path=str(screenshot_path),
            timestamp_crop_box=timestamp_box,
        )

    @staticmethod
    def _row_box(image: Image.Image, row_rect: ScreenRect) -> tuple[int, int, int, int]:
        left = max(int(row_rect.left), 0)
        top = max(int(row_rect.top), 0)
        right = min(int(row_rect.left + row_rect.width), image.width)
        bottom = min(int(row_rect.top + row_rect.height), image.height)
        return (left, top, right, bottom)

    @staticmethod
    def _comment_timestamp_box(
        image: Image.Image,
        row_rect: ScreenRect,
    ) -> tuple[int, int, int, int]:
        left = max(int(row_rect.left + (row_rect.width * 0.695)), 0)
        top = max(int(row_rect.top + 8), 0)
        right = min(int(row_rect.left + row_rect.width - 8), image.width)
        bottom = min(int(row_rect.top + 30), image.height)
        return (left, top, right, bottom)

    @staticmethod
    def _dominant_color(image: Image.Image) -> RgbColor:
        counts = Counter(image.getdata())
        color, _ = counts.most_common(1)[0]
        return color

    def _infer_foreground_token(
        self,
        image: Image.Image,
        *,
        background: RgbColor,
        palette: ThemePalette,
    ) -> tuple[str, RgbColor]:
        counts = Counter(image.getdata())
        samples = [
            (color, count)
            for color, count in counts.items()
            if self._manhattan_distance(color, background) > 20
        ]
        if not samples:
            raise AssertionError(
                "Step 2 failed: the timestamp crop did not contain any visible metadata "
                "pixels to evaluate contrast.",
            )

        candidates: dict[str, RgbColor] = {
            "text": palette.text,
            "muted": palette.muted,
        }
        scored = sorted(
            (
                (
                    self._fit_score(
                        samples=samples,
                        background=background,
                        foreground=foreground,
                    ),
                    name,
                    foreground,
                )
                for name, foreground in candidates.items()
            ),
            key=lambda entry: entry[0],
        )
        _, best_name, best_color = scored[0]
        return best_name, best_color

    def _fit_score(
        self,
        *,
        samples: list[tuple[RgbColor, int]],
        background: RgbColor,
        foreground: RgbColor,
    ) -> float:
        weighted_error = 0.0
        total_weight = 0
        for observed, count in samples:
            best_error = min(
                self._squared_distance(
                    observed,
                    self._alpha_blend(background=background, foreground=foreground, alpha=alpha),
                )
                for alpha in range(1, 256)
            )
            weighted_error += best_error * count
            total_weight += count
        return weighted_error / max(total_weight, 1)

    @staticmethod
    def _alpha_blend(
        *,
        background: RgbColor,
        foreground: RgbColor,
        alpha: int,
    ) -> RgbColor:
        normalized_alpha = alpha / 255
        return (
            round((normalized_alpha * foreground[0]) + ((1 - normalized_alpha) * background[0])),
            round((normalized_alpha * foreground[1]) + ((1 - normalized_alpha) * background[1])),
            round((normalized_alpha * foreground[2]) + ((1 - normalized_alpha) * background[2])),
        )

    @staticmethod
    def _squared_distance(left: RgbColor, right: RgbColor) -> int:
        return (
            ((left[0] - right[0]) ** 2)
            + ((left[1] - right[1]) ** 2)
            + ((left[2] - right[2]) ** 2)
        )

    @staticmethod
    def _manhattan_distance(left: RgbColor, right: RgbColor) -> int:
        return (
            abs(left[0] - right[0])
            + abs(left[1] - right[1])
            + abs(left[2] - right[2])
        )
