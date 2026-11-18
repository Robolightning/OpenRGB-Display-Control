# SPDX-License-Identifier: GPL-2.0-or-later
"""Display-only USB transports. No Aura, Commander, fan or pump writes."""

import contextlib
import os
import platform
import struct
import threading
import time
from pathlib import Path


class DisplayError(RuntimeError):
    pass


class HidDisplay:
    def __init__(self, vid, pid, interface, serial=None):
        import hid

        matches = [
            info
            for info in hid.enumerate(vid, pid)
            if info["interface_number"] == interface
            and (serial is None or info["serial_number"] == serial)
        ]
        if len(matches) != 1:
            raise DisplayError(
                f"Expected one {vid:04X}:{pid:04X} interface {interface}; "
                f"found {len(matches)}. Use --serial when needed."
            )
        self.info = matches[0]
        self.lock = threading.RLock()
        self.dev = hid.device()
        try:
            self.dev.open_path(self.info["path"])
        except BaseException:
            self.close()
            raise

    def write(self, packet):
        count = self.dev.write(packet)
        if count != len(packet):
            raise DisplayError(f"Incomplete HID write: {count}/{len(packet)}")

    def close(self):
        if self.dev is not None:
            self.dev.close()
            self.dev = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def matrix_packet(opcode, payload=b""):
    if len(payload) > 63:
        raise ValueError("ASUS command payload exceeds 63 bytes")
    return (bytes([0xEC, opcode]) + payload).ljust(65, b"\0")


class MatrixUSB(HidDisplay):
    """Explicit opt-in backend: OpenRGB must not own this physical device."""

    def __init__(self, serial=None):
        self.usb = None
        self._last = None
        self._mode = None
        super().__init__(0x0B05, 0x1A21, 1, serial)
        try:
            self.firmware = self.command(0x82, reply=0x02)[3:].split(b"\0")[0].decode("ascii")
            if not self.firmware.startswith("ALDR2-S452-"):
                raise DisplayError("Unsupported ASUS firmware; no display mode was changed")
        except BaseException:
            self.close()
            raise

    def command(self, opcode, payload=b"", reply=None):
        expected = opcode & 0x7F if reply is None else reply
        with self.lock:
            self.write(matrix_packet(opcode, payload))
            deadline = time.monotonic() + 0.5
            while time.monotonic() < deadline:
                data = bytes(self.dev.read(65, 25))
                if len(data) >= 3 and data[:2] == bytes([0xEC, expected]):
                    if opcode in (0x42, 0x7F) and data[2] != 0:
                        raise DisplayError(f"ASUS command {opcode:02X} rejected")
                    return data
            raise DisplayError(f"No matching ASUS reply {expected:02X}")

    def status(self):
        data = self.command(0xC1)
        if len(data) <= 10:
            raise DisplayError("Short ASUS status reply")
        self._mode = data[10]
        return {
            "backend": "usb",
            "firmware": self.firmware,
            "mode": self._mode,
            "serial": self.info["serial_number"],
        }

    def set_mode(self, mode):
        if mode not in (0, 1, 2):
            raise ValueError("Invalid ASUS player mode")
        self.command(0x42, bytes([mode, 0, 0]))
        self._mode, self._last = mode, None

    def off(self):
        self.set_mode(0)
        status = self.status()
        if status["mode"] != 0:
            raise DisplayError("ASUS did not retain off mode")
        return status

    def _open_bulk(self):
        if self.usb is not None:
            return
        import usb.backend.libusb1
        import usb.core
        import usb.util

        backend = usb.backend.libusb1.get_backend()
        if backend is None and os.name == "nt":
            import libusb

            architecture = (
                "arm64"
                if platform.machine().lower() in ("arm64", "aarch64")
                else "x86_64"
                if struct.calcsize("P") == 8
                else "x86"
            )
            dll = (
                Path(libusb.__file__).parent / "_platform/windows" / architecture / "libusb-1.0.dll"
            )
            if dll.is_file():
                backend = usb.backend.libusb1.get_backend(find_library=lambda _: str(dll))
        if backend is None:
            raise DisplayError("libusb backend unavailable; install the usb extra/system libusb")
        matches = []
        for device in usb.core.find(
            find_all=True, idVendor=0x0B05, idProduct=0x1A21, backend=backend
        ):
            if device.serial_number == self.info["serial_number"]:
                matches.append(device)
            else:
                usb.util.dispose_resources(device)
        if len(matches) != 1:
            for device in matches:
                usb.util.dispose_resources(device)
            raise DisplayError("Matching ASUS bulk interface not found")
        try:
            usb.util.claim_interface(matches[0], 0)
        except BaseException:
            usb.util.dispose_resources(matches[0])
            raise
        self.usb = matches[0]

    def send(self, frame):
        if len(frame) != 768:
            raise ValueError("ASUS frames must contain exactly 768 bytes")
        with self.lock:
            if self._mode == 1 and frame == self._last:
                return False
            self._open_bulk()
            if self._mode != 1:
                self.set_mode(1)
            self.command(0x7F, bytes([4, 0, 3]))
            count = self.usb.write(0x01, frame, timeout=500)
            if count != 768:
                raise DisplayError(f"Incomplete ASUS bulk write: {count}/768")
            self._last = frame
            return True

    def close(self):
        if self.usb is not None:
            import usb.util

            with contextlib.suppress(Exception):
                usb.util.release_interface(self.usb, 0)
            usb.util.dispose_resources(self.usb)
            self.usb = None
        super().close()


def corsair_packets(jpeg):
    if not jpeg or len(jpeg) > 1024 * 1024:
        raise ValueError("JPEG must contain 1..1048576 bytes")
    view = memoryview(jpeg)
    for part, offset in enumerate(range(0, len(view), 1016)):
        chunk = view[offset : offset + 1016]
        header = struct.pack(
            "<BBBBHH", 2, 5, 0x40, int(offset + len(chunk) == len(view)), part, len(chunk)
        )
        yield header + bytes(chunk) + bytes(1016 - len(chunk))


class CorsairLCD(HidDisplay):
    def __init__(self, serial=None):
        super().__init__(0x1B1C, 0x0C39, 0, serial)
        self._last = None

    def brightness(self, percent):
        if not 0 <= percent <= 100:
            raise ValueError("Brightness must be 0..100 percent")
        packet = bytes([3, 0x0B, round(percent * 64 / 100), 1])
        with self.lock:
            count = self.dev.send_feature_report(packet)
            if count != len(packet):
                raise DisplayError(f"Incomplete Corsair brightness report: {count}/4")

    def send(self, jpeg):
        with self.lock:
            if jpeg == self._last:
                return False
            for packet in corsair_packets(jpeg):
                self.write(packet)
            self._last = jpeg
            return True

    def off(self):
        from PIL import Image

        from .rendering import jpeg_frame

        try:
            self._last = None
            self.send(jpeg_frame(Image.new("RGB", (480, 480))))
        finally:
            self.brightness(0)  # Also attempt backlight-off after a failed black upload.
        return {"backend": "usb", "black_frame_sent": True, "backlight_percent": 0}

    def status(self):
        return {
            "backend": "usb",
            "usb": "1B1C:0C39",
            "serial": self.info["serial_number"],
            "note": "Framebuffer/backlight readback is unavailable",
        }
