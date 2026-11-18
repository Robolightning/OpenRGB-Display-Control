# SPDX-License-Identifier: GPL-2.0-or-later
"""One cooperating writer per display family, including the legacy Qt bridge."""

import contextlib
import ctypes
import os
import tempfile
from pathlib import Path

from .hardware import DisplayError


@contextlib.contextmanager
def single_writer(device):
    if device not in ("matrix", "corsair"):
        raise ValueError("Unknown display family")
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateMutexW(None, True, "Local\\OpenRGBDisplayControl_" + device)
        error = ctypes.get_last_error()
        if not handle:
            raise ctypes.WinError(error)
        try:
            if error == 183:
                raise DisplayError(f"Another display-control process owns {device}")
            yield
        finally:
            kernel.CloseHandle(handle)
    else:
        import fcntl

        directory = Path(tempfile.gettempdir()) / f"openrgb-display-control-{os.getuid()}"
        directory.mkdir(mode=0o700, exist_ok=True)
        if directory.is_symlink() or directory.stat().st_uid != os.getuid():
            raise DisplayError("Unsafe display lock directory")
        descriptor = os.open(
            directory / f"{device}.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise DisplayError(f"Another display-control process owns {device}") from error
            yield
