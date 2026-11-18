# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared application service. GUI and CLI use identical preparation/playback."""

import math
import time
from dataclasses import dataclass
from datetime import datetime
from threading import Event

from PIL import Image

from . import sdk
from .hardware import CorsairLCD, DisplayError, MatrixUSB
from .locking import single_writer
from .playback import play
from .rendering import Frame, encode_image, image_frames, text_image
from .topology import MATRIX_SIZE


@dataclass(frozen=True)
class Request:
    device: str
    action: str
    value: str = ""
    backend: str = "sdk"
    host: str = "127.0.0.1"
    port: int = 6742
    serial: str | None = None
    brightness: int = 50
    rotation: int = 0
    fit: str = "contain"
    fps: float = 30
    seconds: float = 0
    once: bool = False
    off_on_exit: bool = False
    font: str | None = None

    def validate(self):
        if self.device not in ("matrix", "corsair"):
            raise ValueError("Choose matrix or corsair")
        if self.action not in ("off", "status", "image", "text", "clock", "solid", "sync"):
            raise ValueError("Invalid action")
        if self.backend not in ("sdk", "usb") or not 1 <= self.port <= 65535:
            raise ValueError("Invalid backend or port")
        if not math.isfinite(self.fps) or not 1 <= self.fps <= 60:
            raise ValueError("FPS must be finite and in 1..60")
        if not math.isfinite(self.seconds) or self.seconds < 0:
            raise ValueError("Seconds must be finite and non-negative")
        if (
            not 0 <= self.brightness <= 100
            or self.rotation not in (0, 90, 180, 270)
            or self.fit not in ("contain", "cover", "stretch")
        ):
            raise ValueError("Invalid brightness, rotation or fit")
        if self.action in ("image", "text", "solid", "sync") and not self.value:
            raise ValueError("The selected action needs a value")


def prepare(request, stop):
    """Validate/decode before opening hardware or changing LCD brightness."""
    if request.action == "image":
        return image_frames(
            request.value, request.device, request.fit, request.rotation, request.brightness, stop
        )
    size = MATRIX_SIZE if request.device == "matrix" else (480, 480)
    if request.rotation in (90, 270):
        size = size[::-1]
    if request.action == "text":
        image = text_image(request.value, size, font_path=request.font)
    elif request.action == "solid":
        image = Image.new("RGB", (1, 1), request.value)
        return [Frame(encode_image(image, request.device, request.brightness, fit="stretch"), 1)]
    else:
        return None
    return [Frame(encode_image(image, request.device, request.brightness, request.rotation), 1)]


def open_display(request):
    if request.device == "corsair":
        return CorsairLCD(request.serial)
    if request.backend == "usb":
        return MatrixUSB(request.serial)
    # No exception handler here: failing SDK access must not claim a USB handle.
    return sdk.SDKMatrix.open(request.host, request.port, request.serial)


def execute(request: Request, stop=None, emit=lambda event: None):
    request.validate()
    stop = stop if stop is not None else Event()
    frames = prepare(request, stop)
    if stop.is_set():
        return {"cancelled": True}
    with single_writer(request.device), open_display(request) as display:
        if request.action == "off":
            return display.off()
        if request.action == "status":
            return display.status()
        try:
            if request.device == "corsair":
                display.brightness(request.brightness)
            if frames:
                emit({"event": "ready", "frames": len(frames), "preview": frames[0].data})
                if len(frames) == 1:
                    display.send(frames[0].data)
                    if request.seconds:
                        stop.wait(request.seconds)
                    return {"frames": 1, "bytes": len(frames[0].data), "cancelled": stop.is_set()}
                return play(
                    display,
                    frames,
                    seconds=request.seconds,
                    fps=request.fps,
                    once=request.once,
                    stop=stop,
                )
            if request.action == "clock":
                return run_clock(request, display, stop, emit)
            return run_sync(request, display, stop, emit)
        finally:
            if request.off_on_exit:
                display.off()


def run_clock(request, display, stop, emit):
    size = MATRIX_SIZE if request.device == "matrix" else (480, 480)
    if request.rotation in (90, 270):
        size = size[::-1]
    end = time.monotonic() + request.seconds if request.seconds else math.inf
    last_minute = None
    while not stop.is_set() and time.monotonic() < end:
        now = datetime.now()
        minute = now.strftime("%H:%M")
        if minute != last_minute:
            text = (
                now.strftime("%H\n%M")
                if request.device == "matrix" and request.rotation in (0, 180)
                else minute
            )
            image = text_image(text, size, font_path=request.font)
            data = encode_image(image, request.device, request.brightness, request.rotation)
            display.send(data)
            emit({"event": "ready", "frames": 1, "preview": data})
            last_minute = minute
        stop.wait(min(1, max(0, end - time.monotonic())))
    return {"cancelled": stop.is_set()}


def run_sync(request, display, stop, emit):
    client = sdk.connect(request.host, request.port)
    try:
        # Identity includes the SDK ID. Reject duplicate names instead of mirroring
        # an arbitrary RAM module/controller. A numeric ID is also accepted.
        matches = [
            d for d in client.devices if str(d.id) == request.value or d.name == request.value
        ]
        if len(matches) != 1:
            raise DisplayError("RGB source is missing or ambiguous; use its numeric SDK ID")
        source = matches[0]
        identity = (source.name, source.data.metadata.serial, source.data.metadata.location)
        end = time.monotonic() + request.seconds if request.seconds else math.inf
        first = True
        while not stop.is_set() and time.monotonic() < end:
            started = time.monotonic()
            source.update()
            if (
                source.name,
                source.data.metadata.serial,
                source.data.metadata.location,
            ) != identity:
                raise DisplayError("RGB source identity changed; select the source again")
            if not source.colors:
                raise DisplayError("RGB source has no colors")
            color = tuple(
                round(sum(getattr(c, key) for c in source.colors) / len(source.colors))
                for key in ("red", "green", "blue")
            )
            data = encode_image(
                Image.new("RGB", (1, 1), color), request.device, request.brightness, fit="stretch"
            )
            display.send(data)
            if first:
                emit({"event": "ready", "frames": 1, "preview": data})
                first = False
            stop.wait(max(0, min(end, started + 1 / min(request.fps, 30)) - time.monotonic()))
    finally:
        client.disconnect()
    return {"cancelled": stop.is_set()}
