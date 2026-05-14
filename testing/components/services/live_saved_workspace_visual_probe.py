from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
import math

from testing.components.pages.live_workspace_management_page import (
    SavedWorkspaceActionObservation,
    SavedWorkspaceListObservation,
    SavedWorkspaceRowObservation,
)
from testing.core.utils.color_contrast import (
    RgbColor,
    color_distance,
    contrast_ratio,
    rgb_to_hex,
)
from testing.core.utils.png_image import RgbImage


class LiveSavedWorkspaceVisualProbe:
    def observe(
        self,
        *,
        screenshot_path: Path,
        observation: SavedWorkspaceListObservation,
    ) -> SavedWorkspaceListObservation:
        image = RgbImage.open(screenshot_path)
        rows = tuple(self._observe_row(image=image, row=row) for row in observation.rows)
        return replace(observation, rows=rows)

    def _observe_row(
        self,
        *,
        image: RgbImage,
        row: SavedWorkspaceRowObservation,
    ) -> SavedWorkspaceRowObservation:
        row_box = self._box(
            image=image,
            left=row.left,
            top=row.top,
            width=row.width,
            height=row.height,
        )
        if row_box is None:
            return row

        background_rgb = self._dominant_color(
            image.crop(self._inset_box(row_box, horizontal=20, vertical=12)),
        )
        border_rgb = self._edge_color(image=image, crop_box=row_box, background=background_rgb)
        title = self._foreground_metrics(
            image=image,
            box=self._box(
                image=image,
                left=row.title_left,
                top=row.title_top,
                width=row.title_width,
                height=row.title_height,
            ),
            background=background_rgb,
        )
        detail = self._foreground_metrics(
            image=image,
            box=self._box(
                image=image,
                left=row.detail_left,
                top=row.detail_top,
                width=row.detail_width,
                height=row.detail_height,
            ),
            background=background_rgb,
        )
        target_type = self._foreground_metrics(
            image=image,
            box=self._box(
                image=image,
                left=row.type_left,
                top=row.type_top,
                width=row.type_width,
                height=row.type_height,
            ),
            background=background_rgb,
        )
        icon = self._foreground_metrics(
            image=image,
            box=self._box(
                image=image,
                left=row.icon_left,
                top=row.icon_top,
                width=row.icon_width,
                height=row.icon_height,
            ),
            background=background_rgb,
        )
        actions = tuple(
            self._observe_action(
                image=image,
                action=action,
                row_background=background_rgb,
            )
            for action in row.action_observations
        )
        return replace(
            row,
            background_color=rgb_to_hex(background_rgb).lower(),
            border_color=rgb_to_hex(border_rgb).lower(),
            title_color=title[0],
            title_contrast_ratio=title[1],
            detail_color=detail[0],
            detail_contrast_ratio=detail[1],
            type_color=target_type[0],
            type_contrast_ratio=target_type[1],
            icon_color=icon[0],
            icon_contrast_ratio=icon[1],
            action_observations=actions,
        )

    def _observe_action(
        self,
        *,
        image: RgbImage,
        action: SavedWorkspaceActionObservation,
        row_background: RgbColor,
    ) -> SavedWorkspaceActionObservation:
        action_box = self._box(
            image=image,
            left=action.left,
            top=action.top,
            width=action.width,
            height=action.height,
        )
        if action_box is None:
            return action
        foreground = self._foreground_metrics(
            image=image,
            box=action_box,
            background=row_background,
        )
        border_rgb = self._edge_color(
            image=image,
            crop_box=action_box,
            background=row_background,
        )
        border_distance = color_distance(border_rgb, row_background)
        return replace(
            action,
            foreground_color=foreground[0],
            background_color=rgb_to_hex(row_background).lower(),
            border_color=(
                rgb_to_hex(border_rgb).lower() if border_distance > 8 else None
            ),
            contrast_ratio=foreground[1],
            border_contrast_ratio=(
                contrast_ratio(border_rgb, row_background) if border_distance > 8 else None
            ),
        )

    @staticmethod
    def _box(
        *,
        image: RgbImage,
        left: float | None,
        top: float | None,
        width: float | None,
        height: float | None,
    ) -> tuple[int, int, int, int] | None:
        if (
            left is None
            or top is None
            or width is None
            or height is None
            or width <= 0
            or height <= 0
        ):
            return None
        box = (
            max(int(math.floor(left)), 0),
            max(int(math.floor(top)), 0),
            min(int(math.ceil(left + width)), image.width),
            min(int(math.ceil(top + height)), image.height),
        )
        if box[0] >= box[2] or box[1] >= box[3]:
            return None
        return box

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

    @staticmethod
    def _dominant_color(image: RgbImage) -> RgbColor:
        counts = Counter(image.getdata())
        color, _ = counts.most_common(1)[0]
        return color

    def _edge_color(
        self,
        *,
        image: RgbImage,
        crop_box: tuple[int, int, int, int],
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
        return self._dominant_color_from_pixels(contrasting or edge_pixels)

    def _foreground_metrics(
        self,
        *,
        image: RgbImage,
        box: tuple[int, int, int, int] | None,
        background: RgbColor,
    ) -> tuple[str | None, float | None]:
        if box is None:
            return (None, None)
        crop = image.crop(box)
        foreground = self._sample_foreground(crop, background=background)
        if foreground is None:
            return (None, None)
        return (rgb_to_hex(foreground).lower(), round(contrast_ratio(foreground, background), 2))

    def _sample_foreground(
        self,
        image: RgbImage,
        *,
        background: RgbColor,
    ) -> RgbColor | None:
        counts = Counter(image.getdata())
        samples = [
            (color, count)
            for color, count in counts.items()
            if color_distance(color, background) > 20
        ]
        if not samples:
            return None
        strongest_distance = max(
            color_distance(color, background)
            for color, _ in samples
        )
        strongest_samples = [
            (color, count)
            for color, count in samples
            if strongest_distance - color_distance(color, background) <= 8
        ]
        total = sum(count for _, count in strongest_samples)
        return (
            round(sum(color[0] * count for color, count in strongest_samples) / total),
            round(sum(color[1] * count for color, count in strongest_samples) / total),
            round(sum(color[2] * count for color, count in strongest_samples) / total),
        )

    @staticmethod
    def _dominant_color_from_pixels(pixels) -> RgbColor:
        counts = Counter(pixels)
        color, _ = counts.most_common(1)[0]
        return color
