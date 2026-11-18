# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared GUI/device renderer with bounded pre-encoded animation caches."""

import io
import math
from dataclasses import dataclass
from pathlib import Path
from threading import Event

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageSequence

from .topology import MATRIX_BYTES, MATRIX_SIZE, PIXELS

MAX_PIXELS = 16 * 1024 * 1024
MAX_FRAMES = 2000
MAX_CACHE = 64 * 1024 * 1024


@dataclass(frozen=True)
class Frame:
    data: bytes
    duration: float


def fit_image(image, size, fit="contain", rotation=0, brightness=100):
    if not 0 <= brightness <= 100 or rotation not in (0, 90, 180, 270):
        raise ValueError("Invalid brightness or rotation")
    image = ImageOps.exif_transpose(image).convert("RGBA")
    background = Image.new("RGBA", image.size, (0, 0, 0, 255))
    image = Image.alpha_composite(background, image).convert("RGB")
    if rotation:
        image = image.rotate(-rotation, expand=True)
    if fit == "cover":
        image = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
    elif fit == "contain":
        image = ImageOps.pad(image, size, method=Image.Resampling.LANCZOS, color="black")
    elif fit == "stretch":
        image = image.resize(size, Image.Resampling.LANCZOS)
    else:
        raise ValueError("Fit must be contain, cover or stretch")
    if brightness != 100:
        image = image.point([round(v * brightness / 100) for v in range(256)] * 3)
    return image


def matrix_frame(image):
    if image.size != MATRIX_SIZE:
        raise ValueError("Matrix raster must be 7 x 36 (portrait)")
    pixels = image.convert("RGB").load()
    frame = bytearray(MATRIX_BYTES)
    for x, y, offset in PIXELS:
        frame[offset], frame[offset + 16], frame[offset + 32] = pixels[x, y]
    return bytes(frame)


def matrix_image(frame):
    if len(frame) != MATRIX_BYTES:
        raise ValueError("Matrix frame must be 768 bytes")
    image = Image.new("RGB", MATRIX_SIZE)
    for x, y, offset in PIXELS:
        image.putpixel((x, y), tuple(frame[offset + channel * 16] for channel in range(3)))
    return image


def jpeg_frame(image):
    stream = io.BytesIO()
    image.convert("RGB").save(stream, format="JPEG", quality=90, subsampling=0)
    data = stream.getvalue()
    if len(data) > 1024 * 1024:
        raise ValueError("Encoded image exceeds the LCD's 1 MiB limit")
    return data


def encode_image(image, device, brightness=100, rotation=0, fit="contain"):
    size = MATRIX_SIZE if device == "matrix" else (480, 480)
    image = fit_image(image, size, fit, rotation, brightness if device == "matrix" else 100)
    return matrix_frame(image) if device == "matrix" else jpeg_frame(image)


def image_frames(
    path: Path | str, device, fit="contain", rotation=0, brightness=100, stop: Event | None = None
):
    frames, total = [], 0
    with Image.open(path) as source:
        if source.width * source.height > MAX_PIXELS:
            raise ValueError("Source image exceeds 16 megapixels")
        skip_poster = bool(source.info.get("default_image", False))
        for index, frame in enumerate(ImageSequence.Iterator(source)):
            if stop is not None and stop.is_set():
                raise InterruptedError("Preparation cancelled")
            if skip_poster and index == 0:
                continue
            if len(frames) >= MAX_FRAMES:
                raise ValueError("Animation exceeds 2000 frames")
            data = encode_image(frame, device, brightness, rotation, fit)
            duration = float(frame.info.get("duration", 100) or 100) / 1000
            if not math.isfinite(duration) or duration < 0:
                raise ValueError("Invalid animation duration")
            duration = max(0.001, duration)
            total += len(data)
            if total > MAX_CACHE:
                raise ValueError("Animation exceeds 64 MiB encoded cache")
            frames.append(Frame(data, duration))
    if not frames:
        raise ValueError("Animation contains no playable frames")
    return frames


def text_image(text, size, color="white", font_path=None):
    """Fit wrapped text on portrait Matrix; keep clock digits legible in 2 rows."""
    if not text or len(text) > 256:
        raise ValueError("Text must contain 1..256 characters")
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    # Pillow's bundled font works without Windows fonts or external assets.
    for pixel_size in range(min(size[1], 80), 3, -1):
        font = (
            ImageFont.truetype(str(font_path), pixel_size)
            if font_path
            else ImageFont.load_default(size=pixel_size)
        )
        lines = []
        for paragraph in text.split("\n"):
            line = ""
            for char in paragraph:
                if line and draw.textlength(line + char, font=font) > size[0]:
                    lines.append(line)
                    line = ""
                line += char
            lines.append(line)
        wrapped = "\n".join(lines)
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=1)
        width, height = box[2] - box[0], box[3] - box[1]
        if width <= size[0] and height <= size[1]:
            draw.multiline_text(
                ((size[0] - width) / 2 - box[0], (size[1] - height) / 2 - box[1]),
                wrapped,
                font=font,
                fill=color,
                spacing=1,
                align="center",
            )
            return image
    raise ValueError("Text does not fit; shorten it or provide a smaller font")


def preview_image(data, device, brightness=100):
    if device == "matrix":
        return matrix_image(data)  # Matrix brightness is already encoded.
    with Image.open(io.BytesIO(data)) as image:
        return fit_image(image, image.size, brightness=brightness)
