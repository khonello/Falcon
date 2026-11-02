"""A file made into a PDF with nothing but the standard library: plain text (txt, md, csv, log), and JPEG photos, which a PDF carries as they
are. Anything else (a Word or Excel file, a PNG) is not converted here: doing it honestly needs Office or LibreOffice on the machine, so the
flow step says the format is not supported and the Engine shows its suggestion. Used by the Convert to PDF step (worker_client/flowsync.py).
"""

from __future__ import annotations

TEXT = ("txt", "md", "csv", "log")
JPEG = ("jpg", "jpeg")
A4 = (595, 842)                       # points
MARGIN = 50
FONT_SIZE, LEADING = 9, 11
COLUMNS = int((A4[0] - 2 * MARGIN) / (FONT_SIZE * 0.6))      # Courier is 0.6 em wide
ROWS = int((A4[1] - 2 * MARGIN) / LEADING)
MAX_PAGES = 2000                      # a 20 MB log is not a book anyone opens: past this the PDF says where it stopped


class NotConvertible(Exception):
    """This content cannot be made into a PDF here (a damaged JPEG, a format this module does not read)."""


def convertible(ext: str) -> bool:
    return ext in TEXT or ext in JPEG


def to_pdf(data: bytes, ext: str) -> bytes:
    if ext in TEXT:
        return _text_pdf(data)
    if ext in JPEG:
        return _jpeg_pdf(data)
    raise NotConvertible(ext)


# --- writing ---------------------------------------------------------------------------------------------

def _document(objects: list[bytes]) -> bytes:
    """objects[0] is the catalog. Each is the body of `n 0 obj`, numbered from 1."""
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


def _stream(head: bytes, body: bytes) -> bytes:
    return b"<< " + head + b" /Length %d >>\nstream\n" % len(body) + body + b"\nendstream"


def _pages(page_bodies: list[tuple[bytes, bytes]], width: float, height: float) -> bytes:
    """page_bodies: (resources, content stream). Catalog 1, pages 2, then per page: the page and its content."""
    objects: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>", b""]
    kids = []
    for resources, content in page_bodies:
        page_no = len(objects) + 1
        kids.append(b"%d 0 R" % page_no)
        objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %s %s] /Resources %s /Contents %d 0 R >>"
                       % (_num(width), _num(height), resources, page_no + 1))
        objects.append(_stream(b"", content))
    objects[1] = b"<< /Type /Pages /Kids [" + b" ".join(kids) + b"] /Count %d >>" % len(kids)
    return objects                                                               # type: ignore[return-value]


def _num(x: float) -> bytes:
    return (b"%d" % x) if float(x).is_integer() else (b"%.2f" % x)


# --- text --------------------------------------------------------------------------------------------------

def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _escape(line: str) -> bytes:
    raw = line.encode("cp1252", errors="replace")                 # the standard fonts speak WinAnsi; what they cannot show becomes "?"
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _wrap(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4).split("\n"):
        while len(raw) > COLUMNS:
            lines.append(raw[:COLUMNS])
            raw = raw[COLUMNS:]
        lines.append(raw)
    return lines


def _text_pdf(data: bytes) -> bytes:
    lines = _wrap(_decode(data))
    pages = [lines[i:i + ROWS] for i in range(0, max(len(lines), 1), ROWS)] or [[]]
    if len(pages) > MAX_PAGES:
        pages = pages[:MAX_PAGES]
        pages[-1] = pages[-1][:-1] + [f"[cut here: the file goes on past {MAX_PAGES} pages]"]
    font = b"<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >> >> >>"
    bodies = []
    for page in pages:
        content = b"BT /F1 %d Tf %d TL %d %d Td\n" % (FONT_SIZE, LEADING, MARGIN, A4[1] - MARGIN - FONT_SIZE)
        content += b"".join(b"(" + _escape(line) + b") Tj T*\n" for line in page) + b"ET"
        bodies.append((font, content))
    return _document(_pages(bodies, *A4))


# --- a JPEG, carried as it is ------------------------------------------------------------------------------

def _jpeg_size(data: bytes) -> tuple[int, int, int]:
    """(width, height, components) from the frame header."""
    if data[:2] != b"\xff\xd8":
        raise NotConvertible("not a JPEG")
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            raise NotConvertible("damaged JPEG")
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height = int.from_bytes(data[i + 5:i + 7], "big")
            width = int.from_bytes(data[i + 7:i + 9], "big")
            return width, height, data[i + 9]
        i += 2 + length
    raise NotConvertible("damaged JPEG")


def _jpeg_pdf(data: bytes) -> bytes:
    width, height, comps = _jpeg_size(data)
    if not width or not height or comps not in (1, 3, 4):
        raise NotConvertible("unsupported JPEG")
    space = {1: b"/DeviceGray", 3: b"/DeviceRGB", 4: b"/DeviceCMYK"}[comps]
    # the photo fills an A4 page inside the margins, the way it is turned, keeping its shape
    portrait = height >= width
    page_w, page_h = A4 if portrait else (A4[1], A4[0])
    scale = min((page_w - 2 * MARGIN) / width, (page_h - 2 * MARGIN) / height)
    w, h = width * scale, height * scale
    x, y = (page_w - w) / 2, (page_h - h) / 2
    objects = _pages([(b"<< /XObject << /Im1 5 0 R >> >>", b"q %s 0 0 %s %s %s cm /Im1 Do Q" % (_num(round(w, 2)), _num(round(h, 2)), _num(round(x, 2)), _num(round(y, 2))))],
                     page_w, page_h)
    decode = b" /Decode [1 0 1 0 1 0 1 0]" if comps == 4 else b""   # Adobe's CMYK JPEGs are stored inverted
    objects.append(_stream(b"/Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s /BitsPerComponent 8 /Filter /DCTDecode%s"
                           % (width, height, space, decode), data))
    return _document(objects)
