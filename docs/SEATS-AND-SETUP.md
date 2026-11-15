# Seats, setups and the store: how machines join Falcon

*Decided with the user, 14 Nov 2026. This is the source of truth for joining; the work follows it step by step (the order is at the end).
Anything that turns out to need a change goes back to the user before it is built. The store's side is in `docs/STORE-CONTRACT.md`; the reset
support can walk a company through is in `docs/SUPPORT-RESET.md`; the console page is in `docs/UI-WORK-FROM-ENGINE.md`.*

**Replaces:** the code a joining PC showed for an Admin to type (`enroll.confirm`), licence codes typed at setup (`licence.*`, `--code`), the
per-Engine `falcon-client.json` built into each setup, and `first-admin.txt` for the first Admin. Those stay in the code until each part below
replaces them, and are then removed.

---

## 1. The idea, in a sentence each

- **Workers knock; Admins give seats.** Every PC with the Worker installed keeps knocking at its Engine and is never let in by itself. Admins
  see who is knocking. An Admin gives a knocking PC a seat, and it is in. Taking the seat back cuts the PC off, and it knocks again.
- **Seats are bought in the store.** Buying more raises the count the Engine sees. Bought seats are never checked again.
- **Admins join by signing in to the company account** during the Admin setup, and taking a free Admin seat. Internet is required for it.
- **One Worker setup for every customer**, with a small **signed company file** beside it that says where the company's Engine is.
- **The Engine keeps a private PostgreSQL of its own.**
- **Certificates renew themselves**; nobody reinstalls.
- **No "reset everything" button.** Support walks a company through it.

## 2. Rules that must hold everywhere

1. **No secret in any file a person handles.** The setups and the company file hold none. Every PC gets its own key from the Engine, once,
   when it is seated (a Worker) or when its Admin claim is accepted (an Admin).
2. **Knocking grants nothing.** Only an Admin giving a seat, or a store-signed Admin claim, lets a machine in, and only while a seat of that
   kind is free.
3. **What a machine believes about its Engine is signed by the store** (the company file) or **arrives over the connection it already trusts**
   (a certificate rollover). A company file that was changed, or that points at another Engine, is refused.
4. **The store's signing key never leaves the store's server.** Falcon carries the store's public keys (`common/store_keys.py`) and checks
   every signature itself, with no internet.
5. **Seat counts come only from store-signed grants**, kept verbatim and checked each time they are read; a row edited by hand counts for nothing.
6. **The Engine stays platform-neutral**; only installers and the service are per platform (Windows ships; Linux is kept working).

## 3. The three setups

| Setup | Who runs it | What it asks | Internet |
|---|---|---|---|
| `falcon-engine-setup.exe` | once, on the Engine's machine | sign in to the company account; the names the PCs will use (`falcon.internal` by default); whether to fetch the model | required |
| `falcon-admin-setup.exe` | on each IT Admin's PC | sign in to the company account (the owner or an invited member); which Engine, if the company has more than one | required |
| `falcon-worker-setup.exe` + the company file | on each person's PC | nothing | not needed |

All three are the same files for every customer, downloaded from the store, and signed (a code-signing certificate, to be bought before
shipping, so Windows does not warn "unknown publisher").

## 4. The Engine setup, step by step

1. Check: Windows, an administrator, the payload intact.
2. Stop an older Engine service, if there is one (an upgrade).
3. Copy the code to `C:\Program Files\Falcon Engine\app`; make its runtime there from the payload's wheels.
4. Make the data folder `C:\ProgramData\Falcon Engine`, readable only by the system and administrators.
5. **Its own PostgreSQL** (section 9): the binaries in `C:\Program Files\Falcon Engine\pgsql`, the database in `C:\ProgramData\Falcon Engine\pgdata`,
   the **FalconPostgres** service, the `falcon` login and database with a password made here.
6. Write `falcon.env` (every setting, absolute paths, `FALCON_PG_BIN` naming the private PostgreSQL's tools).
7. `python -m engine setup --no-first-admin`: the certificate for the names, the schema, the master secret, the firewall rule. **No Admin is made here.**
8. **Sign in to the company account** (a browser opens; Google or email), choose or name the company, and **register this Engine**: its names,
   port and certificate. The store answers with this Engine's id, a token for it, and the signed company file; all three are kept in the data folder.
9. Install and start the **FalconEngine** service; wait until it answers.
10. Write the receipt. The last page says: "Now run the Admin setup on your IT Admin's PC."

## 5. The Admin setup, step by step

1. Install the program (the console and the service), as today.
2. **Sign in to the company account** in the browser that opens. The person must be the account's owner or a member the owner invited.
3. The setup lists the company's Engines (chosen at once if there is one) and shows the free Admin seats ("2 of 3 free"). No free seat: it says
   so and stops; seats are bought in the store.
4. The store issues an **Admin claim**, signed, for this PC (its name and hardware identity), valid for 10 minutes, and gives the Engine's signed
   company file.
5. The setup checks both signatures, writes the Engine's certificate, and hands the claim to the service.
6. The service knocks with the claim. The Engine checks it (its signature, that it names this Engine, that it is unexpired and unused, that an
   Admin seat is free) and gives this PC its key at once. The console is signed in as this Admin.

The very first Admin joins this way too: nothing else is needed, and there is no `first-admin.txt`.

## 6. The Worker: from install to seat, step by step

1. **Download the Worker setup** from the console's Machines page: one zip with `falcon-worker-setup.exe` and the company file (say
   `acme.falcon`). The same zip serves every PC for as long as the Engine keeps its names and certificate.
2. **Install**: run the setup with the company file beside it (or `/COMPANY=<path>` for Group Policy or Intune; `/VERYSILENT` for no
   window). The setup checks the company file's signature and refuses it if it was changed; it writes the Engine's certificate and address,
   and makes this PC's **install token**, kept in its private settings. Nothing is typed.
3. **Knock**: the service tells the Engine who it is (the install token, its name, Windows version, network card, hardware identity, who is
   signed in). The Engine keeps **one row per installed PC** and answers "waiting". The PC asks again after 5, 15, 30, 60 and 120 seconds,
   then every 2 minutes, for as long as it takes; the Engine also nudges it on its open connection the moment it is seated. The tray says
   "Waiting for a seat from your Admin". It reaches nothing else.
4. **Give a seat**: an Admin, on the Machines page, picks the knocking PC and **gives it a seat, choosing its department** (if no department
   exists, the default "New machines"). This needs a free Worker seat; with none, the button says so.
5. **In**: the Engine makes the PC's account and its own key, and the PC collects the key on its next knock (or at once, nudged). It is now an
   ordinary Worker.
6. **Take the seat back**: any Admin, on the Machines page. The Engine stops the PC's account, makes its key useless, and closes its connection.
   Its next sign-in is refused with the reason `no_seat`; the PC drops its key and **knocks again** with the same install token. Its history stays.

**Telling look-alike PCs apart** (there is no code any more): each knocking PC shows its name, who is signed in on it, its network address,
its hardware identity and when it first knocked. Two knocking PCs with the same name, or one hardware identity under two names, are flagged.

**Protections on knocking** (kept from today's joining): a limit per network address, and a machine that keeps asking oddly is flagged.
Knocks no longer expire; a PC knocks until it is seated or uninstalled.

## 7. Seats

- **Kinds**: Admin seats and Worker seats, counted separately.
- **Where the count comes from**: store-signed **grants**, each "N seats of a kind, from date to date". A purchase makes a grant; a renewal
  makes a new one. The Engine asks the store once a day (and when an Admin asks: TUI `seats refresh`) for grants it has not seen, and adds
  them. It never re-checks one it has.
- **Free seats** = seats in valid grants of that kind, minus those in use.
- **The end of a period**: issues are raised for the Admins 30, 7 and 1 days before a grant ends, and during its grace. After the end come
  **7 days of grace**; machines keep working. After the grace, if more seats are in use than valid grants cover, **the most recently given
  seats over the count are taken back**, audited and announced; those PCs knock again.
- **Admin seats**: any Admin may take back any Admin's seat; **the last Admin seat can never be taken**.

## 8. The company file

What it holds (signed by the store): the company, the Engine's id, the names and port the PCs use, and the Engine's certificate, or two
certificates during a rollover. No secret. Made by the store when the Engine registers and whenever its certificate changes; the Engine
keeps the latest, and the console downloads it from the Engine for the Worker zip.

## 9. The private PostgreSQL

- Program files in `C:\Program Files\Falcon Engine\pgsql`: **never on PATH**; no PGDATA or other environment setting; no entry under Apps.
- Data in `C:\ProgramData\Falcon Engine\pgdata`, readable only by the FalconPostgres service's own account, the system and administrators.
- Its own service, **FalconPostgres**, under the virtual account `NT SERVICE\FalconPostgres` (PostgreSQL refuses to run as an administrator).
- Listens on `localhost` only, on a free port that is not 5432; no firewall rule.
- `pg_hba.conf` lets in only the `falcon` login, to the `falcon` database, from this machine (scram-sha-256). Its superuser password is made
  at install and kept in the protected data folder (for upgrades); nobody types it.
- `engine backup` and `restore` use these tools (`FALCON_PG_BIN`), never another install's.
- A PostgreSQL the machine already has is never touched: no shared port, files, service, logins or settings.
- The uninstall removes the service and keeps the data unless `--purge-data`.
- An IT department that insists on its own server can give `--database-url` to the installer, on the command line only.

## 10. Certificate renewal

The Engine's certificate is valid for 10 years; renewal is rare, but a lapse would cut every machine off at once, so it is automatic:

1. A daily check. **60 days before the end** (or on TUI `cert renew`, which can also change the names): make the next certificate; register
   both with the store, which issues a company file holding both; push the new one to every connected machine, which adds it to the
   certificates it trusts.
2. **30 days before the end**: switch. New connections get the new certificate. Machines trust both until the old one expires.
3. A machine that was off the whole time needs the current zip run on it (its company file carries the new certificate).

## 11. The order of the work

| Step | What | Waits on |
|---|---|---|
| 0 | these documents | — |
| 1 | `docs/STORE-CONTRACT.md`, `common/ed25519.py` (stdlib verify, RFC 8032 vectors), `common/store_keys.py`, `scripts/store_stub.py` (done 14 Nov 2026) | — |
| 2 | the Engine: knocks, seats, grants, grace (migration 056), TUI commands (done 14 Nov 2026) | 1 |
| 3 | the Worker: knocking, the company file in the setup (done 15 Nov 2026) | 2 |
| 4 | the Admin claim, end to end against the store stub (done 15 Nov 2026; migration 057) | 1, 2 |
| 5 | the Engine setup: the private PostgreSQL, then store registration | a yes for the PostgreSQL binaries download (~300 MB) |
| 6 | certificate renewal | 2 |
| 7 | the Machines page, handed to the design session | 2 |
| 8 | the old joining code removed; docs; drills | 2–6 |

Outside this session: the store itself (the `store/` session, built to `docs/STORE-CONTRACT.md`); the Paddle account (the user); a
code-signing certificate for the setups (to buy before shipping).

## 12. How each step is checked

- Unit tests: Ed25519 against RFC 8032; signed documents (good, changed, wrong key, wrong Engine, expired claim, claim used twice); seat
  counting, grace and the over-count take-back; one knock row per install token; duplicates flagged; `no_seat` at sign-in; renewal timing.
- Real drills, elevated, on the development PC, never touching its own PostgreSQL: a Worker from setup to knock to seat to taken back; an Admin
  setup against the store stub; the private PostgreSQL installed and removed; a renewal with a short-lived certificate rolling a connected
  machine over without a reinstall. `scripts/update_drill.py` still passes; the Linux checks in WSL still pass.
- Before any step is committed: the full suite (without the GUI files while the design session's QML is in flux), `ruff check .`, and WSL.
