# The new product — start here

Written 15 Nov 2026, when Falcon was parked, for the first session that opens in the new product's repository. If you are reading this in
the Falcon repository itself, Falcon is parked (`PARKED.md`): do not build here.

## What it is

One product, forked from Falcon, for IT Admins: it watches what happens to a company's files on its Windows machines (hidden, copied out,
renamed away, sent to a drive, screenshotted, logs cleared, a machine going quiet), puts it together as **cases told in plain words**, and
lets an Admin protect what matters. It does not judge: it proposes, and a person decides ("propose, never silently resolve").

Decided by the user, 15 Nov 2026:
- **One product, not features under an umbrella.** Detective (the cases) and Restricted (what matters, marked) are not separate features
  or pages: to the Admin they are one job, "is anything we care about at risk, and what happened to it?". Two moments of one product:
  *setting up* (marking files and folders as restricted, done where the file is met: from a case, from a machine's files, or one small
  "what matters" list) and *every day* (one main view of cases; cases about marked content first, weighing more, the restricted tag in the
  case itself). Containment is a choice on a case plus one setting for how far it may go. Neither "Detective" nor "Restricted" is a page
  name. Different people for setting up and for cases, if a company wants it, is permissions inside the one product.
- **It watches everything and prioritises restricted content**; it is not limited to it.
- **Out of it:** Falcon's Task, Flow, Automation / Custom Actions and the Assistance leftovers. Flow's step templates and Task chains were
  dropped outright.
- **Kept from Falcon (the groundwork):** the protocol, auth and TLS, seats and the store (`docs/SEATS-AND-SETUP.md`, `docs/STORE-CONTRACT.md`),
  the installers for Windows and Linux with their own private PostgreSQL, the Global File Index with one identity for a file through rename,
  move and edit, the event spine, the audit trail, issues, the Worker's watching (Windows' own places, the machine snapshot), Detective and
  its local LLM wording rules, marks (Restricted), certificate renewal.
- **The GUI is not carried over.** The new product gets a new concept design made for it (a UI session, concept first, as Falcon's was),
  then QML built to it. Falcon's console and Worker pages are reference at most.
- **Screenshots and camera pictures as evidence** are features the company turns on as it sees fit: no legal gates, no lectures; state the
  technical facts (a camera's LED lights in hardware) and list every collection in the deployment guide and the staff notice.
- **Pricing:** yearly seat grants, Admin and Worker seats priced apart (suggested, not settled: Worker ~$40/yr, Admin ~$400/yr, one Admin
  seat included, 10-seat minimum); top-ups end on the main grant's date.

## Its name: Raven

**Raven** (the user, 16 Nov 2026). Nothing has been checked for trademarks or domains yet: do that before anything ships.

Code packages are generic (`engine`,
`worker_client`, `operator_client`, `common`), so the code does not wait for the rename. **The visible brand is renamed once, in one pass,
after the cuts and before anything ships** (`RAVEN-MAP.md`, section 8)**:** `falcon-*-setup.exe`, the services (FalconEngine, FalconPostgres, FalconWorker), the
folders (`C:\ProgramData\Falcon*`, `/opt/falcon`, `/var/lib/falcon*`, `/etc/falcon`), the `FALCON_*` settings, the certificate's organisation,
the Linux users (`falcon`, `falcon-pg`), the docs and pages. After a customer has installed it, renaming means migrating real machines.

## The proposal document

The full product proposal is the Claude Docs document "The new product: Detective, with Restricted under it"
(claude.ai/artifact/FuDY3bpPRvB6HRxc5Ai9Tj): containment's escalation ladder in its own section, what was "Discussed, not built yet", and
its open decisions at the end. It is read and written through the **Claude Docs connector**; a session without it cannot read it (ask the
user to paste it, or to use a session that has it). **It predates the one-product decision above**, and its title is the old shape: update
it to say one product, and rename it once the name is chosen.

Also carried in this repository: `docs/design/proposals-core-features.md` (habits, files made from restricted content with clipboard
fingerprints, the snapshot's BitLocker, printers, USB devices and healing: designed, not built), `docs/design/detective-*.md`.

## Forking: the steps (each needs the user's yes where it creates or publishes something)

1. **The user names the codename and the repository** (a new private GitHub repository under `khonello`, in its own folder `Raven`, in the
   same parent folder as `Falcon`, never inside it: the user, 16 Nov 2026). Creating the repository publishes something: ask first.
2. **Clone Falcon with its history** into that folder (`git clone https://github.com/khonello/Falcon <folder>`), point `origin` at the new
   repository (`git remote set-url origin <new>`), and push `main`. Falcon's own repository stays as it is, parked.
3. **Replace `CLAUDE.md`** with `docs/next-product/CLAUDE.md` (it already says what this product is and the user's standing rules), and
   remove `PARKED.md` from the fork. Commit.
4. **Memory does not follow a new folder.** Save the entries in `docs/next-product/MEMORY-CARRYOVER.md` as this project's memory in the
   first session, then tell the user they are saved.
5. **The user makes the virtual environments** (`environ-engine`, `environ-operator`, `environ-worker`): never make them yourself.
   PostgreSQL 18 is installed locally; make the fork its own databases (not `falcon` or `falcon_test*`: Falcon's), names the user agrees.
6. **Take out what is out of scope** (Task, Flow, Automation / Custom Actions, Assistance leftovers), in reviewed steps, the suite green
   after each (`scripts/test_batches.py`): **follow `docs/next-product/RAVEN-MAP.md`**, which says what goes where, file by file, in order. Falcon's QML stays until the new concept replaces it, then goes.
7. **Then the product itself:** reshape the Engine side as one product (cases first, marks as part of them), and in a separate UI session,
   the new concept design, then QML to it.
8. **The brand rename** to Raven (above).

## Left open from Falcon, still true here

- **The store** is not built (its own session, to `docs/STORE-CONTRACT.md`, device sign-in included). `STORE_URL` and the store's real
  public key in `common/store_keys.py` are empty until it exists. Until then: `scripts/store_stub.py` for tests and drills.
- **A code-signing certificate** for the setups, before shipping.
- **The four-machine network test** (`docs/NETWORK-TEST-SETUP.md`) needs the store, or a test-only build against the stub: the user's call.
- `docs/to-lookat.md`: open items to raise with the user at the start of a session.
