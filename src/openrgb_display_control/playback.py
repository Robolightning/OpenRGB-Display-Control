# SPDX-License-Identifier: GPL-2.0-or-later
"""Absolute-time playback: limit USB updates without slowing the source."""

import bisect
import math
import time
from itertools import accumulate
from threading import Event


def play(display, frames, *, seconds=0, fps=30, once=False, stop=None, clock=time.monotonic):
    if not frames or not math.isfinite(fps) or not 1 <= fps <= 60:
        raise ValueError("Playback needs frames and FPS in 1..60")
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Seconds must be finite and non-negative")
    if any(not math.isfinite(frame.duration) or frame.duration <= 0 for frame in frames):
        raise ValueError("Frame durations must be finite and positive")
    stop = stop if stop is not None else Event()
    boundaries = list(accumulate(frame.duration for frame in frames))
    cycle = boundaries[-1]
    started = clock()
    limit = min(seconds if seconds else math.inf, cycle if once else math.inf)
    sent = dropped = 0
    previous = -1
    while not stop.is_set():
        elapsed = clock() - started
        if elapsed >= limit:
            break
        iteration, within = divmod(elapsed, cycle)
        index = min(bisect.bisect_right(boundaries, within), len(frames) - 1)
        absolute = int(iteration) * len(frames) + index
        dropped += max(0, absolute - previous - 1)
        if absolute != previous:
            sent += int(display.send(frames[index].data))
        previous = absolute
        next_boundary = iteration * cycle + boundaries[index]
        deadline = min(limit, max(elapsed + 1 / fps, next_boundary))
        stop.wait(max(0, started + deadline - clock()))
    return {
        "frames_sent": sent,
        "source_frames_skipped": dropped,
        "elapsed_seconds": round(clock() - started, 3),
        "cancelled": stop.is_set(),
    }
