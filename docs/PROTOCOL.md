# Display protocols

## ASUS X670E Extreme Matrix

Gate: VID/PID `0B05:1A21`, HID interface 1, firmware prefix `ALDR2-S452-`.
Other device families sharing a PID must not receive this frame layout.

HID output reports are 65 bytes, zero padded, beginning with `EC opcode`.
Only matching replies are consumed; writes/read lengths and timeouts are checked.

| Command | Meaning / reply |
|---|---|
| `EC 82` | Firmware query; `EC 02 00 <ASCII firmware>` |
| `EC C1` | Player status; `EC 41`, byte 10 is mode |
| `EC 42 mode 00 00` | Mode 0=off, 1=software, 2=hardware; `EC 42 00` ack |
| `EC 7F 04 00 03` | Prepare one software frame; `EC 7F 00` ack |

Mode 2 restarts the hardware player on the tested firmware. It is **not** an
off/S5 setting. Mode 0 is queried back on the same HID handle. Bulk interface 0,
endpoint `01`, carries a 768-byte frame after the preparation acknowledgment.
The interface is serial-matched before it is claimed; no kernel-driver detach
or firmware persistence command is used.

The frame has 16 blocks × 48 bytes. Each block contains 16 R bytes, then 16 G,
then 16 B. The first block represents 15 wire positions, later blocks 14 each;
unused slots are zero. Active wire IDs are 1..225 excluding 213, 221, 225.
For a one-based wire `w`, let `i=w-1`:

```
slot = i                             if i < 15
slot = 16 + ((i-15)//14)*16 + (i-15)%14 otherwise
R = (slot//16)*48 + slot%16; G=R+16; B=R+32
```

Portrait rows contain `2, 4, 6`, then 26 full rows of 7, then `7,6,5,4,3,2,1`.
Only the 222 physical positions are sampled. The original HAL image-space table
was oblique and must not be treated as physical Cartesian screen coordinates.
The portrait physical landmark order is inferred and awaits asymmetric visual
confirmation on the owner's board. Uniform red does not prove image orientation.

## Corsair ELITE LCD

Gate: `1B1C:0C39`, HID interface 0. Tested device: H170i ELITE LCD, non-XT.
RGB ring/Commander `0C32` are different devices and receive no commands here.

Pillow prepares a 480 × 480 RGB JPEG once per frame. Reports are 1024 bytes:
an 8-byte little-endian `<BBBBHH>` header and up to 1016 JPEG bytes, zero padded.
Header: `02 05 40 end part_index_u16 data_length_u16`. `end=1` on the last report,
including when the JPEG ends on an exact 1016-byte boundary. Max JPEG size: 1 MiB.

Brightness feature report: `03 0B level 01`, with percent mapped to 0..64.
Off attempts a black JPEG upload and then brightness 0; backlight-off is still
attempted when black upload fails. There is no framebuffer/backlight readback in
this implementation. Reported successful writes are not proof of visible content.

References are linked in [third-party notices](../THIRD_PARTY_NOTICES.md).
