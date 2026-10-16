"""The small Falcon program on a Worker's machine: one place to open and see what concerns you.

    python -m worker_client.program [--background]

It starts when the person signs in (a tray icon, nothing on screen) and opens from the icon or the Start-menu shortcut. Four tabs:
Today (what needs you, in a line or two), Tasks (what is assigned to you, with Start), Announcements (what your Admin and the Super User have sent)
and My machine (who your Admin is, and a button to ask for help). It never talks to the Engine: it asks the Worker service on this machine
(`worker_client/localapp.py`) and shows what comes back -- or, when the service is away, what it last knew, and says so.

It is not the console: its own small, calm look, plain words, and no controls beyond what a person at a desk is allowed to do (Start a task, ask for help).
Interruptions stay the overlays' job; this is somewhere you go on purpose, and a quiet note in the corner when something new arrives.
"""
