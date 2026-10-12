"""Starting a program on the signed-in person's desktop from a Windows service.

A service runs in session 0, which has no screen: nothing it draws or captures reaches the person. Windows has an official way across -- ask who
is signed in at the console (`WTSGetActiveConsoleSessionId`), take that person's token (`WTSQueryUserToken`, allowed to the system account only),
and start the program with it on their desktop (`CreateProcessAsUserW`, desktop `winsta0\\default`). This module does exactly that, with pipes for
the program's input and output, so the Worker's windows, the screenshot and the session window need nothing set up by hand.

Run as an ordinary user (the Worker in development) `in_service_session()` is False and callers start the program the plain way; nothing here is used.
A failure at any step returns None with the reason logged -- the caller carries on without a window, never crashes.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from typing import Any

log = logging.getLogger(__name__)


def in_service_session() -> bool:
    """True when this process is in session 0 (a service), where a desktop program must be started in someone else's session."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    sid = wintypes.DWORD()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(sid)):
        return False
    return sid.value == 0


def active_session() -> int | None:
    """The session of the person at the console, or None when nobody is signed in (the sign-in screen)."""
    if sys.platform != "win32":
        return None
    import ctypes

    sid = ctypes.windll.kernel32.WTSGetActiveConsoleSessionId()
    return None if sid in (0xFFFFFFFF, 0) else int(sid)


class _Reader:
    """`await readline()` over a pipe handle read on a thread."""

    def __init__(self, fileobj: Any) -> None:
        self._f = fileobj

    async def readline(self) -> bytes:
        return await asyncio.get_running_loop().run_in_executor(None, self._f.readline)


class _Writer:
    def __init__(self, fileobj: Any) -> None:
        self._f = fileobj

    def write(self, data: bytes) -> None:
        self._f.write(data)

    async def drain(self) -> None:
        await asyncio.get_running_loop().run_in_executor(None, self._f.flush)

    def close(self) -> None:
        try:
            self._f.close()
        except OSError:
            pass


class UserProcess:
    """A program on the person's desktop, shaped like an asyncio subprocess: stdin, stdout, returncode, wait(), terminate()."""

    def __init__(self, process_handle: int, stdin: Any, stdout: Any, pid: int = 0) -> None:
        self._handle = process_handle
        self.pid = pid
        self.stdin = _Writer(stdin)
        self.stdout = _Reader(stdout)

    @property
    def returncode(self) -> int | None:
        import ctypes
        from ctypes import wintypes

        code = wintypes.DWORD()
        if not ctypes.windll.kernel32.GetExitCodeProcess(self._handle, ctypes.byref(code)):
            return -1
        return None if code.value == 259 else int(code.value)          # STILL_ACTIVE

    async def wait(self) -> int:
        while (rc := self.returncode) is None:
            await asyncio.sleep(0.2)
        return rc

    def terminate(self) -> None:
        """End the program and everything it started (a launcher's child would otherwise be left running)."""
        import ctypes

        if self.returncode is None:
            if self.pid:
                subprocess.run(["taskkill", "/PID", str(self.pid), "/T", "/F"], capture_output=True, check=False)
            if self.returncode is None:
                ctypes.windll.kernel32.TerminateProcess(self._handle, 1)

    kill = terminate


def spawn_in_user_session(argv: list[str]) -> UserProcess | None:
    """Start `argv` on the active person's desktop with its stdin and stdout as pipes; None (and why, in the log) when that cannot be done."""
    if sys.platform != "win32":
        return None
    import ctypes
    import msvcrt
    from ctypes import wintypes

    k32, adv, wts, userenv = ctypes.windll.kernel32, ctypes.windll.advapi32, ctypes.windll.wtsapi32, ctypes.windll.userenv
    session = active_session()
    if session is None:
        log.info("nobody is signed in at the console; no desktop to start %s on", argv[:3])
        return None
    token = wintypes.HANDLE()
    if not wts.WTSQueryUserToken(session, ctypes.byref(token)):
        log.warning("WTSQueryUserToken failed (%s): only the system account may start a program on someone's desktop", ctypes.GetLastError())
        return None
    primary = wintypes.HANDLE()
    env = ctypes.c_void_p()
    handles: list[Any] = []
    try:
        # SecurityImpersonation = 2, TokenPrimary = 1, MAXIMUM_ALLOWED
        if not adv.DuplicateTokenEx(token, 0x02000000, None, 2, 1, ctypes.byref(primary)):
            log.warning("DuplicateTokenEx failed (%s)", ctypes.GetLastError())
            return None
        if not userenv.CreateEnvironmentBlock(ctypes.byref(env), primary, False):
            env = ctypes.c_void_p()

        class SECURITY_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p), ("bInheritHandle", wintypes.BOOL)]

        sa = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), None, True)
        in_r, in_w, out_r, out_w = (wintypes.HANDLE() for _ in range(4))
        if not k32.CreatePipe(ctypes.byref(in_r), ctypes.byref(in_w), ctypes.byref(sa), 0) or not k32.CreatePipe(ctypes.byref(out_r), ctypes.byref(out_w), ctypes.byref(sa), 0):
            log.warning("CreatePipe failed (%s)", ctypes.GetLastError())
            return None
        handles += [in_r, in_w, out_r, out_w]
        k32.SetHandleInformation(in_w, 1, 0)                              # our ends are not inherited by the child
        k32.SetHandleInformation(out_r, 1, 0)

        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD), ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
                        ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE), ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        si.lpDesktop = "winsta0\\default"
        si.dwFlags = 0x00000100                                           # STARTF_USESTDHANDLES
        si.hStdInput, si.hStdOutput = in_r, out_w
        si.hStdError = k32.GetStdHandle(-12)
        pi = PROCESS_INFORMATION()
        command = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
        # CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW
        if not adv.CreateProcessAsUserW(primary, None, command, None, None, True, 0x00000400 | 0x08000000, env, None, ctypes.byref(si), ctypes.byref(pi)):
            log.warning("CreateProcessAsUserW failed (%s)", ctypes.GetLastError())
            return None
        k32.CloseHandle(pi.hThread)
        k32.CloseHandle(in_r)                                             # the child's ends are closed here; ours stay
        k32.CloseHandle(out_w)
        stdin = os.fdopen(msvcrt.open_osfhandle(in_w.value, os.O_WRONLY), "wb", buffering=0)
        stdout = os.fdopen(msvcrt.open_osfhandle(out_r.value, os.O_RDONLY), "rb")
        handles.clear()
        return UserProcess(pi.hProcess, stdin, stdout, pi.dwProcessId)
    finally:
        if token:
            k32.CloseHandle(token)
        if primary:
            k32.CloseHandle(primary)
        if env:
            userenv.DestroyEnvironmentBlock(env)
        for h in handles:
            if h:
                k32.CloseHandle(h)
