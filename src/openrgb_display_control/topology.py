# SPDX-License-Identifier: GPL-2.0-or-later
"""Portrait X670E Extreme topology and hardware frame layout.

Wire IDs are retained from the locally inspected HAL table. Portrait placement
is inferred from the owner's photo and matching 222-pixel layout; the exact
asymmetric physical landmark pattern has not yet been confirmed by the owner.
"""

import json
from importlib.resources import files

MATRIX_SIZE = (7, 36)
MATRIX_BYTES = 768
MATRIX_NAME = "ASUS ROG Crosshair X670E Extreme AniMe Matrix"
MATRIX_MAP = tuple(json.loads(files(__package__).joinpath("matrix_map.json").read_text()))
ACTIVE = tuple(sorted(set(MATRIX_MAP) - {0}))


def red_offset(wire: int) -> int:
    """One-based wire ID -> R byte offset; G/B follow at +16/+32."""
    if wire not in ACTIVE:
        raise ValueError("Inactive Matrix wire ID")
    index = wire - 1
    slot = index if index < 15 else 16 + (index - 15) // 14 * 16 + (index - 15) % 14
    return slot // 16 * 48 + slot % 16


PIXELS = tuple(
    (index % 7, index // 7, red_offset(wire)) for index, wire in enumerate(MATRIX_MAP) if wire
)
WIRE_OFFSETS = tuple(red_offset(wire) for wire in ACTIVE)

if (
    len(MATRIX_MAP) != 252
    or ACTIVE != tuple(w for w in range(1, 226) if w not in (213, 221, 225))
    or len(PIXELS) != 222
):
    raise ValueError("Invalid bundled Matrix topology")
