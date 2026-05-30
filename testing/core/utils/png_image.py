from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

RgbPixel = tuple[int, int, int]

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class RgbImage:
    width: int
    height: int
    pixels: tuple[RgbPixel, ...]

    @classmethod
    def open(cls, path: Path) -> "RgbImage":
        payload = path.read_bytes()
        if not payload.startswith(_PNG_SIGNATURE):
            raise ValueError(f"Unsupported screenshot format for {path}: expected PNG data.")

        cursor = len(_PNG_SIGNATURE)
        width = 0
        height = 0
        bit_depth = 0
        color_type = -1
        idat_chunks: list[bytes] = []

        while cursor < len(payload):
            if cursor + 8 > len(payload):
                raise ValueError(f"Corrupt PNG screenshot at {path}: truncated chunk header.")
            chunk_length = struct.unpack(">I", payload[cursor : cursor + 4])[0]
            chunk_type = payload[cursor + 4 : cursor + 8]
            chunk_start = cursor + 8
            chunk_end = chunk_start + chunk_length
            chunk_crc_end = chunk_end + 4
            if chunk_crc_end > len(payload):
                raise ValueError(f"Corrupt PNG screenshot at {path}: truncated chunk payload.")
            chunk_data = payload[chunk_start:chunk_end]
            cursor = chunk_crc_end

            if chunk_type == b"IHDR":
                (
                    width,
                    height,
                    bit_depth,
                    color_type,
                    compression_method,
                    filter_method,
                    interlace_method,
                ) = struct.unpack(">IIBBBBB", chunk_data)
                if compression_method != 0 or filter_method != 0:
                    raise ValueError(
                        f"Unsupported PNG screenshot for {path}: unsupported compression/filter method.",
                    )
                if interlace_method != 0:
                    raise ValueError(
                        f"Unsupported PNG screenshot for {path}: interlaced PNGs are not supported.",
                    )
            elif chunk_type == b"IDAT":
                idat_chunks.append(chunk_data)
            elif chunk_type == b"IEND":
                break

        if width <= 0 or height <= 0:
            raise ValueError(f"Corrupt PNG screenshot at {path}: missing IHDR chunk.")
        if bit_depth != 8:
            raise ValueError(
                f"Unsupported PNG screenshot for {path}: expected 8-bit channels, got {bit_depth}.",
            )

        channels = _channel_count(color_type)
        bytes_per_pixel = channels
        decompressed = zlib.decompress(b"".join(idat_chunks))
        stride = width * bytes_per_pixel
        expected_length = height * (stride + 1)
        if len(decompressed) != expected_length:
            raise ValueError(
                f"Corrupt PNG screenshot at {path}: unexpected image payload length {len(decompressed)}.",
            )

        rows: list[bytes] = []
        previous = bytes(stride)
        offset = 0
        for _ in range(height):
            filter_type = decompressed[offset]
            raw_row = decompressed[offset + 1 : offset + 1 + stride]
            row = _unfilter_row(
                filter_type=filter_type,
                row=raw_row,
                previous=previous,
                bytes_per_pixel=bytes_per_pixel,
            )
            rows.append(row)
            previous = row
            offset += stride + 1

        pixels: list[RgbPixel] = []
        for row in rows:
            for index in range(0, len(row), bytes_per_pixel):
                pixel = _to_rgb(
                    color_type=color_type,
                    channels=row[index : index + bytes_per_pixel],
                )
                pixels.append(pixel)
        return cls(width=width, height=height, pixels=tuple(pixels))

    def crop(self, box: tuple[int, int, int, int]) -> "RgbImage":
        left, top, right, bottom = box
        left = max(left, 0)
        top = max(top, 0)
        right = min(right, self.width)
        bottom = min(bottom, self.height)
        if left >= right or top >= bottom:
            raise ValueError(f"Invalid crop box {box!r} for image {self.width}x{self.height}.")

        cropped_pixels: list[RgbPixel] = []
        for y in range(top, bottom):
            row_start = y * self.width
            cropped_pixels.extend(self.pixels[row_start + left : row_start + right])
        return RgbImage(
            width=right - left,
            height=bottom - top,
            pixels=tuple(cropped_pixels),
        )

    def getdata(self) -> tuple[RgbPixel, ...]:
        return self.pixels


def _channel_count(color_type: int) -> int:
    if color_type == 0:
        return 1
    if color_type == 2:
        return 3
    if color_type == 4:
        return 2
    if color_type == 6:
        return 4
    raise ValueError(f"Unsupported PNG color type: {color_type}.")


def _unfilter_row(
    *,
    filter_type: int,
    row: bytes,
    previous: bytes,
    bytes_per_pixel: int,
) -> bytes:
    if filter_type == 0:
        return row

    reconstructed = bytearray(len(row))
    for index, value in enumerate(row):
        left = reconstructed[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        up = previous[index]
        upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0

        if filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = up
        elif filter_type == 3:
            predictor = (left + up) // 2
        elif filter_type == 4:
            predictor = _paeth_predictor(left=left, up=up, upper_left=upper_left)
        else:
            raise ValueError(f"Unsupported PNG filter type: {filter_type}.")

        reconstructed[index] = (value + predictor) & 0xFF
    return bytes(reconstructed)


def _paeth_predictor(*, left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def _to_rgb(*, color_type: int, channels: bytes) -> RgbPixel:
    if color_type == 0:
        channel = channels[0]
        return (channel, channel, channel)
    if color_type == 2:
        return (channels[0], channels[1], channels[2])
    if color_type == 4:
        return _composite_on_white(channels[0], channels[0], channels[0], channels[1])
    if color_type == 6:
        return _composite_on_white(channels[0], channels[1], channels[2], channels[3])
    raise ValueError(f"Unsupported PNG color type: {color_type}.")


def _composite_on_white(red: int, green: int, blue: int, alpha: int) -> RgbPixel:
    if alpha >= 255:
        return (red, green, blue)
    alpha_ratio = alpha / 255
    return (
        round(red * alpha_ratio + 255 * (1 - alpha_ratio)),
        round(green * alpha_ratio + 255 * (1 - alpha_ratio)),
        round(blue * alpha_ratio + 255 * (1 - alpha_ratio)),
    )
