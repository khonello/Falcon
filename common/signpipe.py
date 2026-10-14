"""Signing for a console on a machine whose key belongs to the service (Windows).

An Admin's workstation is registered once, by the Worker service on it (installers/registration by probation); the key it is handed
is kept where only the system account and administrators can read it. The console runs as the person, so it cannot read that key,
and must not: instead it asks the service to answer the Engine's challenge. The key never leaves the service.

    service  ->  SignPipeServer(key).start()          a named pipe, local interactive users only
    console  ->  sign("<nonce>")                      -> HMAC-SHA256(key, nonce), hex

What this does and does not give: anyone signed in at that machine can sign in to the Engine as that machine's account -- exactly as
they could by sitting at it and opening its console -- and nobody off the machine can, because there is no key to carry away.

Stdlib only (ctypes): this module is bundled by the Worker and the Operator Client.
"""

from __future__ import annotations

import errno
import hashlib
import hmac
import json
import os
import sys
import threading
import time
from typing import Any

PIPE_NAME = r"\\.\pipe\FalconSign"
# SYSTEM and Administrators: everything; interactively signed-in users: read and write (no one else, no network logons)
SDDL = "D:(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGW;;;IU)"
MAX_NONCE = 256
CLIENT_SECONDS = 3.0
ABSENT_SECONDS = 1.5      # between one client being taken and the next instance being made there is a moment with no pipe at all; a loaded machine stretches it

_PIPE_ACCESS_DUPLEX, _PIPE_REJECT_REMOTE_CLIENTS, _UNLIMITED = 0x3, 0x8, 255
_ERROR_PIPE_CONNECTED, _ERROR_PIPE_BUSY = 535, 231


def respond(key: bytes, request: bytes, client_id: str = "") -> bytes:
    """One request line in, one reply line out (kept apart from the pipe so it can be tested anywhere)."""
    try:
        msg = json.loads(request)
        if msg.get("whoami"):                                # the machine's client id is not secret; the console needs it to introduce itself
            return (json.dumps({"client_id": client_id}) + "\n").encode()
        nonce = str(msg["nonce"])
        if not nonce or len(nonce) > MAX_NONCE:
            raise ValueError(f"a nonce is 1 to {MAX_NONCE} characters")
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return (json.dumps({"error": str(exc) or "bad request"}) + "\n").encode()
    return (json.dumps({"hmac": hmac.new(key, nonce.encode("utf-8"), hashlib.sha256).hexdigest()}) + "\n").encode()


class SignPipeServer:
    def __init__(self, key: bytes | str, name: str | None = None, sddl: str = SDDL, client_id: str = "") -> None:
        self.key = bytes.fromhex(key) if isinstance(key, str) else key
        self.client_id = client_id
        self.name = name or PIPE_NAME
        self.sddl = sddl
        self.served = 0
        self.error: str | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if sys.platform != "win32" or not self.key:
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="falcon-sign-pipe", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            try:                                           # wake the one waiting for a client
                with open(self.name, "r+b", buffering=0):
                    pass
            except OSError:
                pass
            self._thread.join(3)
            self._thread = None

    def _run(self) -> None:
        try:
            self._serve()
        except Exception as exc:  # noqa: BLE001 -- the pipe thread must say why it stopped, not vanish
            self.error = f"the pipe stopped: {exc!r}"

    def _serve(self) -> None:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        adv = ctypes.WinDLL("advapi32", use_last_error=True)
        k32.CreateNamedPipeW.restype = wintypes.HANDLE
        k32.CreateNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                         wintypes.DWORD, ctypes.c_void_p]
        for fn, args in ((k32.ConnectNamedPipe, [wintypes.HANDLE, ctypes.c_void_p]),
                         (k32.ReadFile, [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]),
                         (k32.WriteFile, [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]),
                         (k32.FlushFileBuffers, [wintypes.HANDLE]), (k32.DisconnectNamedPipe, [wintypes.HANDLE]),
                         (k32.CancelIoEx, [wintypes.HANDLE, ctypes.c_void_p]), (k32.CloseHandle, [wintypes.HANDLE])):
            fn.argtypes = args

        class SECURITY_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p), ("bInheritHandle", wintypes.BOOL)]

        sd = ctypes.c_void_p()
        adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
                                                                              ctypes.c_void_p]
        if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(self.sddl, 1, ctypes.byref(sd), None):
            self.error = f"could not build the pipe's access rules ({ctypes.get_last_error()})"
            return
        sa = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), sd, False)

        def serve_one(handle: int) -> None:
            timer = threading.Timer(CLIENT_SECONDS, lambda: k32.CancelIoEx(handle, None))      # a client that says nothing is let go
            timer.start()
            try:
                buf = ctypes.create_string_buffer(4096)
                got = wintypes.DWORD(0)
                data = b""
                while b"\n" not in data and len(data) < 4096:
                    if not k32.ReadFile(handle, buf, 4096, ctypes.byref(got), None) or not got.value:
                        break
                    data += buf.raw[:got.value]
                if b"\n" in data:
                    reply = respond(self.key, data.split(b"\n", 1)[0], self.client_id)
                    wrote = wintypes.DWORD(0)
                    k32.WriteFile(handle, reply, len(reply), ctypes.byref(wrote), None)
                    k32.FlushFileBuffers(handle)
                    self.served += 1
            finally:
                timer.cancel()
                k32.DisconnectNamedPipe(handle)
                k32.CloseHandle(handle)

        while not self._stop.is_set():
            handle = k32.CreateNamedPipeW(self.name, _PIPE_ACCESS_DUPLEX, _PIPE_REJECT_REMOTE_CLIENTS, _UNLIMITED, 4096, 4096, 0, ctypes.byref(sa))
            if handle in (None, wintypes.HANDLE(-1).value):
                self.error = f"could not open the pipe ({ctypes.get_last_error()})"
                time.sleep(1)
                continue
            connected = k32.ConnectNamedPipe(handle, None) or ctypes.get_last_error() == _ERROR_PIPE_CONNECTED
            if not connected or self._stop.is_set():
                k32.CloseHandle(handle)
                continue
            threading.Thread(target=serve_one, args=(handle,), daemon=True).start()


def _ask(message: dict[str, Any], name: str | None, seconds: float) -> dict[str, Any]:
    name = name or PIPE_NAME
    start = time.monotonic()
    end = start + seconds
    while True:
        try:
            with open(name, "r+b", buffering=0) as pipe:
                pipe.write((json.dumps(message) + "\n").encode())
                line = pipe.readline()
            break
        except OSError as exc:
            # open() reports "every instance is busy" as EINVAL (the Windows code is lost on the way) and "no such pipe" as ENOENT: wait a
            # moment for the first (the service is serving someone else), only a moment for the second (there may be no service at all)
            busy = exc.errno == errno.EINVAL or getattr(exc, "winerror", None) == _ERROR_PIPE_BUSY
            absent = exc.errno == errno.ENOENT
            now = time.monotonic()
            if (busy and now < end) or (absent and now < min(end, start + ABSENT_SECONDS)):
                time.sleep(0.05)
                continue
            raise
    reply: dict[str, Any] = json.loads(line or b"{}")
    return reply


def sign(nonce: str, name: str | None = None, seconds: float = CLIENT_SECONDS) -> str:
    """Ask the service on this machine to answer the Engine's challenge. Raises OSError when there is no service to ask."""
    reply = _ask({"nonce": nonce}, name, seconds)
    if "hmac" not in reply:
        raise OSError(str(reply.get("error") or "the service did not sign"))
    return str(reply["hmac"])


def whoami(name: str | None = None, seconds: float = CLIENT_SECONDS) -> str:
    """This machine's client id, from the service ("" when there is none yet: it is still waiting to be registered)."""
    return str(_ask({"whoami": True}, name, seconds).get("client_id") or "")


def available(name: str | None = None) -> bool:
    return os.name == "nt" and os.path.exists(name or PIPE_NAME)
