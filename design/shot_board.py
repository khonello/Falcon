"""Screenshot design boards with a headless browser -- no shell recipe needed.

    python design/shot_board.py DP05-Department [RC05-Record ...] [--size=1440x900] [--out=design/shots]
    python design/shot_board.py --all

Each name is a file in design/boards/ (`<NAME>.dc.html` or `<NAME>.html`); the PNG lands in design/shots/<NAME>.png.
Uses Microsoft Edge on Windows, else Chrome/Chromium. The browser writes its --screenshot after the process returns
and only to an absolute path, so this waits for the file.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOARDS = HERE / "boards"


def browser() -> str:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("msedge"), shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise SystemExit("no Edge / Chrome / Chromium found for headless screenshots")


def shoot(name: str, out_dir: Path, size: str, exe: str) -> Path:
    page = next((p for p in (BOARDS / f"{name}.dc.html", BOARDS / f"{name}.html") if p.exists()), None)
    if page is None:
        raise SystemExit(f"no board named {name} in {BOARDS}")
    target = (out_dir / f"{name}.png").resolve()
    target.unlink(missing_ok=True)
    w, h = size.lower().split("x")
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}",
                    f"--screenshot={target}", page.resolve().as_uri()],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    for _ in range(100):                      # the file appears after the browser has returned
        if target.exists() and target.stat().st_size > 0:
            return target
        time.sleep(0.1)
    raise SystemExit(f"{name}: no screenshot was written")


def main(argv: list[str]) -> int:
    opts = {a[2:].partition("=")[0]: a.partition("=")[2] for a in argv if a.startswith("--")}
    names = [a for a in argv if not a.startswith("--")]
    if "all" in opts:
        names = sorted(p.name.split(".")[0] for p in BOARDS.glob("*.dc.html"))
    if not names:
        print(__doc__)
        return 2
    out_dir = Path(opts.get("out") or HERE / "shots")
    out_dir.mkdir(parents=True, exist_ok=True)
    exe = browser()
    for name in names:
        print(shoot(name, out_dir, opts.get("size") or "1440x900", exe))
    return 0


if __name__ == "__main__":
    os.chdir(HERE.parent)
    raise SystemExit(main(sys.argv[1:]))
