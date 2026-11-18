# Draft: Initial commit for ASUS ROG Crosshair X670E Extreme AniMe Matrix

**Draft disclosure:** AI tools assisted this implementation and audit. Independent
human vetting has not been completed. OpenRGB's contribution policy generally
disallows AI-generated submissions; this draft does not claim compliance or
readiness for merge and may be closed under that policy.

The separate motherboard Matrix controller is currently missing native support.
This adds firmware-gated detection of `0B05:1A21` / `ALDR2-S452-*`, Off, per-pixel
Direct with brightness, a 222-LED stepped portrait matrix map, and the default
hardware-animation mode. It does not change Aura, cooling or LiveDash OLED.

USB transport and RGBController adapter are separate. The bulk interface is
claimed lazily after serial matching. HID acknowledgments and bulk uploads share
a transaction mutex; identical frames are skipped. A retained private libusb
context avoids generic detectors' global UsbDk-default conflict on Windows.
Off is queried back on the controller's own HID handle.

Validation:

* Owner previously confirmed full-session native Off, uniform red and Direct.
* Refactored transport: actual Windows frame upload/repeated frame/Off/readback,
  zero logged warnings in that exercise.
* All three native source files compiled with MSVC and GCC/Linux against the
  current upstream headers; transport regression executable passed on both.
* Linux physical-device behavior and a full fresh OpenRGB build are not claimed.

Outstanding before review/merge:

* A human author must fully understand/manually vet the implementation and resolve
  compliance with the project's AI submission policy. AI assistance was used.
* Confirm asymmetric physical landmarks for the inferred portrait map.
* Exercise first hotplug, a Windows reboot and, if available, Linux hardware.
* Open/link the device issue; the prepared issue draft is not a submitted issue.

No Python runtime, display GUI, GIF player, Corsair LCD support or Commander Core
fix is included. Protocol details and the explicit validation scope are in
`Documentation/ASUSAnimeMatrix.md`.

Checklist:

- [x] Dedicated unprotected source branch, independent of Commander Core
- [ ] New Device issue linked (not opened by this preparation)
- [x] Protocol documentation and support metadata present
- [x] Windows hardware transport exercised
- [ ] Linux physical hardware tested
- [x] Info/warning logging for detection/transfer failures
- [ ] Independent human review completed
- [ ] Asymmetric physical map confirmed
