"""The actions that come with Falcon (migration 055; the user, 13 Nov 2026: "it must begin with a good enough number of actions internal to the system").

A fresh install's Actions library is not empty: the built-ins ready to run with sensible settings (a lock for five minutes, a restart with a
warning), and scripts an IT Admin reaches for every week (free disk space, what is installed, why it needs a restart). They are Windows-native
only, like any custom action, and checked by the same validator. Most only look; the few that change something (clear old temporary files,
restart the print spooler) say so in their name.

`ensure()` runs at every Engine start and adds what is missing by its key, archived ones included: an action an Admin archived stays archived,
and one an Admin changed keeps their change. A new entry here reaches every install on its next start. Nothing in this list is ever removed
from a database by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.control import custom_actions
from engine.control.actions import BUILTIN, SETTLE_SECONDS, check_params, run_length


@dataclass(frozen=True)
class Starter:
    key: str
    name: str
    description: str
    kind: str                          # control | monitoring | custom
    timeout_s: int = 60
    builtin_type: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    language: str | None = None        # custom: powershell | python
    script: str | None = None
    output_kind: str = "text"          # custom: text | list | status


def _b(key: str, name: str, description: str, builtin_type: str, params: dict[str, Any] | None = None, timeout_s: int = 60) -> Starter:
    return Starter(key, name, description, BUILTIN[builtin_type]["category"], timeout_s, builtin_type, params or {})


def _ps(key: str, name: str, description: str, script: str, output_kind: str = "text", timeout_s: int = 60) -> Starter:
    return Starter(key, name, description, "custom", timeout_s, language="powershell", script=script.strip() + "\n", output_kind=output_kind)


def _py(key: str, name: str, description: str, script: str, output_kind: str = "text", timeout_s: int = 60) -> Starter:
    return Starter(key, name, description, "custom", timeout_s, language="python", script=script.strip() + "\n", output_kind=output_kind)


SAVE = "IT needs this machine in a few minutes. Please save your work now."

STARTER: tuple[Starter, ...] = (
    # --- the built-ins, ready to run ----------------------------------------------------------------------------------------------------
    _b("screenshot", "Take a screenshot", "What is on the screen right now", "screenshot"),
    _b("save-your-work", "Ask them to save their work", "A message on their screen until they close it", "notify", {"message": SAVE, "stay_s": 0}),
    _b("it-on-the-way", "Tell them IT is on the way", "A message on their screen for a minute", "notify",
       {"message": "IT has seen the problem and is on the way.", "stay_s": 60}),
    _b("lock-5", "Lock the screen for 5 minutes", "They cannot use it until it ends", "lock_session",
       {"duration_s": 300, "message": "IT has locked this machine for a few minutes."}),
    _b("lock-30", "Lock the screen for 30 minutes", "They cannot use it until it ends", "lock_session",
       {"duration_s": 1800, "message": "IT has locked this machine for half an hour."}),
    _b("restart-5", "Restart in 5 minutes", "They are warned first; unsaved work is lost", "reboot",
       {"delay_s": 300, "message": "This machine restarts in 5 minutes. Please save your work."}),
    _b("restart-1", "Restart in 1 minute", "They are warned first; unsaved work is lost", "reboot",
       {"delay_s": 60, "message": "This machine restarts in 1 minute. Please save your work."}),
    _b("shutdown-5", "Shut down in 5 minutes", "They are warned first; unsaved work is lost", "shutdown",
       {"delay_s": 300, "message": "This machine shuts down in 5 minutes. Please save your work."}),
    _b("running-programs", "List running programs", "Every program running now, heaviest first", "process_list"),
    _b("health", "Check CPU, memory and disk", "How hard the machine is working now", "system_metrics"),
    _b("idle", "How long it has been idle", "Time since the last key press or mouse move", "idle_time"),
    _b("usb", "What is on its USB drives", "The files on any drive plugged in now", "usb_contents"),
    _b("close-browser-edge", "Close Microsoft Edge", "The browser closes; unsaved forms are lost", "kill_process", {"name": "msedge.exe"}),

    # --- scripts that only look ---------------------------------------------------------------------------------------------------------
    _ps("disk-space", "Free disk space", "Each drive, how much is free", r'''
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    "{0}`t{1:N1} GB free`tof {2:N1} GB" -f $_.DeviceID, ($_.FreeSpace / 1GB), ($_.Size / 1GB)
}''', "list"),
    _ps("installed-programs", "Installed programs", "Name, version and maker of each", r'''
$keys = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
Get-ItemProperty $keys -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -and -not $_.SystemComponent } |
    Sort-Object DisplayName -Unique | ForEach-Object { "{0}`t{1}`t{2}" -f $_.DisplayName, $_.DisplayVersion, $_.Publisher }''', "list", 120),
    _ps("uptime", "When it last started", "The last start, and how long it has been up", r'''
$os = Get-CimInstance Win32_OperatingSystem
$up = (Get-Date) - $os.LastBootUpTime
"Started {0:ddd d MMM, HH:mm}; up {1} days {2} hours" -f $os.LastBootUpTime, $up.Days, $up.Hours'''),
    _ps("windows-version", "Windows version", "Edition, version and build", r'''
$os = Get-CimInstance Win32_OperatingSystem
$v = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').DisplayVersion
"{0}, version {1} (build {2})" -f $os.Caption, $v, $os.BuildNumber'''),
    _ps("signed-in", "Who is signed in", "The account at the keyboard now", r'''
$u = (Get-CimInstance Win32_ComputerSystem).UserName
if ($u) { "$u is signed in" } else { "Nobody is signed in" }'''),
    _ps("needs-restart", "Does it need a restart", "Whether Windows is waiting to restart, and why", r'''
$why = @()
if (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') { $why += 'Windows components' }
if (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired') { $why += 'Windows Update' }
$sm = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -ErrorAction SilentlyContinue
if ($sm.PendingFileRenameOperations) { $why += 'files waiting to be replaced' }
if ($why) { "Needs a restart: " + ($why -join ', ') } else { "No restart needed" }'''),
    _ps("updates", "Latest Windows updates", "The last fifteen installed, newest first", r'''
Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 15 | ForEach-Object {
    "{0}`t{1}`t{2:d MMM yyyy}" -f $_.HotFixID, $_.Description, $_.InstalledOn
}''', "list", 120),
    _ps("antivirus", "Antivirus status", "Defender's protection, signatures and last scan", r'''
$s = Get-MpComputerStatus
$rt = if ($s.RealTimeProtectionEnabled) { 'on' } else { 'OFF' }
"Real-time protection {0}; signatures from {1:d MMM yyyy}; last quick scan {2:d MMM, HH:mm}" -f $rt, $s.AntivirusSignatureLastUpdated, $s.QuickScanEndTime'''),
    _ps("firewall", "Firewall status", "Each profile, on or off", r'''
Get-NetFirewallProfile | ForEach-Object { "{0}`t{1}" -f $_.Name, $(if ($_.Enabled) { 'on' } else { 'OFF' }) }''', "list"),
    _ps("ip-addresses", "Its network addresses", "Each adapter and its address", r'''
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' } | ForEach-Object {
    "{0}`t{1}/{2}`t{3}" -f $_.InterfaceAlias, $_.IPAddress, $_.PrefixLength, $_.PrefixOrigin
}''', "list"),
    _ps("connections", "Open network connections", "Which program talks to which address", r'''
$names = @{}
Get-Process | ForEach-Object { $names[$_.Id] = $_.ProcessName }
Get-NetTCPConnection -State Established | Where-Object { $_.RemoteAddress -notin '127.0.0.1', '::1' } | Sort-Object OwningProcess | ForEach-Object {
    "{0}`t{1}:{2}" -f $names[[int]$_.OwningProcess], $_.RemoteAddress, $_.RemotePort
}''', "list"),
    _ps("stopped-services", "Services that should be running", "Set to start by themselves, but stopped", r'''
Get-CimInstance Win32_Service -Filter "StartMode='Auto' AND State<>'Running'" | ForEach-Object { "{0}`t{1}" -f $_.DisplayName, $_.State }''', "list"),
    _ps("errors-today", "Errors in the last day", "Windows' own errors, newest first", r'''
$since = (Get-Date).AddDays(-1)
Get-WinEvent -FilterHashtable @{ LogName = 'System', 'Application'; Level = 1, 2; StartTime = $since } -MaxEvents 50 -ErrorAction SilentlyContinue | ForEach-Object {
    "{0:HH:mm}`t{1}`t{2}" -f $_.TimeCreated, $_.ProviderName, (($_.Message -split "`r?`n")[0])
}''', "list", 90),
    _ps("printers", "Printers and their queues", "Each printer, ready or not, and what waits", r'''
$jobs = @(Get-CimInstance Win32_PrintJob)
Get-CimInstance Win32_Printer | ForEach-Object {
    $p = $_
    $n = @($jobs | Where-Object { $_.Name -like ($p.Name + ',*') }).Count
    "{0}`t{1}`t{2} waiting" -f $p.Name, $(if ($p.WorkOffline) { 'offline' } else { 'ready' }), $n
}''', "list"),
    _ps("battery", "Battery", "How charged, and whether it is plugged in", r'''
$b = @(Get-CimInstance Win32_Battery)
if (-not $b.Count) { "No battery: a desktop" } else {
    foreach ($x in $b) {
        $st = if ($x.BatteryStatus -eq 1) { 'on battery' } elseif ($x.BatteryStatus -eq 2) { 'plugged in' } else { 'status ' + $x.BatteryStatus }
        "{0}% charged; {1}" -f $x.EstimatedChargeRemaining, $st
    }
}'''),
    _ps("startup-programs", "Programs that start with Windows", "Name, for whom, and what runs", r'''
Get-CimInstance Win32_StartupCommand | ForEach-Object { "{0}`t{1}`t{2}" -f $_.Name, $_.User, $_.Command }''', "list"),
    _ps("local-admins", "Who is an administrator", "The machine's own administrators", r'''
Get-LocalGroupMember -SID 'S-1-5-32-544' | ForEach-Object { "{0}`t{1}" -f $_.Name, $_.ObjectClass }''', "list"),
    _ps("shared-folders", "Folders it shares", "Each share and where it points", r'''
Get-SmbShare | Where-Object { $_.Name -notmatch '\$$' } | ForEach-Object { "{0}`t{1}" -f $_.Name, $_.Path }''', "list"),
    _py("largest-files", "Largest files in people's folders", "The twenty biggest under C:\\Users", r'''
import heapq
import os

top = []
for root, dirs, files in os.walk(r"C:\Users"):
    dirs[:] = [d for d in dirs if d not in ("AppData", "Application Data")]
    for name in files:
        path = os.path.join(root, name)
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if len(top) < 20:
            heapq.heappush(top, (size, path))
        elif size > top[0][0]:
            heapq.heapreplace(top, (size, path))
for size, path in sorted(top, reverse=True):
    print(f"{size / 1048576:,.0f} MB\t{path}")''', "list", 180),

    # --- scripts that change something, and say so --------------------------------------------------------------------------------------
    _ps("clear-temp", "Clear old temporary files", "Deletes temporary files older than a week", r'''
$cut = (Get-Date).AddDays(-7)
$n = 0
$bytes = 0
foreach ($dir in @($env:TEMP, "$env:windir\Temp")) {
    Get-ChildItem -Path $dir -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt $cut } | ForEach-Object {
        $len = $_.Length
        try { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop; $n++; $bytes += $len } catch { }
    }
}
"Removed {0} files, {1:N0} MB" -f $n, ($bytes / 1MB)''', "text", 300),
    _ps("empty-recycle-bin", "Empty the recycle bin", "What is in it is deleted for good", r'''
Clear-RecycleBin -Force -ErrorAction SilentlyContinue''', "status"),
    _ps("restart-spooler", "Restart the print spooler", "Unsticks a print queue; waiting jobs may be lost", r'''
$ErrorActionPreference = 'Stop'
Restart-Service -Name Spooler -Force''', "status"),
    _ps("flush-dns", "Clear the DNS cache", "Forgets the addresses it looked up", r'''
$ErrorActionPreference = 'Stop'
Clear-DnsClientCache''', "status"),
    _ps("sync-clock", "Set the clock from the network", "Asks the time server again", r'''
w32tm /resync | Out-Null
if ($LASTEXITCODE -ne 0) { exit 1 }''', "status"),
    _ps("refresh-policy", "Refresh group policy", "Applies the domain's settings again now", r'''
gpupdate /target:computer /force | Out-Null
if ($LASTEXITCODE -ne 0) { exit 1 }''', "status", 180),
)


def problems() -> list[str]:
    """What is wrong with the list itself: a key twice, a built-in's settings refused, a script the validator refuses. The tests ask; empty is right."""
    out, seen = [], set()
    for s in STARTER:
        if s.key in seen:
            out.append(f"{s.key}: the key is used twice")
        seen.add(s.key)
        if s.kind == "custom":
            res = custom_actions.validate(s.language or "", s.script or "")
            out += [f"{s.key}: {p}" for p in res.problems]
        else:
            try:
                check_params(s.builtin_type or "", s.params)
            except Exception as exc:  # noqa: BLE001 -- reported, not raised
                out.append(f"{s.key}: {exc}")
    return out


async def ensure(db: Any) -> int:
    """Add Falcon's actions that are not in the database yet (by key; archived ones count as there). Returns how many were added."""
    have = await db.control.falcon_keys()
    added = 0
    for s in STARTER:
        if s.key in have:
            continue
        if s.kind == "custom":
            if not custom_actions.validate(s.language or "", s.script or "").ok:
                continue
            await db.control.create_action(None, "custom", s.timeout_s, custom_script=s.script, custom_script_language=s.language,
                                           name=s.name, description=s.description, output_kind=s.output_kind, falcon_key=s.key)
        else:
            params = check_params(s.builtin_type or "", s.params)
            await db.control.create_action(None, s.kind, max(s.timeout_s, run_length(params) + SETTLE_SECONDS), builtin_type=s.builtin_type,
                                           name=s.name, description=s.description, params=params, falcon_key=s.key)
        added += 1
    return added
