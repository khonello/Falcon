"""What a file looks like to the OS besides its content: size, last write, attributes, who may open it, its identity.

The OS reports "something about this file changed" for a content edit, a read-only flag, and a permissions change
alike. Comparing two looks tells them apart (watcher.py): the size or last write changed -> content; the attributes
changed -> read-only / hidden / archive flipped; the permissions fingerprint changed -> who may open it or who owns it.

  * attributes    Windows file attribute flags (st_file_attributes); elsewhere the file mode
  * security      Windows: a hash of the file's owner, group and access list, read with GetFileSecurityW (ctypes);
                  elsewhere: mode, owner and group. None when it could not be read.
  * identity      the file's own id (Windows file index / inode), which survives a rename or move -- what lets the polling
                  fallback tell a move from a delete plus a create
"""

from __future__ import annotations

import hashlib
import os
import sys
from typing import NamedTuple

OWNER_GROUP_DACL = 0x1 | 0x2 | 0x4          # OWNER_SECURITY_INFORMATION | GROUP_ | DACL_


class Meta(NamedTuple):
    size: int
    mtime_ns: int
    attrs: int
    security: str | None
    identity: int


def _security_win(path: str) -> str | None:
    import ctypes
    from ctypes import wintypes

    adv = ctypes.windll.advapi32
    adv.GetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                     ctypes.POINTER(wintypes.DWORD)]
    adv.GetFileSecurityW.restype = wintypes.BOOL
    needed = wintypes.DWORD(0)
    adv.GetFileSecurityW(path, OWNER_GROUP_DACL, None, 0, ctypes.byref(needed))    # the first call says how much room
    if needed.value == 0:
        return None
    buf = ctypes.create_string_buffer(needed.value)
    if not adv.GetFileSecurityW(path, OWNER_GROUP_DACL, buf, needed.value, ctypes.byref(needed)):
        return None
    return hashlib.sha1(buf.raw[:needed.value]).hexdigest()


def meta(path: str) -> Meta | None:
    """The file's metadata now, or None if it cannot be read (gone, or no access)."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    if sys.platform == "win32":
        attrs = int(getattr(st, "st_file_attributes", 0))
        try:
            security = _security_win(path)
        except OSError:
            security = None
    else:
        attrs = int(st.st_mode)
        security = f"{st.st_mode}:{st.st_uid}:{st.st_gid}"
    return Meta(st.st_size, st.st_mtime_ns, attrs, security, st.st_ino)


FILE_ATTRIBUTE_READONLY, FILE_ATTRIBUTE_HIDDEN, FILE_ATTRIBUTE_SYSTEM = 0x1, 0x2, 0x4


def attr_detail(before: int, after: int, *, windows: bool | None = None) -> dict[str, bool]:
    """Which attributes an `attrib` change was: hidden, system, read-only -- before and after, so "made hidden" can be told from "made visible" and from the rest.
    Only Windows has these flags in the attribute word; elsewhere nothing is claimed."""
    if not (sys.platform == "win32" if windows is None else windows):
        return {}
    return {"hidden": bool(after & FILE_ATTRIBUTE_HIDDEN), "was_hidden": bool(before & FILE_ATTRIBUTE_HIDDEN),
            "system": bool(after & FILE_ATTRIBUTE_SYSTEM), "was_system": bool(before & FILE_ATTRIBUTE_SYSTEM), "read_only": bool(after & FILE_ATTRIBUTE_READONLY)}


def changes(before: Meta, after: Meta) -> list[str]:
    """Which kinds of change turn `before` into `after`: 'modify' (content), 'attrib', 'security'."""
    out = []
    if (before.size, before.mtime_ns) != (after.size, after.mtime_ns):
        out.append("modify")
    if before.attrs != after.attrs:
        out.append("attrib")
    if before.security is not None and after.security is not None and before.security != after.security:
        out.append("security")
    return out
