# Getting started

Two ways to run Falcon: **everything on one machine** (to develop or try it), and **a real network** (the Engine on
one machine, the IT Admins and the people's PCs on theirs). Settings live in `.env`; nothing is ever set in the
shell. Commands are shown for Windows; on Linux use `bin/python` instead of `Scripts\python.exe`.

**On every machine, beforehand:** Python 3.10+ and a clone (or copy) of this repository. On the Engine's machine,
PostgreSQL (16 or later). The virtual environments are made once per machine, one per package, and each has a
requirements file in the repository root. Run the install from the root of the clone:

| Machine | Environment | Install |
|---|---|---|
| the Engine | `environ-engine` | `pip install -r requirements-engine.txt` |
| an IT Admin | `environ-operator` | `pip install -r requirements-operator.txt` |
| a person's PC (a Worker) | `environ-worker` | `pip install -r requirements-worker.txt` (includes its small windows) |

---

## 1. Everything on one machine

```powershell
python -m venv environ-engine
environ-engine\Scripts\python.exe -m pip install -r requirements-engine.txt
environ-engine\Scripts\python.exe -m engine setup --admin-url postgresql://postgres:<postgres-password>@localhost:5432/postgres
```

`setup` prints each step and is safe to run again. It writes `.env`, makes the Engine's certificate, creates the
`falcon` role and the `falcon` / `falcon_test` databases, applies the schema, creates the master secret, makes the
first **IT Admin** in a department named IT (its id and key printed **once**) and writes them into this machine's Operator Client settings.
Without `--admin-url` it prints the SQL to run as a PostgreSQL superuser, and stops until the databases exist.
`--download-model` also fetches the local language model (~1.8 GB) used by Tasks.

```powershell
environ-engine\Scripts\python.exe -m engine                              # the Engine (leave it running)

python -m venv environ-operator
environ-operator\Scripts\python.exe -m pip install -r requirements-operator.txt
environ-operator\Scripts\python.exe -m operator_client --gui             # opens as the first IT Admin, nothing to type
```

Check it: `environ-engine\Scripts\python.exe -m pytest` -- every test should run (the header says *database tests ON*).

---

## 2. A real network

**Superseded 14 Nov 2026 by `docs/SEATS-AND-SETUP.md`** (Workers knock and are given seats; Admins sign in to the company account; one setup for everyone plus a signed company file). Kept until each part is replaced.

**Four Windows test machines (an Engine, an IT Admin, two Workers) on each kind of network** -- a network of its own inside an existing one,
the existing network as it is, or our own Wi-Fi -- are set up as `docs/NETWORK-TEST-SETUP.md` says. The steps below are the commands it uses.

### The picture

```
                        ┌──────────────────────────────┐
                        │  THE ENGINE  (one machine)   │   PostgreSQL, the master secret,
                        │  falcon.internal : 7400 TLS  │   engine.crt / engine.key
                        └──────────────┬───────────────┘
                                       │  TCP 7400, TLS, the certificate pinned
          ┌────────────────────────────┼─────────────────────────────┐
  ┌───────┴────────┐          ┌────────┴────────┐           ┌────────┴────────┐
  │ first IT Admin │          │ other IT Admins │           │  people's PCs   │
  │ Operator GUI   │          │  Operator GUI   │           │  Worker service │
  └────────────────┘          └─────────────────┘           └─────────────────┘
```

Every machine reaches the Engine by one name or address; every client carries a copy of **`engine.crt`** (the Engine's
certificate -- clients refuse an Engine that does not present it) and its **own client id + key** (issued once, when the
machine is registered).

### Step 1 -- the Engine

**With the installer (how it ships, on Windows):** install PostgreSQL first (postgresql.org's Windows installer; remember its superuser
password), then run **`falcon-engine-setup.exe`** as an administrator. It asks the names the PCs will use (keep `falcon.internal`), the first
IT Admin's PC name and PostgreSQL's superuser password, and does everything below by itself: certificate, database, first IT Admin, firewall,
the **FalconEngine** service (starts with Windows). It leaves, in `C:\ProgramData\Falcon Engine`: `falcon-client.json` (give it to the PCs'
setup.exe builds), `first-admin.txt` (the first IT Admin's id and key: keep them, then delete it) and `master.secret` (**back it up offline**).
Its log is `C:\ProgramData\Falcon Engine\logs\engine.log`; `python -m engine health` on that machine says whether it is well; it is
stopped and started from Services (`services.msc`) or `python -m engine service stop|start`. Silent: `falcon-engine-setup.exe /VERYSILENT
/ANSWERS=answers.json`. The steps below are the same by hand, from a clone.

On the machine that will run it (Windows, or Linux if it must be; it is the only machine with a database). On Windows, from an **elevated** PowerShell
in the Falcon folder, so setup can add the firewall rule:

1. Give it a fixed address on the network and a name the others can resolve (e.g. `falcon.internal`, or just its IP). On a test network
   the name is a line in each client's `hosts` file (`docs/NETWORK-TEST-SETUP.md`); a fixed address on Windows:

   ```powershell
   ipconfig                                                    # this network's adapter name, gateway and prefix
   New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.50.10 -PrefixLength 24 -DefaultGateway 192.168.50.1
   Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses 192.168.50.1
   ```

   (or reserve the address for this machine in the router's DHCP settings; `getmac /v` shows its MAC address)
2. Install PostgreSQL and make the environment (table above):

   ```powershell
   python -m venv environ-engine
   environ-engine\Scripts\python.exe -m pip install -r requirements-engine.txt
   ```
3. Run setup with **every name and address the clients will use**, so the certificate is valid for them (the **first** is the one written
   into the client bundle):

   ```powershell
   environ-engine\Scripts\python.exe -m engine setup --names falcon.internal --admin-url postgresql://postgres:<postgres-password>@localhost:5432/postgres --hostname IT-01 --no-operator-config --download-model
   ```

   The certificate is made once: a later `--names` changes nothing until `data\engine.crt` and `data\engine.key` are deleted, and then
   every client needs the new `engine.crt`. Choose the names first.

   `--hostname` is the **first IT Admin's workstation name** (not the Engine's); `--no-operator-config` because that
   Admin works from their own machine. Save the printed **client id + key** for step 2.
4. `.env` already listens on every network interface (`FALCON_ENGINE_HOST=0.0.0.0`, port `7400`). `python -m engine setup` opens
   **TCP 7400** in the host firewall:
   - **Windows:** a Windows Defender Firewall rule, *Falcon Engine (TCP 7400)*, for **private and domain networks only** (from an elevated
     prompt; otherwise it prints the `netsh` command to run). On a network Windows calls *Public* nothing reaches the Engine, so make this
     machine's network Private:

     ```powershell
     Get-NetConnectionProfile                                                    # NetworkCategory: Private or DomainAuthenticated
     Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private   # if it says Public (the adapter name ipconfig shows)
     ```
   - **Linux:** `ufw` or `firewalld`, whichever is running (as root; otherwise it prints the one command to run). Any other firewall is left
     alone and setup says so.

   With `--names`, setup also writes **`data\falcon-client.json`**: the first name, the port and the certificate (no key), the file every
   PC's installer is given, and prints the certificate's **fingerprint** to compare on each PC.
5. Start it: `environ-engine\Scripts\python.exe -m engine` and leave the window open (as a service in production -- Phase 9 packages
   this). On Windows keep the machine awake while it is the Engine: `powercfg /change standby-timeout-ac 0`.
6. **Back up `data/master.secret`** somewhere safe and offline. Every client key derives from it; lose it and every
   machine must be registered again.

Copy **`data/engine.crt`** (only the `.crt` -- never `engine.key` or `master.secret`) to a USB stick or share; every
client needs it.

**From every other machine, check it can reach the Engine** before installing anything there:

```powershell
Add-Content C:\Windows\System32\drivers\etc\hosts "`n192.168.50.10  falcon.internal"     # elevated; only when the name is not in the network's DNS
Test-NetConnection falcon.internal -Port 7400                                            # TcpTestSucceeded : True
environ-engine\Scripts\python.exe -m engine health falcon.internal:7400                 # on the Engine's machine: well, version, uptime, database
```

### Step 2 -- the first IT Admin's workstation

```powershell
python -m venv environ-operator
environ-operator\Scripts\python.exe -m pip install -r requirements-operator.txt
environ-operator\Scripts\python.exe -m operator_client --gui
```

On the connect screen: **Engine address** `falcon.internal : 7400`, **your client id** and **your key** from step 1,
and **Choose…** the `engine.crt` you copied. It is remembered on this machine.

### With licence codes

A licence comes with codes: admin codes and worker codes. Take them in once, in the TUI: `licence import <file.json>` (the file the licence
store hands over); `licences` lists them with how many machines each has let in. Then install each PC with its code (`setup.exe` asks for it,
or `--code`): it joins at once, as an IT Admin's workstation or a person's PC, and nobody confirms it. A worker joins the department its
code names, else "New machines"; an Admin joins IT. `licence revoke <id>` withdraws a code.

### Step 3 -- departments, and more IT Admins

Version 1 has IT Admins only (`docs/design/v1-it-admin.md`): every Admin reaches every department, and a department is a
label for grouping machines and people.

1. **Make each department** on **Manage → Departments**: name it, then click machines to move them in. (TUI: `dept add <name>`,
   `dept rename <id> <name>`, `pc move <pc_id> <department_id>`.)
2. **Another IT Admin** is never one click in the console. Install Falcon on their PC and let it in as a machine (step 4),
   then make that person an Admin from the TUI: `promote <account_id>` (their new key is shown **once**). The full steps
   for making an Admin are still being designed.
3. **When an Admin leaves**: `account offboard <id>`, then `account owns <id>` and `account handover <from> <to>` give what
   they owned to another Admin.

### Step 4 -- people's PCs (Workers)

1. An Admin opens **Machines → Registry** → **Register a machine** → types the PC's name (e.g. `OPS-15`).
   Its **client id + key** are shown **once**.
2. On that PC:

   ```powershell
   python -m venv environ-worker
   environ-worker\Scripts\python.exe -m pip install -r requirements-worker.txt
   environ-worker\Scripts\python.exe -m worker_client --engine falcon.internal:7400 --client-id <id> --client-key <key> --ca C:\path\to\engine.crt --watch C:\Users\<them>\Documents
   ```

   Everything is remembered (in `C:\ProgramData\Falcon\worker.json`); after the first run it starts with no options.
   It watches the folders given with `--watch` (repeatable) and relays file activity, runs actions, and shows the
   person's small windows ("R. Mensah is using this machine", a task given to them).

   To keep it running without anyone signed in, as a Windows service (once, from an elevated prompt, after the run above has remembered its settings):

   ```powershell
   environ-worker\Scripts\python.exe -m worker_client service install
   environ-worker\Scripts\python.exe -m worker_client service start
   ```

   It then starts with Windows and restarts itself; its log is `C:\ProgramData\Falcon\worker.log`. `service stop` / `uninstall` / `status` do the rest.

### Checking it works

- The Overview shows what waits on you; **Machines** lists every machine in every department, quiet when fine.
- A Worker that connected appears at its machine; opening it and entering shows its screen (the bar across the top says so).
- If a client cannot connect, its connect screen says which of three it is: the key does not match, the Engine cannot
  be reached (address, port 7400, firewall), or the certificate does not match (it was made without that name --
  re-run setup on the Engine with `--names`, delete `data/engine.crt` first, and copy the new one out).

### When a machine's key is lost

Open the machine (double-click it) → **Issue a new key**. The old key stops at once; enter the new one on that machine.

---

## Registering machines from the network

A Worker installed with the installer (`installers/README.md`) needs no key typed by hand: it asks the Engine to be registered, the
request waits under **Machines → Registry → Asking to join**, and an Admin lets it in by typing the short code shown on that PC's screen.
The key then goes to the PC by itself. Step 4 above is the by-hand way.

---

## Keeping it running

- **Is it well?** `python -m engine health [host:port]` asks the running Engine (before any sign-in, so a monitor needs no key): whether
  the database answers, how long it has run, how many machines are connected. Exit code 0 well, 1 something wrong, 2 not answering.
- **Back up the database:** `python -m engine backup [file]` (PostgreSQL's `pg_dump`; default `data/backups/falcon-<when>.dump`).
  Put it back with `python -m engine restore <file> --yes`, with the Engine stopped: what is in the database is replaced.
- **Back up the master secret apart, offline:** `data/master.secret` is not in a database backup. Without it no machine's key can be
  made again, and every machine would have to be registered anew.

## A server that cannot run the local model

Falcon's model runs on the Engine's own machine, and nothing leaves it. If that machine cannot run the model (too little memory, too slow), a Groq key
makes Groq answer what the local model could not. Add it to `.env` and restart the Engine:

```
FALCON_GROQ_API_KEY=<a key from console.groq.com>
```

Task descriptions then leave your network, so set it only where that is acceptable. Each use is on the audit trail (`llm.fallback`). Groq's free plan
refuses bursts: a refused question reaches the person as unclear, and nothing is lost. Groq retires models: when it does, the log says the fallback failed,
and `FALCON_GROQ_MODEL` is what to change.

