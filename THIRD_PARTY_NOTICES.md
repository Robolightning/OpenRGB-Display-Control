# Third-party notices and provenance

This project was extracted from a local OpenRGB display-control experiment.
The new Python/Qt code and proposed native driver are provided under
GPL-2.0-or-later. AI assistance was used; independent human review is outstanding.
No formal clean-room certification or legal clearance is asserted.

## Protocol/data references

* [Polylux](https://github.com/vladulus/polylux): MIT. Studied the ASUS
  HID/bulk framing, stepped 222-pixel panel topology and pinned byte positions.
  The portrait ordering was cross-checked against this reference and an owner
  photo. Its exact MIT notice is retained in
  [third_party_licenses/polylux.txt](third_party_licenses/polylux.txt).
* [corsair_lcd_tool](https://github.com/UDPSendToFailed/corsair_lcd_tool): consulted
  as a Corsair JPEG packet-format reference. No source files or assets from that
  repository are distributed here. Its repository did not include a license file
  in the inspected checkout; it is not treated as licensed code for reuse.
* [OpenLinkHub](https://github.com/jurkovic-nikola/OpenLinkHub/blob/main/src/devices/cc/cc.go):
  consulted for the Corsair brightness command/report layout. No Go source is
  distributed or translated line-for-line into this repository.
* [OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB): GPL-2.0-or-later source
  headers/protocol are used by the separately proposed driver. The companion
  communicates with its SDK via openrgb-python. The core patch remains separate
  and does not contain the Commander Core fix or the custom GUI.

The original sparse HAL wire IDs were inspected locally in the installed ASUS
HAL. The repository contains the numeric wire-coordinate data and an independently
written frame packer; it contains no ASUS DLL, disassembly, executable, artwork,
or captured vendor animation. Physical portrait landmark ordering remains an
explicit validation limitation.

## Dependencies

Dependencies are installed from their own packages, not vendored in releases.
Their own notices/licenses continue to apply (Pillow, hidapi, openrgb-python,
optional PySide6 Essentials, PyUSB and libusb). This project's license statement
does not relicense them. Build wheels/sdists contain only this project's sources
and documented handoff material, not dependency binaries.
