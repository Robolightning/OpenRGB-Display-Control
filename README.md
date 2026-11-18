# OpenRGB Display Control

[![checks](https://github.com/Robolightning/OpenRGB-Display-Control/actions/workflows/checks.yml/badge.svg)](https://github.com/Robolightning/OpenRGB-Display-Control/actions/workflows/checks.yml)

Experimental releases: [GitHub Releases](https://github.com/Robolightning/OpenRGB-Display-Control/releases).

**Experimental, hardware-specific alpha.** A standalone Python/Qt companion for
ASUS ROG Crosshair X670E Extreme AniMe Matrix and Corsair H170i ELITE LCD.
This is an independent project, not an official OpenRGB component or plugin.

Display images, GIF/APNG, wrapped text, a clock, solid colors, or the average
color of a selected OpenRGB device. Animation frames are encoded once into a
bounded cache; playback follows source time and skips frames when an FPS limit
or slow transfer prevents sending every frame. Static images upload once.

## Supported hardware

| Display | Connection | Scope |
|---|---|---|
| ASUS X670E Extreme AniMe Matrix | `0B05:1A21`, `ALDR2-S452-*` | 222 RGB LEDs, portrait 7 × 36 with stepped edges; Off/Direct |
| Corsair H170i ELITE LCD (non-XT) | `1B1C:0C39`, HID interface 0 | 480 × 480 JPEG upload, brightness, black/backlight off |

Windows 11 hardware operation has been exercised on one installation. This
does **not** imply support for every ASUS Matrix, Corsair LCD, firmware, or OS.
Linux software checks are distinct from Linux hardware validation. See
[validation](docs/VALIDATION.md) for exactly what has and has not been checked.

The program does not control cooling, fan curves, pumps, Commander RGB ports,
Aura, or the separate LiveDash OLED. The Corsair RGB ring remains a separate
OpenRGB zone.

## Install from this repository

Python 3.11 or newer is required. A virtual environment is recommended.

```sh
python -m venv .venv
# Activate .venv using your platform's standard activation command.
python -m pip install ".[gui]"
openrgb-display-control-gui
```

CLI-only installation: `python -m pip install .`. For a known tested dependency
set, add `-c constraints-tested.txt` to the install command. Those constraints
record one tested environment; they are not a universal platform lock file.

### ASUS connection

The default Matrix backend is **OpenRGB SDK** at `127.0.0.1:6742`. OpenRGB must
contain the separately prepared native Matrix driver. The driver is not yet
accepted upstream; see [the upstream handoff](upstream/README.md).
The SDK device must expose the matching portrait map and 222 LEDs.

SDK errors fail explicitly. They never silently fall back to direct USB.

An optional direct backend is available with `pip install ".[usb]"` and
`--backend usb`. Use it only while no other application owns the Matrix's HID
or bulk interfaces. In particular, close OpenRGB or disable its Matrix detector
before using raw USB. The cooperating-process lock does not arbitrate against
Armoury Crate or arbitrary USB clients. No driver changes are made by this tool.

### Corsair connection

The LCD uses its own HID interface, separate from Commander Core. Close other
LCD players before use. Multiple matching displays require `--serial`.
On Linux, install system libusb/HID dependencies and suitable device permissions;
the included [udev example](docs/60-openrgb-display-control.rules) is narrow and
not installed automatically. Linux physical hardware operation is unverified.

## GUI

The standalone GUI has ASUS Matrix and Corsair LCD pages. Choose content, use
**Choose file…** for images/animations, then **Apply**. The preview shows the
first *applied, encoded* frame, including brightness and Matrix holes. It does
not show a second, approximate rendering of the input file. Rotation is clockwise.

The application opens without changing either display. Saved paths/settings
never autoplay. **Turn display off** cancels the current player, waits for its
device handle to be released, and then blanks that display. Normal window close
also attempts to blank displays used by that window; crashes or forced process
termination cannot guarantee blanking. Hardware errors are shown in the page.

RGB synchronization accepts a unique device name or its numeric SDK ID. Use
the `sources` command below to list IDs. A changed source identity stops mirroring.

## CLI examples

```sh
openrgb-display-control --device matrix status
openrgb-display-control --device matrix image animation.apng --fps 30 --once
openrgb-display-control --device matrix image portrait.png --fit cover --brightness 35
openrgb-display-control --device matrix clock --seconds 30 --off-on-exit
openrgb-display-control --device corsair text OpenRGB --brightness 35
openrgb-display-control --device corsair image animation.gif --seconds 20 --off-on-exit
openrgb-display-control sources
openrgb-display-control --device matrix sync 4 --seconds 20 --off-on-exit
openrgb-display-control --device all off
```

Place `--device`, `--backend`, `--host`, `--port`, `--serial` before the action;
content options can follow it. `--seconds 0` means unlimited animation/clock/
mirroring. A static image/text/color uploads once and exits unless a duration
was requested. `--off-on-exit` blanks on normal completion, cancellation or a
handled playback failure, including after a static upload. Ctrl+C/SIGTERM request
cooperative cancellation. `--once` plays one source cycle, independent of the FPS
cap. A source with more frames than can be transmitted has frames skipped.

Images larger than 16 megapixels, animations over 2000 frames, and encoded
caches over 64 MiB are rejected. Text wraps to fit; overly long text fails clearly.
For the portrait Matrix, the clock uses hours and minutes on separate lines.

## Development

```sh
python -m pip install ".[dev,gui]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m build
```

Tests use simulated transports and do not write to physical devices. CI covers
Windows/Linux and Python 3.11/3.14, including an offscreen GUI when installed.
Current remote results are available in [GitHub Actions](https://github.com/Robolightning/OpenRGB-Display-Control/actions).
The validation record distinguishes local checks from hosted CI and hardware observations.

Read the [architecture](docs/ARCHITECTURE.md), [protocol notes](docs/PROTOCOL.md),
[audit](docs/AUDIT.md), [release handoff](docs/RELEASE.md), and
[third-party notices](THIRD_PARTY_NOTICES.md).

## License and provenance

New project code is offered under `GPL-2.0-or-later`; see [LICENSE](LICENSE).
Protocol references and independent code/data provenance are documented in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). No vendor DLLs, USB captures,
private machine configuration, or bundled dependency binaries are shipped.

AI tools assisted this implementation and audit. This is not evidence of
independent human review. The upstream Matrix patch needs a human maintainer
who understands and manually vets it under OpenRGB's contribution policy.
