"""What a flow's Conversion steps are done with on this machine (engine/flow/steps.py has the tree).

  * Word, Excel, PowerPoint (and the OpenDocument kinds) to PDF, and a PDF to DOCX: Microsoft Office when it is installed (driven through
    PowerShell, as Windows itself allows), else LibreOffice run with no window (`soffice --headless --convert-to`). Neither is shipped with
    Falcon; `office_tool()` says which this machine has, and the Worker says so when it connects.
  * Images (PNG, JPG, BMP, GIF, TIFF) to JPG or PNG: Windows' own image library (System.Drawing), through PowerShell.
  * Text to PDF and JPEG to PDF: worker_client/pdf.py, nothing outside the standard library. Text to DOCX: written here.

Each takes and returns bytes; anything it cannot do raises Unconvertible, which the step turns into "copied as it is" or "left out".
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from worker_client import pdf

OFFICE_SECONDS = 180
IMAGE_SECONDS = 60
WORD = ("doc", "docx", "rtf", "odt")
EXCEL = ("xls", "xlsx", "ods")
POWERPOINT = ("ppt", "pptx", "odp")
IMAGES = ("jpg", "jpeg", "png", "bmp", "gif", "tif", "tiff")
TEXT = pdf.TEXT


class Unconvertible(Exception):
    """This file cannot be converted here: why, in a few words."""


# --- what this machine has -------------------------------------------------------------------------------------------------------

def _soffice() -> str | None:
    found = shutil.which("soffice")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            exe = Path(base) / "LibreOffice" / "program" / "soffice.exe"
            if exe.is_file():
                return str(exe)
    return None


def _office_app(prog_id: str) -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog_id + "\\CLSID"):
            return True
    except OSError:
        return False


@lru_cache(maxsize=1)
def office_tool() -> str | None:
    """'word' when Microsoft Office is installed, 'libreoffice' when LibreOffice is, else None."""
    if _office_app("Word.Application"):
        return "word"
    if _soffice():
        return "libreoffice"
    return None


# --- running a tool on a file ------------------------------------------------------------------------------------------------------

def _run(argv: list[str], seconds: int) -> None:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        done = subprocess.run(argv, capture_output=True, timeout=seconds, check=False, creationflags=flags)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Unconvertible(f"the converter did not finish ({exc.__class__.__name__})") from exc
    if done.returncode != 0:
        raise Unconvertible((done.stderr or done.stdout).decode("utf-8", "replace").strip()[-200:] or f"the converter stopped with {done.returncode}")


def _in_temp(data: bytes, ext: str, work: Path) -> Path:
    src = work / f"in.{ext}"
    src.write_bytes(data)
    return src


def _out(work: Path, ext: str) -> bytes:
    found = sorted(p for p in work.iterdir() if p.suffix.lower() == f".{ext}" and p.stem.startswith(("out", "in")))
    if not found or found[0].stat().st_size == 0:
        raise Unconvertible("the converter made nothing")
    return found[0].read_bytes()


PS_OFFICE = r"""
param([string]$App, [string]$In, [string]$Out, [string]$To)
$ErrorActionPreference = 'Stop'
if ($App -eq 'word') {
  $w = New-Object -ComObject Word.Application; $w.Visible = $false; $w.DisplayAlerts = 0
  try { $d = $w.Documents.Open($In, $false, $true); $fmt = if ($To -eq 'pdf') { 17 } else { 16 }; $d.SaveAs2($Out, $fmt); $d.Close(0) } finally { $w.Quit() }
} elseif ($App -eq 'excel') {
  $x = New-Object -ComObject Excel.Application; $x.Visible = $false; $x.DisplayAlerts = $false
  try { $b = $x.Workbooks.Open($In, 0, $true); $b.ExportAsFixedFormat(0, $Out); $b.Close($false) } finally { $x.Quit() }
} else {
  $p = New-Object -ComObject PowerPoint.Application
  try { $s = $p.Presentations.Open($In, $true, $false, $false); $s.SaveAs($Out, 32); $s.Close() } finally { $p.Quit() }
}
"""

PS_IMAGE = r"""
param([string]$In, [string]$Out, [string]$To, [int]$Quality)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile($In)
try {
  if ($To -eq 'png') { $img.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png) }
  else {
    $bmp = New-Object System.Drawing.Bitmap $img.Width, $img.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp); $g.Clear([System.Drawing.Color]::White); $g.DrawImage($img, 0, 0, $img.Width, $img.Height); $g.Dispose()
    $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
    $ps = New-Object System.Drawing.Imaging.EncoderParameters 1
    $ps.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality), ([long]$Quality)
    $bmp.Save($Out, $codec, $ps); $bmp.Dispose()
  }
} finally { $img.Dispose() }
"""


def _powershell(script: str, work: Path, args: list[str], seconds: int) -> None:
    if os.name != "nt":
        raise Unconvertible("this needs Windows")
    ps1 = work / "step.ps1"
    ps1.write_text(script, encoding="utf-8")
    _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(ps1), *args], seconds)


def office(data: bytes, frm: str, to: str) -> bytes:
    """A Word, Excel or PowerPoint file to PDF, or a Word file or a PDF to DOCX, with what this machine has."""
    tool = office_tool()
    if tool is None:
        raise Unconvertible("there is no Office or LibreOffice on this machine")
    with tempfile.TemporaryDirectory(prefix="falcon-convert-") as tmp:
        work = Path(tmp)
        src = _in_temp(data, frm, work)
        if tool == "word":
            app = "word" if frm in WORD or frm == "pdf" else "excel" if frm in EXCEL else "powerpoint" if frm in POWERPOINT else None
            if app is None or (app != "word" and to != "pdf"):
                raise Unconvertible(f"Office does not make a {to.upper()} from a {frm.upper()} file")
            if app != "word" and not _office_app(f"{app.capitalize() if app != 'powerpoint' else 'PowerPoint'}.Application"):
                raise Unconvertible(f"{app.capitalize()} is not installed here")
            out = work / f"out.{to}"
            _powershell(PS_OFFICE, work, ["-App", app, "-In", str(src), "-Out", str(out), "-To", to], OFFICE_SECONDS)
            return _out(work, to)
        soffice = _soffice()
        assert soffice is not None
        target = "docx:MS Word 2007 XML" if to == "docx" else "pdf"
        argv = [soffice, "--headless", "--norestore", f"-env:UserInstallation=file:///{work.as_posix()}/profile"]
        if frm == "pdf":
            argv.append("--infilter=writer_pdf_import")
        _run([*argv, "--convert-to", target, "--outdir", str(work), str(src)], OFFICE_SECONDS)
        return _out(work, to)


def image(data: bytes, frm: str, to: str, quality: int = 85) -> bytes:
    """An image to JPG or PNG (Windows' own image library)."""
    with tempfile.TemporaryDirectory(prefix="falcon-image-") as tmp:
        work = Path(tmp)
        src = _in_temp(data, frm, work)
        out = work / f"out.{to}"
        _powershell(PS_IMAGE, work, ["-In", str(src), "-Out", str(out), "-To", to, "-Quality", str(int(quality))], IMAGE_SECONDS)
        return _out(work, to)


def to_pdf(data: bytes, frm: str) -> bytes:
    if frm in TEXT or frm in pdf.JPEG:
        try:
            return pdf.to_pdf(data, frm)
        except pdf.NotConvertible as exc:
            raise Unconvertible(f"a damaged {frm.upper()} file") from exc
    if frm in IMAGES:
        return pdf.to_pdf(image(data, frm, "jpg", 92), "jpg")
    if frm in WORD or frm in EXCEL or frm in POWERPOINT:
        return office(data, frm, "pdf")
    raise Unconvertible(f"a {frm.upper()} file is not made into a PDF")


def to_docx(data: bytes, frm: str) -> bytes:
    if frm in TEXT:
        return text_docx(data)
    if frm == "pdf" or frm in WORD:
        return office(data, frm, "docx")
    raise Unconvertible(f"a {frm.upper()} file is not made into a DOCX")


# --- DOCX from text, written here ------------------------------------------------------------------------------------------------

def text_docx(data: bytes) -> bytes:
    """A plain Word document: one paragraph per line of the text."""
    text = pdf._decode(data)
    paras = "".join(f'<w:p><w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r></w:p>' for line in text.splitlines() or [""])
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                               '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                               '<Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" '
                               'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                             f'<w:body>{paras}</w:body></w:document>',
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, body.encode("utf-8"))
    return out.getvalue()
