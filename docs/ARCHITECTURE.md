# Architecture

`control.Request` is the common request model used by the CLI and Qt pages.
`control.execute` validates and prepares media before opening hardware. The Qt
worker runs this same service on a cancellable thread; it never creates a shell,
an interpreter redirector or a child playback process.

* `topology.py` + `matrix_map.json`: stepped portrait coordinates, stable wire IDs.
* `rendering.py`: EXIF/alpha handling, fit/rotation, text fitting, bounded caches,
  hardware encoders, and preview decoding of the exact encoded data.
* `playback.py`: absolute source timeline, direct seek after a stall, interruptible
  waits, independent FPS cap. No backlog and no idle playback service.
* `sdk.py`: native Matrix driver adapter. SDK errors propagate; raw USB is not a
  recovery path. Native brightness is set to 100 because content brightness is
  already encoded. Device identity is queried before every write so reused SDK
  IDs cannot redirect output. One SDK color update is sent per changed frame.
* `hardware.py`: explicit Matrix HID/bulk backend and separate Corsair LCD HID.
* `locking.py`: Windows mutex/POSIX advisory lock, one writer per display family.
* `gui.py`: optional Qt interface; settings in the platform user configuration
  location, no autoplay, cancellation/replacement serialized by worker completion.

The software lock coordinates instances of this application and the previous
custom Windows Qt bridge. It cannot exclude unrelated RGB applications.
Static content releases the lock after upload. Do not run competing renderers.

The companion is intentionally independent from the custom OpenRGB GUI. The old
header-only C++ display pages and startup scripts are not part of the publishable
repository. A future native OpenRGB plugin can consume this protocol/renderer
design, but no plugin binary/API compatibility is claimed by this release.

The core Matrix driver is separately owned by the OpenRGB worktree/patch. It has
no dependency on this Python project. Its HID acknowledgments and bulk transfers
share a transaction mutex. It retains a private libusb context created during
early HID detection to avoid the legacy global UsbDk-default conflict on Windows.
