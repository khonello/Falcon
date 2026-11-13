# Network test setup: four Windows machines, three kinds of network

*Written 13 Nov 2026 for the first test on real machines, outside any VM. The commands for each machine are in `GETTING-STARTED.md`; this page says
how the four machines are put on each kind of network. Packaging (`setup.exe`) will replace the "once on every machine" steps; the network part stays.*

## The machines

| Machine | Name in these steps | Runs |
|---|---|---|
| The Engine | `ENG-01` | PostgreSQL, the Engine (`python -m engine`), the local model |
| The IT Admin | `IT-01` | the console (`python -m operator_client --gui`) |
| Worker 1 | `WS-01` | the Worker (`python -m worker_client`) |
| Worker 2 | `WS-02` | the Worker |

All four run Windows. Only `ENG-01` has a database. Each of the other three opens **one** connection, to `ENG-01` on **TCP 7400** (TLS, with
the Engine's certificate pinned), and nothing else: no machine needs to reach another, and nothing reaches the clients.

## The one idea: the Engine is called `falcon.internal` everywhere

The certificate is made once, for the **name** `falcon.internal`. Every client reaches the Engine by that name, and on each network one line
in each client's `hosts` file says which address the name has there. Moving the four machines from one kind of network to another then
changes **one line on three machines**, and no certificate is ever remade or handed out again.

(Remaking the certificate means giving every machine the new one: avoid it. If you would rather use plain addresses, list every one you
will use in `--names` the first time: `--names falcon.internal,192.168.50.10,192.168.8.10,192.168.137.1`.)

## Once, on every machine (needs the internet: do it before case 3)

1. **ENG-01**, from an elevated PowerShell, in the Falcon folder (full commands in `GETTING-STARTED.md`, section 2, step 1):
   PostgreSQL installed; `environ-engine` made and filled; then
   `environ-engine\Scripts\python.exe -m engine setup --names falcon.internal --hostname IT-01 --no-operator-config --admin-url postgresql://postgres:<password>@localhost:5432/postgres --download-model`.
   It makes the certificate for `falcon.internal`, the databases, the first IT Admin for `IT-01` (its **client id + key are printed once**:
   keep them), opens TCP 7400 in Windows Defender Firewall for private and domain networks, and writes `data\falcon-client.json`.
2. **ENG-01** never sleeps while it is the Engine: `powercfg /change standby-timeout-ac 0`.
3. **Copy `data\engine.crt`** (only that file) to a USB stick, for the three clients.
4. **IT-01, WS-01, WS-02:** Python 3.10, the Falcon folder, and `environ-operator` (IT-01) or `environ-worker` (WS-01, WS-02) made and filled
   (`GETTING-STARTED.md`, section 2, steps 2 and 4). Copy `engine.crt` to `C:\Falcon\engine.crt` on each.

## On whichever network: three checks

On **ENG-01**:

```powershell
ipconfig                                                    # the Engine's address on this network (IPv4 Address)
Get-NetConnectionProfile                                    # NetworkCategory must be Private (or DomainAuthenticated), not Public
Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private     # if it said Public (use the name ipconfig shows, e.g. "Ethernet")
```

The firewall rule is for private and domain networks only, on purpose: on a network Windows calls Public, nothing reaches the Engine.

On **IT-01, WS-01 and WS-02**, from an elevated PowerShell, with the Engine's address from `ipconfig`:

```powershell
Add-Content C:\Windows\System32\drivers\etc\hosts "`n192.168.50.10  falcon.internal"     # the Engine's address on THIS network
Test-NetConnection falcon.internal -Port 7400                                            # TcpTestSucceeded : True
```

When the machines move to another network, edit that line (`notepad C:\Windows\System32\drivers\etc\hosts`) rather than adding a second one.
Then start the console on IT-01 and the Worker on WS-01 and WS-02 as `GETTING-STARTED.md` says, with **Engine address** `falcon.internal : 7400`.

---

## Case 1: a network of its own, inside an existing one

**What it is:** a small router of our own, its internet port plugged into the existing network, its other ports (and its Wi-Fi) for the four
machines. The four are on a subnet of their own, say `192.168.50.0/24`; they reach the internet through the existing network, and nothing on the
existing network can reach them (the router's NAT keeps them apart). The existing network's people need do nothing.

*(The same thing done by the existing network's IT staff, with a VLAN of its own on their switches, works the same way: ask them for the
subnet, a fixed address for ENG-01, and that the four may reach each other on TCP 7400.)*

1. Plug the router's **WAN / internet** port into a socket of the existing network. Set its LAN to `192.168.50.1/24` (most routers: Network or
   LAN settings) and its DHCP to hand out `192.168.50.100`–`192.168.50.199`.
2. Connect the four machines to it (cable or its Wi-Fi). Turn **off** anything called "AP isolation", "client isolation" or "guest network" for
   the network they use: it stops machines reaching each other.
3. **A fixed address for ENG-01:** in the router's DHCP settings, reserve `192.168.50.10` for ENG-01's MAC address (`getmac /v` on ENG-01 shows it).
   Or set it on ENG-01 itself, outside the DHCP range:
   ```powershell
   New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.50.10 -PrefixLength 24 -DefaultGateway 192.168.50.1
   Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses 192.168.50.1
   ```
4. The three checks above, with `192.168.50.10` in the hosts line.

## Case 2: the existing network as it is

**What it is:** the four machines join the office (or home) network like any other PC; the Engine is one more machine on it.

1. Ask whoever runs the network for **a fixed address for ENG-01** (a DHCP reservation), say `192.168.1.50`. With no one to ask, set one on
   ENG-01 outside the router's DHCP range, as in case 1 step 3, with that network's gateway and prefix (`ipconfig` shows them).
2. Make sure the four are on the **same network and not a guest one**: guest Wi-Fi and "client isolation" stop machines reaching each other.
   If IT-01 or a Worker sits on another subnet (another floor, a VPN), the router or firewall between must let TCP 7400 through to ENG-01.
3. If the network has its own DNS (a company domain), IT can add `falcon.internal` (or `falcon.<company>`) pointing at ENG-01; then the hosts
   lines are not needed, but the name must be one the certificate was made for (`--names`).
4. The three checks above, with ENG-01's address in the hosts line.

## Case 3: our own Wi-Fi, for testing

**What it is:** a network that is only the four machines, with no internet. Do the "once on every machine" steps first, while there is internet.

**Recommended: a travel router** (a small battery or USB-powered Wi-Fi router), connected to nothing:

1. Power it on; give it a network name and a password. Its address is usually `192.168.8.1`; it hands out `192.168.8.x`.
2. Connect all four machines to its Wi-Fi.
3. Reserve `192.168.8.10` for ENG-01 in its DHCP settings (or set it on ENG-01 as in case 1 step 3, with gateway `192.168.8.1`).
4. The three checks above, with `192.168.8.10` in the hosts line. Windows may call a network with no internet "Public": set it to Private on ENG-01.

**Without a router: ENG-01's own Mobile Hotspot.**

1. On ENG-01: **Settings → Network & internet → Mobile hotspot**, set a name and password, turn it on. ENG-01 is then always `192.168.137.1`.
2. Connect IT-01, WS-01 and WS-02 to that Wi-Fi.
3. The three checks above, with `192.168.137.1` in the hosts line (on ENG-01, the hotspot's network is the one to make Private).

Limits: at most 8 machines; and Windows may refuse to turn the hotspot on when ENG-01 has no connection of its own to share. Then use the travel
router.

---

## When it does not connect

| What you see | What it is | What to do |
|---|---|---|
| `Test-NetConnection` fails, `PingSucceeded` false too | not on the same network, or isolation | same Wi-Fi / router? turn off client isolation |
| `PingSucceeded` true, `TcpTestSucceeded` false | the Engine is not running, or the port is shut | start the Engine; on ENG-01 the network must be Private; re-run `engine setup` from an elevated prompt for the firewall rule |
| it connects from ENG-01 itself only | the Engine listens on localhost only | `.env` must have `FALCON_ENGINE_HOST=0.0.0.0` |
| the console says the certificate does not match | the certificate was made without `falcon.internal`, or the client has another one | copy ENG-01's current `data\engine.crt` to the client |
| it worked, then stopped after a move | the hosts line still has the old network's address | edit the line |
