# VM test plan (Hyper-V, on a machine with enough memory)

What can only be proved on separate machines. Everything else has been run on one PC against real Worker processes (`scripts/live_drill.py`, `tests/`).

## The machines

The host that holds the VMs needs about 14 GB free. Three guests are enough; a fourth is optional.

| Guest | Role | Memory | Notes |
|---|---|---|---|
| `falcon-engine` | the Engine (Linux, Ubuntu Server or the netinst you have) | 2 GB, 2 vCPU | PostgreSQL on it; the model (1.8 GB) lives on its disk |
| `pc-a` | a person's PC (Windows 11) | 4 GB, 2 vCPU | the Flow source |
| `pc-b` | a person's PC (Windows 11) | 4 GB, 2 vCPU | the Flow destination |
| `admin-1` (optional) | an Admin's workstation | 4 GB | the console + the Worker pieces |

Use an **external** (bridged) switch so the guests reach each other and the host, and give the Engine a fixed address. The Super User's console can run on the host.

## Order

1. **Engine:** copy the repository (or the `.deb` from `installers/engine/build_deb.sh`) in; `sudo falcon-engine-install --names <its address> --hostname <host name>`; note the fingerprint and `falcon-client.json`; copy the first Super User's id and key off the box.
2. **Host:** `installers.windows.install --role superuser --bundle falcon-client.json --fingerprint <it> --client-id ... --client-key-file ...`; open the console: it connects by itself.
3. **admin-1 (or the host):** `--role admin`; the Super User confirms its code (Registry); the Admin's console signs in through the service. As a **standard user** (not administrator) on that machine, open the console: it must connect (the signing pipe's access rules).
4. **pc-a, pc-b:** `--role worker`; each shows a code; the Admin confirms each (Registry, or the TUI `enroll confirm`).

## What to try on separate machines

- **Flow between two PCs:** an Admin makes a flow from a folder on `pc-a` to one on `pc-b` (New flow); drop files, a 20 MB file, a file written slowly; edit at the destination and change at the source (a `-modified` copy must appear); put a different file of the same name at the destination first (the collision question appears; nothing is overwritten); delete at the source (the destination keeps its copy) and bring it back.
- **Away and back (proactive):** shut `pc-b` down, change files at the source, start `pc-b`: it is caught up with no action. Shut `pc-a` down, change its files while off, start it: the destination receives them. Stop the Engine for two minutes while files change on both: after it returns, everything converges.
- **Restricted across machines:** mark a file on `admin-1`; copy it to `pc-a` by USB or share (an issue appears, owned by the marker); rename and move the original (no issue); "Delete this copy" removes it from `pc-a`.
- **Task:** give `pc-a` a task by typing it in the console (the model reads it); do the work on `pc-a` (create the file, open it in a program); the checks pass; only the Admin completes it.
- **Session window with a second machine watching:** enter `pc-a` from `admin-1`'s console in See and in Control mode; type and click; the overlay shows on `pc-a`'s own screen.
- **Overlays:** `pc-a` shows the blocked card and the viewing bar; none appear on `admin-1` for being entered except its own overlay.
- **Update and uninstall:** run an installer again over an installed machine (it keeps its key); uninstall one (the program goes, the key stays).

## Record

Run `python scripts/live_drill.py flow|restricted|task|gui|forms` from the host against the Engine for the single-machine checks (they need Worker processes on the same PC as the drill, so they do not replace the above).

## The Falcon program, announcements, emergencies (added 16 Oct 2026)

On a Worker VM (installed with the Windows installer, signed in as a normal user):
1. After sign-in the Falcon tray icon is there with no window. Click it: the window opens on Today. Click the Start-menu "Falcon" shortcut while it is open: it comes forward, no second copy.
2. From the Admin console, give this person a task: its window appears once. Close it without Start. The tray icon shows a count; after the interval a small note appears in the corner and goes by itself; it never takes the keyboard.
3. Send an announcement to the department: a corner note, the Announcements tab shows it, the count on the icon goes up and clears when the tab is opened.
4. Send an emergency: the screen is covered until "I have read this"; it is still in the Announcements tab. Restart the Worker service before reading it: it is shown again.
5. Stop the Worker service: the program says it cannot reach the service and keeps showing what it last knew.
6. My machine → Ask for help pings the Admin.
7. Another Windows user on the same machine (fast user switching): each gets their own program.
