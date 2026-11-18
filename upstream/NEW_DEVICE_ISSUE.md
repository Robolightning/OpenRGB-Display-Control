# [New Device] ASUS ROG Crosshair X670E Extreme AniMe Matrix

Preparation draft; no issue has been posted.

* Motherboard: ASUS ROG Crosshair X670E Extreme.
* Display: separate 222-pixel RGB AniMe Matrix on the I/O cover.
* Interface: USB `0B05:1A21`, HID interface 1 and bulk interface 0, endpoint `01`.
* Tested firmware: `ALDR2-S452-0106`.
* OS exercised on physical hardware: Windows 11 x64.
* Functions tested: hardware Off/readback, uniform RGB, software Direct frames,
  image/animation streaming. Exact asymmetric physical portrait landmarks remain
  unconfirmed. Linux hardware, S5/reboot and hotplug are untested.

Protocol notes: `Documentation/ASUSAnimeMatrix.md` in the separately prepared
driver patch. Firmware families sharing the PID are gated by prefix and not
assumed compatible. This is separate from Aura and LiveDash OLED.

Before posting, the human author should add the manufacturer's product link,
relevant vendor application screenshots and, if required, narrowly scoped USB
captures with personal/unique data reviewed. None of those attachments is
fabricated or silently uploaded by this preparation.
