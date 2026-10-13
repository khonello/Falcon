"""Does the Worker's keyboard injection reach a real window?  (the part of the session window a single PC cannot show)

Opens a small window with a text box on this desktop, gives it focus, sends the console's keyboard events the way the Worker
applies them (`RemoteInput`, without blocking the person's own input), and prints what arrived.

    environ-worker\\Scripts\\python.exe scripts\\keyboard_check.py
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worker_client.screenstream import RemoteInput  # noqa: E402

VK_A, VK_BACK, VK_SHIFT, VK_RETURN, VK_LEFT = 0x41, 0x08, 0x10, 0x0D, 0x25


def main() -> int:
    root = tk.Tk()
    root.title("Falcon keyboard check")
    root.geometry("360x90+200+200")
    root.attributes("-topmost", True)
    box = tk.Entry(root, width=40)
    box.pack(padx=10, pady=10)
    root.update()
    import ctypes

    user32 = ctypes.windll.user32
    user32.keybd_event(0x12, 0, 0, 0)         # an Alt tap lifts Windows' lock on who may take the foreground
    user32.keybd_event(0x12, 0, 2, 0)
    user32.SetForegroundWindow(user32.GetParent(root.winfo_id()) or root.winfo_id())
    root.update()
    box.focus_force()
    root.update()
    remote = RemoteInput()
    remote.start()
    remote.controlling = True            # applies input; deliberately does not block the person's own keyboard and mouse

    def press(vk: int) -> list[dict]:
        return [{"t": "key", "vk": vk, "down": True}, {"t": "key", "vk": vk, "down": False}]

    def send() -> None:
        events = [{"t": "text", "text": "Hello, Falcon "}]               # typed characters (any language)
        events += [{"t": "key", "vk": VK_SHIFT, "down": True}] + press(VK_A) + [{"t": "key", "vk": VK_SHIFT, "down": False}]   # Shift+A
        events += press(VK_A)                                             # a
        events += press(VK_A) + press(VK_BACK)                            # a then Backspace
        events += [{"t": "text", "text": "é中"}]
        remote.apply(events)

    result: dict[str, str] = {}

    def read() -> None:
        result["text"] = box.get()
        root.destroy()

    root.after(600, send)
    root.after(2200, read)
    root.mainloop()
    remote.stop()
    want = "Hello, Falcon Aaé中"
    got = result.get("text", "")
    print(f"typed into the box: {ascii(got)}")
    print("PASS" if got == want else f"FAIL (wanted {ascii(want)})")
    return 0 if got == want else 1


if __name__ == "__main__":
    raise SystemExit(main())
