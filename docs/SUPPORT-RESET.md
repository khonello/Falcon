# Support procedure: starting a company's Falcon again after a compromise

*14 Nov 2026. Falcon has no "reset everything" button (the user: it is too dangerous to put in the product). When a company believes its
Engine's keys were stolen (the Engine's machine was broken into, a backup of its data folder leaked), support walks them through this. It
takes every machine offline until it is set up again, so it is done only when that is the lesser harm.*

## Why each step is needed

What a thief could hold: the Engine's **certificate key** (to pose as the Engine) and its **master secret** (to make any machine's key).
Both live only in `C:\ProgramData\Falcon Engine`. Replacing them makes everything made from them useless, including every copy of the
old Worker zip.

## The steps

1. **Confirm who is asking.** Only the company account's owner, signed in to the store, may start it. Support records the request and the reason.
2. **Back up what is worth keeping** (with the company): `python -m engine backup` on the Engine machine, kept offline. The data the
   company owns (tasks, flows, the audit trail) survives; the keys do not.
3. **Revoke the old Engine in the store** (support, on the store's admin side): its company files and its engine token stop being accepted
   for anything new; grants move to the new Engine when it registers.
4. **Reinstall the Engine with a fresh data folder**: uninstall with `--purge-data` (the database is kept), then run
   `falcon-engine-setup.exe` again. A new certificate and a new master secret are made, and the Engine registers again.
5. **Restore the data** if the company wants it: `python -m engine restore <file> --yes`.
6. **Every machine is set up again**: the old keys no longer work, so each PC runs the current Worker zip (Machines, Download Worker setup),
   knocks, and is given its seat again. Each Admin runs the Admin setup and signs in.
7. **Close the case** with the company: what was found, what was replaced, when the last machine was back.
