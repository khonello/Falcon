"""The `screenshot` built-in: the primary screen, scaled down, as a PNG -- stdlib only.

Captured with GDI through ctypes (StretchBlt with HALFTONE does the scaling in one step) and encoded
as PNG with zlib, so there is no PowerShell (Windows Defender blocks the usual CopyFromScreen script
as malicious) and no imaging library to bundle. The width is capped at MAX_WIDTH and the picture is
made smaller again until it fits MAX_BYTES, the Engine's limit.

Run as the executor's built-in: prints `FALCON:summary` and `FALCON:image <path>`. When the Worker
runs as a Windows service this must run in the signed-in person's session (a helper), since a
service's own desktop is empty.
"""

from __future__ import annotations

import os
import struct
import sys
import time
import zlib

MAX_WIDTH = 1600
MAX_BYTES = 2 * 1024 * 1024 - 64 * 1024     # under the Engine's 2 MB, with room to spare


def png(width: int, height: int, rgb_rows: list[bytes]) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + r for r in rgb_rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def capture(width: int) -> tuple[int, int, int, int, list[bytes]]:
    """(screen width, screen height, width, height, RGB rows) of the primary screen at `width`."""
    import ctypes
    from ctypes import wintypes

    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    try:
        user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    w = min(width, sw)
    h = max(1, round(sh * w / sw))
    screen = user32.GetDC(None)
    mem = gdi32.CreateCompatibleDC(screen)
    bmp = gdi32.CreateCompatibleBitmap(screen, w, h)
    try:
        gdi32.SelectObject(mem, bmp)
        gdi32.SetStretchBltMode(mem, 4)                 # HALFTONE: averaged, not dropped pixels
        gdi32.SetBrushOrgEx(mem, 0, 0, None)
        if not gdi32.StretchBlt(mem, 0, 0, w, h, screen, 0, 0, sw, sh, 0x00CC0020):   # SRCCOPY
            raise OSError("StretchBlt failed (no desktop in this session?)")

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                        ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                        ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                        ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

        info = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)  # top-down
        buf = ctypes.create_string_buffer(w * h * 4)
        if gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(info), 0) != h:
            raise OSError("GetDIBits failed")
    finally:
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem)
        user32.ReleaseDC(None, screen)
    bgra = buf.raw
    rows = []
    for y in range(h):
        line = bgra[y * w * 4:(y + 1) * w * 4]
        rgb = bytearray(w * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = line[2::4], line[1::4], line[0::4]
        rows.append(bytes(rgb))
    return sw, sh, w, h, rows


def main() -> int:
    if sys.platform != "win32":
        print("screenshot: unsupported on this platform in v1", file=sys.stderr)
        return 1
    width = MAX_WIDTH
    while True:
        sw, sh, w, h, rows = capture(width)
        data = png(w, h, rows)
        if len(data) <= MAX_BYTES or w <= 320:
            break
        width = int(w * 0.75)
    out = os.path.join(os.environ.get("TEMP", "."), f"falcon-shot-{time.strftime('%Y%m%d%H%M%S')}.png")
    with open(out, "wb") as f:
        f.write(data)
    print(f"FALCON:summary screen {sw}x{sh} · picture {w}x{h}, {len(data) // 1024} KB")
    print(f"FALCON:image {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
