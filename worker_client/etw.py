"""Instant program starts and file opens, from Windows' own event tracing (ETW) -- no polling, no Windows audit policy to switch on by hand.

Two real-time trace sessions, each started only while an automation waits for what it carries and stopped the moment none does:

  * Microsoft-Windows-Kernel-Process   -> a program started / stopped, the instant Windows creates / ends the process
  * Microsoft-Windows-Kernel-File      -> a file or folder opened, the instant the file system is asked to; filtered here, in the
                                          callback, by the paths the automations named, so the flood of every open on the machine
                                          never leaves this module

Windows lets only an elevated process, or a member of "Performance Log Users", start a trace session. The Worker runs as a service under
the system account (packaging), which can; run as an ordinary user it cannot, `start()` says so and returns False, and the caller keeps
its look-every-few-seconds fallback -- nothing breaks, it is just not instant. Nothing is ever left running: a session is stopped by
name on `stop()`, and a stale one a crashed run left behind is stopped before a new one starts.

The callbacks run on the trace's own thread and do almost nothing: read a few fields, test them against the wanted set, queue the match.
Falcon's own process is ignored so reporting a signal never causes another.
"""

from __future__ import annotations

import logging
import os
import struct
import sys
import threading
import uuid
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

PROCESS_PROVIDER = "{22FB2CD6-0E7B-422B-A0C7-2FAD1FD0E716}"     # Microsoft-Windows-Kernel-Process
FILE_PROVIDER = "{EDD08927-9CC4-4E65-B970-C2560FB5C289}"        # Microsoft-Windows-Kernel-File
PROCESS_KEYWORD = 0x10                                           # WINEVENT_KEYWORD_PROCESS
FILE_KEYWORD_CREATE = 0x80                                       # KERNEL_FILE_KEYWORD_CREATE
EVENT_PROCESS_START, EVENT_PROCESS_STOP, EVENT_FILE_CREATE = 1, 2, 12
FILE_DIRECTORY_FILE = 0x00000001

Emit = Callable[[str, dict[str, Any]], None]

# programs that open everything all the time and say nothing about who made a change: not worth remembering as "the one that touched it"
QUIET_TOUCHERS = frozenset({"system", "searchindexer.exe", "searchprotocolhost.exe", "msmpeng.exe", "svchost.exe", "dllhost.exe", "backgroundtaskhost.exe",
                            "runtimebroker.exe", "audiodg.exe", "wmiprvse.exe", "smartscreen.exe", "taskhostw.exe"})


# --- reading an event's payload (pure: testable anywhere) ---------------------------------------------------------------------


def utf16z(data: bytes, offset: int) -> str:
    """The NUL-terminated UTF-16 string at `offset`, or "" when there is none."""
    if offset >= len(data):
        return ""
    end = offset
    while end + 1 < len(data) and data[end:end + 2] != b"\x00\x00":
        end += 2
    return data[offset:end].decode("utf-16-le", "replace")


def basename(path: str) -> str:
    return path.replace("/", "\\").rsplit("\\", 1)[-1]


def process_start(data: bytes) -> tuple[int, str] | None:
    """(pid, image name) of a Kernel-Process start event: ProcessID u32, CreateTime u64, ParentProcessID u32, SessionID u32, Flags u32, ImageName."""
    if len(data) < 26:
        return None
    pid = struct.unpack_from("<I", data, 0)[0]
    # The image name follows a few fields whose number differs between Windows versions (observed on Windows 11: 76 bytes in), and it always begins
    # with the kernel's own device path, so it is found by that rather than at a fixed place.
    at = data.find("\\Device\\".encode("utf-16-le"), 8)
    name = basename(utf16z(data, at if at >= 0 else 24))
    return (pid, name) if name else None


def file_open(data: bytes, pointer_size: int = 8) -> tuple[str, int] | None:
    """(device path, create options) of a Kernel-File create event: Irp, FileObject (pointers), IssuingThreadId, CreateOptions, CreateAttributes, ShareAccess, FileName."""
    head = pointer_size * 2
    if len(data) < head + 16 + 2:
        return None
    options = struct.unpack_from("<I", data, head + 4)[0]
    path = utf16z(data, head + 16)
    return (path, options) if path else None


def device_map() -> dict[str, str]:
    """`\\Device\\HarddiskVolume3` -> `C:` for every drive letter (the kernel names files by device, people by letter)."""
    if sys.platform != "win32":
        return {}
    import ctypes

    out: dict[str, str] = {}
    buf = ctypes.create_unicode_buffer(1024)
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if ctypes.windll.kernel32.QueryDosDeviceW(f"{letter}:", buf, 1024):
            out[buf.value.lower()] = f"{letter}:"
    return out


def drive_path(device_path: str, devices: dict[str, str]) -> str | None:
    """`\\Device\\HarddiskVolume3\\Users\\a.txt` -> `C:\\Users\\a.txt`, or None for a path with no drive letter (pipes, the registry, network shares)."""
    low = device_path.lower()
    for dev, letter in devices.items():
        if low.startswith(dev + "\\"):
            return letter + device_path[len(dev):]
    return None


class FileMatcher:
    """The paths automations named. `add` per interest block {path_prefix?, name_suffix?}; `matches` is cheap enough for the trace thread.
    An interest naming neither (only a resource tier) cannot be decided here and is not matched: the Engine would be sent every open on the machine."""

    def __init__(self) -> None:
        self.prefixes: list[str] = []
        self.suffixes: list[str] = []
        self.unfiltered_skipped = 0

    def set(self, matches: list[dict[str, Any]]) -> None:
        prefixes, suffixes, skipped = [], [], 0
        for m in matches:
            pre, suf = str(m.get("path_prefix") or "").replace("/", "\\").lower(), str(m.get("name_suffix") or "").lower()
            if pre:
                prefixes.append(pre)
            elif suf:
                suffixes.append(suf)
            else:
                skipped += 1
        self.prefixes, self.suffixes, self.unfiltered_skipped = prefixes, suffixes, skipped

    @property
    def active(self) -> bool:
        return bool(self.prefixes or self.suffixes)

    def matches(self, path: str) -> bool:
        low = path.lower()
        return any(low.startswith(p) for p in self.prefixes) or any(low.endswith(s) for s in self.suffixes)


# --- the trace sessions --------------------------------------------------------------------------------------------------------


def _guid_bytes(text: str) -> bytes:
    return uuid.UUID(text).bytes_le


class TraceSession:
    """One real-time ETW session on one provider, delivering each event's (event id, process id, payload) to `handle` on its own thread."""

    def __init__(self, name: str, provider: str, keyword: int, handle: Callable[[int, int, bytes], None]) -> None:
        self.name, self.provider, self.keyword, self.handle = name, provider, keyword, handle
        self._thread: threading.Thread | None = None
        self._session = 0
        self._ready = threading.Event()
        self._ok = False
        self._callback: Any = None
        self.error = ""
        self.records = 0                  # every record Windows delivered, wanted or not: proof the trace itself works

    def start(self) -> bool:
        if sys.platform != "win32":
            self.error = "not Windows"
            return False
        self._thread = threading.Thread(target=self._run, name=f"falcon-{self.name}", daemon=True)
        self._thread.start()
        self._ready.wait(10)
        return self._ok

    def stop(self) -> None:
        if sys.platform != "win32":
            return
        self._control_stop()
        if self._thread is not None:
            self._thread.join(3)
        self._ok = False

    # -- Windows ------------------------------------------------------------------------------------------------

    def _properties(self):
        import ctypes
        from ctypes import wintypes

        class WNODE_HEADER(ctypes.Structure):
            _fields_ = [("BufferSize", wintypes.ULONG), ("ProviderId", wintypes.ULONG), ("HistoricalContext", ctypes.c_uint64),
                        ("TimeStamp", ctypes.c_int64), ("Guid", ctypes.c_ubyte * 16), ("ClientContext", wintypes.ULONG), ("Flags", wintypes.ULONG)]

        class EVENT_TRACE_PROPERTIES(ctypes.Structure):
            _fields_ = [("Wnode", WNODE_HEADER), ("BufferSize", wintypes.ULONG), ("MinimumBuffers", wintypes.ULONG), ("MaximumBuffers", wintypes.ULONG),
                        ("MaximumFileSize", wintypes.ULONG), ("LogFileMode", wintypes.ULONG), ("FlushTimer", wintypes.ULONG), ("EnableFlags", wintypes.ULONG),
                        ("AgeLimit", wintypes.LONG), ("NumberOfBuffers", wintypes.ULONG), ("FreeBuffers", wintypes.ULONG), ("EventsLost", wintypes.ULONG),
                        ("BuffersWritten", wintypes.ULONG), ("LogBuffersLost", wintypes.ULONG), ("RealTimeBuffersLost", wintypes.ULONG),
                        ("LoggerThreadId", wintypes.HANDLE), ("LogFileNameOffset", wintypes.ULONG), ("LoggerNameOffset", wintypes.ULONG)]

        size = ctypes.sizeof(EVENT_TRACE_PROPERTIES) + 2 * (len(self.name) + 1) + 2 * 1024
        buf = ctypes.create_string_buffer(size)
        props = EVENT_TRACE_PROPERTIES.from_buffer(buf)
        props.Wnode.BufferSize = size
        props.Wnode.Flags = 0x00020000                                   # WNODE_FLAG_TRACED_GUID
        props.Wnode.ClientContext = 1                                    # QPC timestamps
        props.LogFileMode = 0x00000100                                   # EVENT_TRACE_REAL_TIME_MODE
        props.BufferSize = 64                                            # KB
        props.MinimumBuffers, props.MaximumBuffers = 4, 16
        props.LoggerNameOffset = ctypes.sizeof(EVENT_TRACE_PROPERTIES)
        return buf, props

    def _control_stop(self) -> None:
        import ctypes

        buf, _ = self._properties()
        ctypes.windll.advapi32.ControlTraceW(ctypes.c_uint64(self._session), self.name, buf, 1)       # EVENT_TRACE_CONTROL_STOP

    def _run(self) -> None:
        import ctypes
        from ctypes import wintypes

        adv = ctypes.windll.advapi32
        for fn in (adv.StartTraceW, adv.ControlTraceW, adv.EnableTraceEx2, adv.OpenTraceW, adv.ProcessTrace, adv.CloseTrace):
            fn.restype = ctypes.c_ulong
        adv.OpenTraceW.restype = ctypes.c_uint64
        handle = ctypes.c_uint64(0)
        buf, _ = self._properties()
        rc = adv.StartTraceW(ctypes.byref(handle), self.name, buf)
        if rc == 183:                                                    # ERROR_ALREADY_EXISTS: a crashed run left one; stop it and start ours
            stale, _ = self._properties()
            adv.ControlTraceW(ctypes.c_uint64(0), self.name, stale, 1)
            buf, _ = self._properties()
            rc = adv.StartTraceW(ctypes.byref(handle), self.name, buf)
        if rc != 0:
            self.error = "needs an elevated process or membership of Performance Log Users" if rc == 5 else f"StartTrace failed ({rc})"
            self._ready.set()
            return
        self._session = handle.value
        provider = (ctypes.c_ubyte * 16).from_buffer_copy(_guid_bytes(self.provider))
        rc = adv.EnableTraceEx2(ctypes.c_uint64(self._session), ctypes.byref(provider), 1, 5, ctypes.c_uint64(self.keyword), ctypes.c_uint64(0), 0, None)
        if rc != 0:
            self.error = f"EnableTraceEx2 failed ({rc})"
            self._control_stop()
            self._ready.set()
            return

        class EVENT_RECORD_HEAD(ctypes.Structure):
            _fields_ = [("Size", wintypes.WORD), ("HeaderType", wintypes.WORD), ("Flags", wintypes.WORD), ("EventProperty", wintypes.WORD),
                        ("ThreadId", wintypes.DWORD), ("ProcessId", wintypes.DWORD), ("TimeStamp", ctypes.c_int64), ("ProviderId", ctypes.c_ubyte * 16),
                        ("Id", wintypes.WORD), ("Version", ctypes.c_ubyte), ("Channel", ctypes.c_ubyte), ("Level", ctypes.c_ubyte), ("Opcode", ctypes.c_ubyte),
                        ("Task", wintypes.WORD), ("Keyword", ctypes.c_uint64), ("KernelTime", wintypes.DWORD), ("UserTime", wintypes.DWORD),
                        ("ActivityId", ctypes.c_ubyte * 16), ("ProcessorNumber", ctypes.c_ubyte), ("Alignment", ctypes.c_ubyte), ("LoggerId", wintypes.WORD),
                        ("ExtendedDataCount", wintypes.WORD), ("UserDataLength", wintypes.WORD), ("ExtendedData", ctypes.c_void_p), ("UserData", ctypes.c_void_p),
                        ("UserContext", ctypes.c_void_p)]

        callback_type = ctypes.WINFUNCTYPE(None, ctypes.POINTER(EVENT_RECORD_HEAD))

        def on_record(rec) -> None:
            try:
                r = rec.contents
                self.records += 1
                data = ctypes.string_at(r.UserData, r.UserDataLength) if r.UserData and r.UserDataLength else b""
                self.handle(r.Id, r.ProcessId, data)
            except Exception:      # never let an exception cross back into Windows
                log.exception("trace record failed")

        self._callback = callback_type(on_record)

        class TIME_ZONE_INFORMATION(ctypes.Structure):
            _fields_ = [("Bias", wintypes.LONG), ("StandardName", wintypes.WCHAR * 32), ("StandardDate", wintypes.WORD * 8), ("StandardBias", wintypes.LONG),
                        ("DaylightName", wintypes.WCHAR * 32), ("DaylightDate", wintypes.WORD * 8), ("DaylightBias", wintypes.LONG)]

        class TRACE_LOGFILE_HEADER(ctypes.Structure):
            _fields_ = [("BufferSize", wintypes.ULONG), ("Version", wintypes.ULONG), ("ProviderVersion", wintypes.ULONG), ("NumberOfProcessors", wintypes.ULONG),
                        ("EndTime", ctypes.c_int64), ("TimerResolution", wintypes.ULONG), ("MaximumFileSize", wintypes.ULONG), ("LogFileMode", wintypes.ULONG),
                        ("BuffersWritten", wintypes.ULONG), ("LogInstanceGuid", ctypes.c_ubyte * 16), ("LoggerName", ctypes.c_void_p), ("LogFileName", ctypes.c_void_p),
                        ("TimeZone", TIME_ZONE_INFORMATION), ("BootTime", ctypes.c_int64), ("PerfFreq", ctypes.c_int64), ("StartTime", ctypes.c_int64),
                        ("ReservedFlags", wintypes.ULONG), ("BuffersLost", wintypes.ULONG)]

        class EVENT_TRACE_LOGFILEW(ctypes.Structure):
            _fields_ = [("LogFileName", wintypes.LPWSTR), ("LoggerName", wintypes.LPWSTR), ("CurrentTime", ctypes.c_int64), ("BuffersRead", wintypes.ULONG),
                        ("ProcessTraceMode", wintypes.ULONG), ("CurrentEvent", ctypes.c_byte * 88), ("LogfileHeader", TRACE_LOGFILE_HEADER),
                        ("BufferCallback", ctypes.c_void_p), ("BufferSize", wintypes.ULONG), ("Filled", wintypes.ULONG), ("EventsLost", wintypes.ULONG),
                        ("EventRecordCallback", callback_type), ("IsKernelTrace", wintypes.ULONG), ("Context", ctypes.c_void_p)]

        # Windows reads these by offset: a wrong size silently moves the callback and nothing ever arrives. 64-bit sizes from the SDK headers.
        if ctypes.sizeof(ctypes.c_void_p) == 8 and (ctypes.sizeof(TRACE_LOGFILE_HEADER) != 280 or ctypes.sizeof(EVENT_TRACE_LOGFILEW) != 448):
            self.error = f"trace structures are the wrong size ({ctypes.sizeof(TRACE_LOGFILE_HEADER)}/{ctypes.sizeof(EVENT_TRACE_LOGFILEW)})"
            self._control_stop()
            self._ready.set()
            return

        logfile = EVENT_TRACE_LOGFILEW()
        logfile.LoggerName = self.name
        logfile.ProcessTraceMode = 0x00000100 | 0x10000000               # real time + EVENT_RECORD
        logfile.EventRecordCallback = self._callback
        trace = adv.OpenTraceW(ctypes.byref(logfile))
        if trace == 0xFFFFFFFFFFFFFFFF or trace == 0xFFFFFFFF:
            self.error = "OpenTrace failed"
            self._control_stop()
            self._ready.set()
            return
        self._ok = True
        self._ready.set()
        handles = (ctypes.c_uint64 * 1)(trace)
        adv.ProcessTrace(handles, 1, None, None)                         # blocks until the session is stopped
        adv.CloseTrace(ctypes.c_uint64(trace))


class EtwWatcher:
    """Instant program starts / stops and file opens, started on demand. `emit(type, data)` is called from the trace thread."""

    def __init__(self, emit: Emit) -> None:
        self.emit = emit
        self.files = FileMatcher()
        self._me = os.getpid()
        self._names: dict[int, str] = {}
        self._devices: dict[str, str] = {}
        self._process: TraceSession | None = None
        self._file: TraceSession | None = None
        self._recent: dict[str, float] = {}
        self.errors: dict[str, str] = {}
        # Who last touched a file under the folders this machine is watched on: the program name and when. Kept for Detective's witness stamp ("which program
        # made this change"), by the same trace -- one dict write per open under the watched folders, nothing sent anywhere.
        self.touch_roots: list[str] = []
        self.touches: OrderedDict[str, tuple[int, float]] = OrderedDict()       # path -> (the process that opened it, when); named when asked, not now
        self._ended: OrderedDict[int, str] = OrderedDict()                       # the last few programs that have already finished

    def set_touch_roots(self, roots: list[str]) -> None:
        self.touch_roots = [r.replace("/", "\\").rstrip("\\").lower() + "\\" for r in roots if r]

    def who(self, path: str, within: float = 5.0) -> str:
        """The program that last opened this file, if it did so in the last few seconds (the file change being reported is what it did)."""
        import time

        hit = self.touches.get(path.replace("/", "\\").lower())
        if not hit or time.monotonic() - hit[1] > within:
            return ""
        name = self._name_of(hit[0])
        return "" if name.lower() in QUIET_TOUCHERS else name

    @property
    def programs_live(self) -> bool:
        return self._process is not None

    @property
    def files_live(self) -> bool:
        return self._file is not None

    def want_programs(self, on: bool) -> bool:
        if on and self._process is None:
            try:
                import psutil

                self._names = {p.pid: p.info["name"] for p in psutil.process_iter(["name"]) if p.info.get("name")}
            except ImportError:
                self._names = {}
            session = TraceSession("FalconProcess", PROCESS_PROVIDER, PROCESS_KEYWORD, self._on_process)
            if session.start():
                self._process = session
            else:
                self.errors["programs"] = session.error
                log.info("instant program events unavailable: %s", session.error)
        elif not on and self._process is not None:
            self._process.stop()
            self._process = None
        return self._process is not None

    def want_files(self, matches: list[dict[str, Any]] | None) -> bool:
        self.files.set(matches or [])
        if self.files.unfiltered_skipped:
            log.warning("%d file-open interest(s) name no path or suffix and are not watched live", self.files.unfiltered_skipped)
        if (self.files.active or self.touch_roots) and self._file is None:
            self._devices = device_map()
            session = TraceSession("FalconFile", FILE_PROVIDER, FILE_KEYWORD_CREATE, self._on_file)
            if session.start():
                self._file = session
            else:
                self.errors["files"] = session.error
                log.info("instant file-open events unavailable: %s", session.error)
        elif not (self.files.active or self.touch_roots) and self._file is not None:
            self._file.stop()
            self._file = None
        return self._file is not None

    def stop(self) -> None:
        for session in (self._process, self._file):
            if session is not None:
                session.stop()
        self._process = self._file = None

    # -- trace callbacks (the trace's own thread) -----------------------------------------------------------------

    def _on_process(self, event_id: int, pid: int, data: bytes) -> None:
        if event_id == EVENT_PROCESS_START:
            got = process_start(data)
            if got is not None and got[0] != self._me:
                self._names[got[0]] = got[1]
                self.emit("program.launched", {"process": got[1]})
        elif event_id == EVENT_PROCESS_STOP and pid != self._me:
            name = self._names.pop(pid, None)
            if name:
                self._ended[pid] = name
                while len(self._ended) > 2000:
                    self._ended.popitem(last=False)
                self.emit("program.exited", {"process": name})

    def _on_file(self, event_id: int, pid: int, data: bytes) -> None:
        if event_id != EVENT_FILE_CREATE or pid == self._me:
            return
        got = file_open(data)
        if got is None or got[1] & FILE_DIRECTORY_FILE or got[0].endswith("\\"):
            return
        path = drive_path(got[0], self._devices)
        if path is None:
            return
        import time

        now = time.monotonic()
        low = path.lower()
        if self.touch_roots and low.startswith(tuple(self.touch_roots)) and (self._names.get(pid) or self._ended.get(pid) or "").lower() not in QUIET_TOUCHERS:
            self.touches[low] = (pid, now)           # the program's name may not have reached us yet (the two traces are delivered separately): it is looked up when asked
            self.touches.move_to_end(low)
            while len(self.touches) > 20000:
                self.touches.popitem(last=False)
        if not self.files.matches(path) or os.path.isdir(path):
            return                                  # (a folder opened without the directory flag is still a folder)
        if now - self._recent.get(path, 0.0) < 3.0:                       # one open is many create calls: tell it once
            return
        if len(self._recent) > 2000:
            self._recent.clear()
        self._recent[path] = now
        self.emit("file.accessed", {"path": path, "name": basename(path), "process": self._name_of(pid)})

    def _name_of(self, pid: int) -> str:
        """Which program opened it: known from its start, or asked of Windows for a process that was already running."""
        name = self._names.get(pid) or self._ended.get(pid)
        if name is None:
            try:
                import psutil

                name = self._names[pid] = psutil.Process(pid).name()
            except Exception:  # noqa: BLE001 -- it ended already, or may not be looked at
                name = ""
        return name
