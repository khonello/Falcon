"""Screenshots of the Worker's windows (boards WR01, TK07), each over a desktop backdrop.

    environ-operator/Scripts/python.exe design/shot_worker.py design/shots
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
now = datetime.now().astimezone()
SPECS = {
    "blocked": {"occupant_name": "R. Mensah", "deadline_at": (now + timedelta(minutes=20)).isoformat()},
    "message": {"from": "R. Mensah", "text": "Please save your work; the network restarts at 18:00."},
    "ask": {"to": "R. Mensah", "draft": "The printer on floor 2 won't take my login."},
    "locked": {"message": "Locked for maintenance.", "until": (now + timedelta(minutes=25)).isoformat()},
    "task": {"from": "R. Mensah", "title": "Q3 reconciliation",
             "description": "Reconcile the Q3 supplier invoices against suppliers-q3.xlsx and produce reconciliation-q3.docx.",
             "due": (now + timedelta(days=2)).replace(hour=17, minute=0).isoformat(),
             "signs": [{"name": "suppliers-q3.xlsx", "seen": now.replace(hour=10, minute=42).isoformat()},
                       {"name": "reconciliation-q3.docx", "hint": "save it anywhere; it is found by name"},
                       {"name": "Excel, on that file", "program": True}]},
}


def main(out: str) -> None:
    out_dir = ROOT / out
    out_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    if os.name == "nt":
        env.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
    for kind, spec in SPECS.items():
        path = out_dir / f"worker-{kind}.png"
        r = subprocess.run([sys.executable, "-m", "worker_client.windows", kind, json.dumps(spec), "--shot", str(path)],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
        print(kind, r.stdout.strip() or r.stderr.strip()[-400:])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "design/shots")
