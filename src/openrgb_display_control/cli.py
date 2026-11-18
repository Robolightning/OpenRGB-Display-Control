# SPDX-License-Identifier: GPL-2.0-or-later
"""Images, GIF/APNG, text, clocks and RGB mirroring for two display families."""

import argparse
import json
import signal
from threading import Event

from . import __version__, sdk
from .control import Request, execute


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--version", action="version", version=__version__)
    result.add_argument("--device", choices=("matrix", "corsair", "all"), default="all")
    result.add_argument(
        "--backend",
        choices=("sdk", "usb"),
        default="sdk",
        help="Matrix backend; usb is explicit and requires exclusive USB ownership",
    )
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--port", type=int, default=6742)
    result.add_argument("--serial", help="Select one physical display (exact serial)")
    result.add_argument(
        "action", choices=("off", "status", "image", "text", "clock", "solid", "sync", "sources")
    )
    result.add_argument("value", nargs="?", default="")
    result.add_argument("--brightness", type=int, default=50)
    result.add_argument("--fps", type=float, default=30)
    result.add_argument("--seconds", type=float, default=0)
    result.add_argument(
        "--rotation", type=int, choices=(0, 90, 180, 270), default=0, help="Clockwise rotation"
    )
    result.add_argument("--fit", choices=("contain", "cover", "stretch"), default="contain")
    result.add_argument("--font", help="Optional local TrueType/OpenType font")
    result.add_argument("--once", action="store_true", help="Play one source animation cycle")
    result.add_argument("--off-on-exit", action="store_true")
    return result


def main(argv=None):
    arguments = parser()
    args = arguments.parse_args(argv)
    if args.serial and args.device == "all":
        arguments.error("--serial requires a single --device")
    if args.device == "all" and args.action not in ("off", "status", "sources"):
        arguments.error("Choose a single --device for content")
    stop = Event()
    previous = {}
    for name in (signal.SIGINT, signal.SIGTERM):
        previous[name] = signal.signal(name, lambda *_: stop.set())
    results, failures = {}, 0
    try:
        if args.action == "sources":
            client = sdk.connect(args.host, args.port)
            try:
                print(json.dumps([{"id": d.id, "name": d.name} for d in client.devices], indent=2))
            finally:
                client.disconnect()
            return 0
        options = vars(args).copy()
        targets = ("matrix", "corsair") if options.pop("device") == "all" else (args.device,)
        for target in targets:
            if stop.is_set():
                break
            request = Request(device=target, **options)
            try:
                request.validate()
                results[target] = execute(
                    request,
                    stop,
                    lambda event: print(
                        json.dumps({k: v for k, v in event.items() if k != "preview"}), flush=True
                    ),
                )
            except (Exception, KeyboardInterrupt) as error:
                failures += 1
                results[target] = {"error": f"{type(error).__name__}: {error}"}
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 130 if stop.is_set() else int(bool(failures))
    except Exception as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}))
        return 1
    finally:
        for name, handler in previous.items():
            signal.signal(name, handler)
