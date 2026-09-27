# Getting started

Two ways to run Falcon: **everything on one machine** (to develop or try it), and **a real network** (the Engine on
one machine, the Super User, Admins and their people on theirs). Settings live in `.env`; nothing is ever set in the
shell. Commands are shown for Windows; on Linux use `bin/python` instead of `Scripts\python.exe`.

**On every machine, beforehand:** Python 3.10+ and a clone (or copy) of this repository. On the Engine's machine,
PostgreSQL (16 or later). The virtual environments are made once per machine, one per package:

| Machine | Environment | Install |
|---|---|---|
| the Engine | `environ-engine` | `pip install -e ".[engine,dev]"` |
| the Super User, an Admin | `environ-operator` | `pip install -e ".[tui,gui]"` |
| a person's PC (a Worker) | `environ-worker` | `pip install -e ".[worker,worker-ui]"` (`worker-ui` = its small windows) |

---

## 1. Everything on one machine

```powershell
python -m venv environ-engine
environ-engine\Scripts\python.exe -m pip install -e ".[engine,dev,gui]"
environ-engine\Scripts\python.exe -m engine setup --admin-url postgresql://postgres:<postgres-password>@localhost:5432/postgres
```

`setup` prints each step and is safe to run again. It writes `.env`, makes the Engine's certificate, creates the
`falcon` role and the `falcon` / `falcon_test` databases, applies the schema, creates the master secret, makes the
first **Super User** (its id and key printed **once**) and writes them into this machine's Operator Client settings.
Without `--admin-url` it prints the SQL to run as a PostgreSQL superuser, and stops until the databases exist.
`--download-model` also fetches the local language model (~640 MB) used by Tasks.

```powershell
environ-engine\Scripts\python.exe -m engine                              # the Engine (leave it running)

python -m venv environ-operator
environ-operator\Scripts\python.exe -m pip install -e ".[tui,gui]"
environ-operator\Scripts\python.exe -m operator_client --gui             # opens as the Super User, nothing to type
```

Check it: `environ-engine\Scripts\python.exe -m pytest` -- every test should run (the header says *database tests ON*).

---

## 2. A real network

### The picture

```
                        ┌──────────────────────────────┐
                        │  THE ENGINE  (one machine)   │   PostgreSQL, the master secret,
                        │  falcon.internal : 7400 TLS  │   engine.crt / engine.key
                        └──────────────┬───────────────┘
                                       │  TCP 7400, TLS, the certificate pinned
          ┌────────────────────────────┼─────────────────────────────┐
  ┌───────┴────────┐          ┌────────┴────────┐           ┌────────┴────────┐
  │ Super User PC  │          │  Admin PCs      │           │  people's PCs   │
  │ Operator GUI   │          │  Operator GUI   │           │  Worker service │
  └────────────────┘          └─────────────────┘           └─────────────────┘
```

Every machine reaches the Engine by one name or address; every client carries a copy of **`engine.crt`** (the Engine's
certificate -- clients refuse an Engine that does not present it) and its **own client id + key** (issued once, when the
machine is registered).

### Step 1 -- the Engine

On the machine that will run it (Linux or Windows; it is the only machine with a database):

1. Give it a fixed address on the network and a name the others can resolve (e.g. `falcon.internal`, or just its IP).
2. Install PostgreSQL and make the environment (table above).
3. Run setup with **every name and address the clients will use**, so the certificate is valid for them:

   ```
   environ-engine/bin/python -m engine setup --names falcon.internal,192.168.1.20 --admin-url postgresql://postgres:<postgres-password>@localhost:5432/postgres --hostname SU-PC --no-operator-config --download-model
   ```

   `--hostname` is the **Super User's workstation name** (not the Engine's); `--no-operator-config` because the Super
   User works from their own machine. Save the printed **client id + key** for step 2.
4. `.env` already listens on every network interface (`FALCON_ENGINE_HOST=0.0.0.0`, port `7400`). Open **TCP 7400**
   in the machine's firewall for the local network.
5. Start it: `environ-engine/bin/python -m engine` (as a service in production -- Phase 9 packages this).
6. **Back up `data/master.secret`** somewhere safe and offline. Every client key derives from it; lose it and every
   machine must be registered again.

Copy **`data/engine.crt`** (only the `.crt` -- never `engine.key` or `master.secret`) to a USB stick or share; every
client needs it.

### Step 2 -- the Super User's workstation

```powershell
python -m venv environ-operator
environ-operator\Scripts\python.exe -m pip install -e ".[tui,gui]"
environ-operator\Scripts\python.exe -m operator_client --gui
```

On the connect screen: **Engine address** `falcon.internal : 7400`, **your client id** and **your key** from step 1,
and **Choose…** the `engine.crt` you copied. It is remembered on this machine.

### Step 3 -- departments and Admins

In the Super User's window:

1. **Make each department** (Authority → New department).
2. **Give each department an Admin**: open the department → *Who governs* → **Give it an Admin** → type the Admin's
   workstation name. The Admin's **client id + key** are shown **once** -- write them down for that machine.
3. On each Admin's workstation: the same as step 2, with *their* id and key.

### Step 4 -- people's PCs (Workers)

1. An Admin (or the Super User) opens the department → **Register a machine** → types the PC's name (e.g. `OPS-15`).
   Its **client id + key** are shown **once**.
2. On that PC:

   ```powershell
   python -m venv environ-worker
   environ-worker\Scripts\python.exe -m pip install -e ".[worker,worker-ui]"
   environ-worker\Scripts\python.exe -m worker_client --engine falcon.internal:7400 --client-id <id> --client-key <key> --ca C:\path\to\engine.crt --watch C:\Users\<them>\Documents
   ```

   Everything is remembered (in `C:\ProgramData\Falcon\worker.json`); after the first run it starts with no options.
   It watches the folders given with `--watch` (repeatable) and relays file activity, runs actions, and shows the
   person's small windows ("R. Mensah is using this machine", a task given to them).

### Checking it works

- The Super User's **Must see** shows every department; a department shows its machines, quiet when fine.
- A Worker that connected appears at its machine; double-clicking it enters (the bar across the top says so).
- If a client cannot connect, its connect screen says which of three it is: the key does not match, the Engine cannot
  be reached (address, port 7400, firewall), or the certificate does not match (it was made without that name --
  re-run setup on the Engine with `--names`, delete `data/engine.crt` first, and copy the new one out).

### When a machine's key is lost

Open the machine (double-click it) → **Issue a new key**. The old key stops at once; enter the new one on that machine.

---

## Coming: registering machines from the network

Typing each PC's name and copying its key by hand is the step that stings at scale. The agreed replacement is in
`design/ENGINE-WORK.md` (item 15), not built yet: the installed agent finds the Engine on the local network and asks to
be registered; the request waits in the department's **"Waiting to be registered"** list; the Admin confirms it by
typing a short **pairing code** shown on that PC's screen; the key then goes to the PC by itself. Until then, Step 4
above is the way.
