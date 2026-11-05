"""Reading a person's file without getting in their way.

On Windows a plain `open()` does not share delete access, so while it is held the person cannot rename, move or delete their own file: Windows tells them it is in use.
The Worker reads people's files all day (hashing what changed, sending what a flow carries), and a big file takes seconds. So it asks Windows to let them carry on: what it
has open keeps reading what it opened, whatever they do to the name.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import BinaryIO

GENERIC_READ = 0x80000000
SHARE_EVERYTHING = 0x1 | 0x2 | 0x4          # read, write, delete
OPEN_EXISTING = 3
SEQUENTIAL_SCAN = 0x08000000


def open_shared(path: Path | str) -> BinaryIO:
    """A file open for reading in binary that never stops anyone renaming, moving, changing or deleting it. Raises what `open()` raises."""
    if sys.platform != "win32":
        return open(path, "rb")                 # elsewhere an open file was never in the way
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.restype = wintypes.HANDLE
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    handle = create(str(path), GENERIC_READ, SHARE_EVERYTHING, None, OPEN_EXISTING, SEQUENTIAL_SCAN, None)
    if handle in (None, wintypes.HANDLE(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    return os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDONLY), "rb")
