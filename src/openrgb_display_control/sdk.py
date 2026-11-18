# SPDX-License-Identifier: GPL-2.0-or-later
"""OpenRGB Matrix adapter. SDK failures never trigger a raw USB fallback."""

from .hardware import DisplayError
from .topology import ACTIVE, MATRIX_MAP, MATRIX_NAME, MATRIX_SIZE, WIRE_OFFSETS


def connect(host="127.0.0.1", port=6742):
    from openrgb import OpenRGBClient

    client = OpenRGBClient(host, port, "OpenRGB Display Control")
    client.comms.sock.settimeout(3)
    return client


class SDKMatrix:
    def __init__(self, client, device):
        self.client, self.device = client, device
        self._last = None
        self._identity = self.identity()

    def identity(self):
        return (
            self.device.name,
            self.device.data.metadata.serial,
            self.device.data.metadata.location,
        )

    def refresh(self):
        # SDK numeric IDs can be reused after a rescan. Check before every write,
        # including Off, rather than addressing whatever now occupies that ID.
        self.device.update()
        if self.identity() != self._identity:
            raise DisplayError("Matrix identity changed; stop and reopen the display")

    @classmethod
    def open(cls, host="127.0.0.1", port=6742, serial=None):
        client = connect(host, port)
        try:
            matches = [
                d
                for d in client.devices
                if d.name == MATRIX_NAME and (serial is None or d.data.metadata.serial == serial)
            ]
            if len(matches) != 1:
                raise DisplayError(
                    "Expected one native ASUS Matrix in OpenRGB. Install the "
                    "separate driver patch; use --serial for multiple devices."
                )
            device = matches[0]
            expected_map = [ACTIVE.index(wire) if wire else None for wire in MATRIX_MAP]
            if (
                len(device.leds) != 222
                or len(device.zones) != 1
                or (device.zones[0].mat_width, device.zones[0].mat_height) != MATRIX_SIZE
                or not {"Off", "Direct"}.issubset(m.name for m in device.modes)
                or [pixel for row in device.zones[0].matrix_map for pixel in row] != expected_map
                or not device.data.metadata.version.startswith("ALDR2-S452-")
            ):
                raise DisplayError("Native ASUS Matrix layout/modes do not match this renderer")
            return cls(client, device)
        except BaseException:
            client.disconnect()
            raise

    def off(self):
        self.refresh()
        self.device.set_mode("Off", save=False)
        self._last = None
        return {"backend": "sdk", "mode": "Off", "pixels": 222}

    def status(self):
        self.refresh()
        return {
            "backend": "sdk",
            "mode": self.device.modes[self.device.active_mode].name,
            "pixels": 222,
            "firmware": self.device.data.metadata.version,
        }

    def send(self, frame):
        from openrgb.utils import RGBColor

        if len(frame) != 768:
            raise ValueError("ASUS frames must contain exactly 768 bytes")
        self.refresh()
        direct = next(mode for mode in self.device.modes if mode.name == "Direct")
        if (
            frame == self._last
            and self.device.modes[self.device.active_mode].name == "Direct"
            and direct.brightness == 100
        ):
            return False
        if self.device.modes[self.device.active_mode].name != "Direct" or direct.brightness != 100:
            direct.brightness = 100
            self.device.set_mode(direct, save=False, force=True)
        colors = [
            RGBColor(frame[offset], frame[offset + 16], frame[offset + 32])
            for offset in WIRE_OFFSETS
        ]
        self.device.set_colors(colors, fast=True)
        self._last = frame
        return True

    def close(self):
        self.client.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
