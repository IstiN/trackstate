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
    _reference_fingerprints: dict[str, str] | None = None
    _REFERENCE_ICON_FINGERPRINTS = {
        "repository": "0000000001111111011111110111111101111111011111110111111101111110",
        "folder": "0000000000011111011111110111001101000010011111100111111000000000",
    }

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
        icon_box = self._box(
            image=image,
            left=row.icon_left,
            top=row.icon_top,
            width=row.icon_width,
            height=row.icon_height,
        )
        icon = self._foreground_metrics(
            image=image,
            box=icon_box,
            background=background_rgb,
        )
        icon_identity, icon_fingerprint = self._classify_icon(
            image=image,
            box=icon_box,
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
            icon_identity=icon_identity,
            icon_fingerprint=icon_fingerprint,
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

    def _classify_icon(
        self,
        *,
        image: RgbImage,
        box: tuple[int, int, int, int] | None,
        background: RgbColor,
    ) -> tuple[str | None, str | None]:
        if box is None:
            return (None, None)
        fingerprint = self._icon_fingerprint(image.crop(box), background=background)
        if fingerprint is None:
            return (None, None)
        distances = sorted(
            (
                (identity, self._hamming_distance(fingerprint, reference))
                for identity, reference in self._reference_icon_fingerprints().items()
            ),
            key=lambda item: item[1],
        )
        if not distances:
            return (None, fingerprint)
        best_identity, best_distance = distances[0]
        if len(distances) > 1 and distances[1][1] - best_distance < 4:
            return (None, fingerprint)
        if best_distance > 24:
            return (None, fingerprint)
        return (best_identity, fingerprint)

    def _reference_icon_fingerprints(self) -> dict[str, str]:
        if self._reference_fingerprints is None:
            self._reference_fingerprints = dict(self._REFERENCE_ICON_FINGERPRINTS)
        return self._reference_fingerprints

    def _reference_icon_fingerprint(self, kind: str) -> str:
        bits: list[str] = []
        size = 32
        cells = 8
        for row_index in range(cells):
            for column_index in range(cells):
                start_x = math.floor((column_index * size) / cells)
                end_x = math.floor(((column_index + 1) * size) / cells)
                start_y = math.floor((row_index * size) / cells)
                end_y = math.floor(((row_index + 1) * size) / cells)
                ink_pixels = 0
                total_pixels = 0
                for y in range(start_y, end_y):
                    for x in range(start_x, end_x):
                        total_pixels += 1
                        if self._reference_icon_contains_ink(kind, x + 0.5, y + 0.5):
                            ink_pixels += 1
                bits.append("1" if total_pixels > 0 and (ink_pixels / total_pixels) >= 0.08 else "0")
        return "".join(bits)

    def _icon_fingerprint(self, image: RgbImage, *, background: RgbColor) -> str | None:
        bits: list[str] = []
        cells = 8
        for row_index in range(cells):
            for column_index in range(cells):
                start_x = math.floor((column_index * image.width) / cells)
                end_x = math.floor(((column_index + 1) * image.width) / cells)
                start_y = math.floor((row_index * image.height) / cells)
                end_y = math.floor(((row_index + 1) * image.height) / cells)
                ink_pixels = 0
                total_pixels = 0
                for y in range(start_y, end_y):
                    row_offset = y * image.width
                    for x in range(start_x, end_x):
                        total_pixels += 1
                        if color_distance(image.pixels[row_offset + x], background) > 18:
                            ink_pixels += 1
                bits.append("1" if total_pixels > 0 and (ink_pixels / total_pixels) >= 0.08 else "0")
        fingerprint = "".join(bits)
        return fingerprint if "1" in fingerprint else None

    @staticmethod
    def _hamming_distance(left: str, right: str) -> int:
        return sum(1 for left_bit, right_bit in zip(left, right) if left_bit != right_bit)

    def _reference_icon_contains_ink(self, kind: str, x: float, y: float) -> bool:
        if kind == "repository":
            return self._repository_icon_contains_ink(x, y)
        if kind == "folder":
            return self._folder_icon_contains_ink(x, y)
        raise ValueError(f"Unsupported icon reference kind: {kind}")

    def _repository_icon_contains_ink(self, x: float, y: float) -> bool:
        size = 32
        stroke_width = size * 0.08
        half_stroke = stroke_width / 2
        left = size * 0.18
        top = size * 0.16
        right = size * 0.82
        bottom = size * 0.84
        radius = size * 0.08
        if self._is_rounded_rect_stroke(
            x=x,
            y=y,
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            radius=radius,
            stroke_width=stroke_width,
        ):
            return True
        if self._distance_to_segment(x, y, left, size * 0.34, right, size * 0.34) <= half_stroke:
            return True
        if self._distance_to_segment(x, y, size * 0.32, size * 0.54, size * 0.66, size * 0.54) <= half_stroke:
            return True
        if self._distance_to_segment(x, y, size * 0.32, size * 0.68, size * 0.58, size * 0.68) <= half_stroke:
            return True
        return math.hypot(x - (size * 0.3), y - (size * 0.25)) <= (size * 0.03)

    def _folder_icon_contains_ink(self, x: float, y: float) -> bool:
        size = 32
        stroke_width = size * 0.08
        half_stroke = stroke_width / 2
        points = (
            (size * 0.14, size * 0.32),
            (size * 0.38, size * 0.32),
            (size * 0.46, size * 0.22),
            (size * 0.84, size * 0.22),
            (size * 0.78, size * 0.78),
            (size * 0.18, size * 0.78),
        )
        for start, end in zip(points, (*points[1:], points[0])):
            if self._distance_to_segment(x, y, start[0], start[1], end[0], end[1]) <= half_stroke:
                return True
        return False

    def _is_rounded_rect_stroke(
        self,
        *,
        x: float,
        y: float,
        left: float,
        top: float,
        right: float,
        bottom: float,
        radius: float,
        stroke_width: float,
    ) -> bool:
        half_stroke = stroke_width / 2
        outer = self._inside_rounded_rect(
            x=x,
            y=y,
            left=left - half_stroke,
            top=top - half_stroke,
            right=right + half_stroke,
            bottom=bottom + half_stroke,
            radius=radius + half_stroke,
        )
        inner = self._inside_rounded_rect(
            x=x,
            y=y,
            left=left + half_stroke,
            top=top + half_stroke,
            right=right - half_stroke,
            bottom=bottom - half_stroke,
            radius=max(radius - half_stroke, 0),
        )
        return outer and not inner

    @staticmethod
    def _inside_rounded_rect(
        *,
        x: float,
        y: float,
        left: float,
        top: float,
        right: float,
        bottom: float,
        radius: float,
    ) -> bool:
        if x < left or x > right or y < top or y > bottom:
            return False
        if radius <= 0:
            return True
        inner_left = left + radius
        inner_right = right - radius
        inner_top = top + radius
        inner_bottom = bottom - radius
        if inner_left <= x <= inner_right or inner_top <= y <= inner_bottom:
            return True
        corner_x = inner_left if x < inner_left else inner_right
        corner_y = inner_top if y < inner_top else inner_bottom
        return ((x - corner_x) ** 2) + ((y - corner_y) ** 2) <= radius**2

    @staticmethod
    def _distance_to_segment(
        x: float,
        y: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> float:
        delta_x = x2 - x1
        delta_y = y2 - y1
        if delta_x == 0 and delta_y == 0:
            return math.hypot(x - x1, y - y1)
        projection = ((x - x1) * delta_x + (y - y1) * delta_y) / ((delta_x**2) + (delta_y**2))
        clamped = min(1.0, max(0.0, projection))
        closest_x = x1 + (clamped * delta_x)
        closest_y = y1 + (clamped * delta_y)
        return math.hypot(x - closest_x, y - closest_y)
