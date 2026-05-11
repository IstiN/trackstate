from __future__ import annotations

import math

RgbColor = tuple[int, int, int]


def contrast_ratio(foreground: RgbColor, background: RgbColor) -> float:
    lighter = _relative_luminance(foreground)
    darker = _relative_luminance(background)
    maximum = lighter if lighter > darker else darker
    minimum = darker if lighter > darker else lighter
    return (maximum + 0.05) / (minimum + 0.05)


def rgb_to_hex(color: RgbColor) -> str:
    return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"


def color_distance(left: RgbColor, right: RgbColor) -> float:
    return math.sqrt(
        ((left[0] - right[0]) ** 2)
        + ((left[1] - right[1]) ** 2)
        + ((left[2] - right[2]) ** 2),
    )


def _relative_luminance(color: RgbColor) -> float:
    def channel(value: int) -> float:
        normalized = value / 255
        if normalized <= 0.03928:
            return normalized / 12.92
        return ((normalized + 0.055) / 1.055) ** 2.4

    return (
        (0.2126 * channel(color[0]))
        + (0.7152 * channel(color[1]))
        + (0.0722 * channel(color[2]))
    )
