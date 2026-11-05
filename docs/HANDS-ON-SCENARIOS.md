# Hands-on scenarios

Four scenarios to try by hand, to see the system really work: Task, Restricted, Flow, Detective. Every command here was run on this machine on 5 Nov 2026, and each "you should see" is what it showed, with Notepad and File Explorer's parts done by a script: doing those by hand is the point of your test.

All three "machines" run on this one PC, each with its own folders. That is the same code and the same messages as three PCs; a flow between two real PCs is still in `docs/VM-TEST-PLAN.md`.

## Before you start (about 2 minutes)

Use **elevated** PowerShell windows (Run as administrator): the sign that a file was opened comes from Windows' own file trace, which needs it. From the Falcon folder:

**Window 1, the Engine.** Leave it running.

```powershell
environ-engine\Scripts\python.exe -m engine
```

**Window 2, the machines.** Wait for `The machines are running.` Leave it running. It builds everything under `data\hands-on\` fresh each time, and clears earlier marks and Detective cases, so what you see is only what you do.

```powershell
environ-operator\Scripts\python.exe scripts\hands_on.py
```

It prints each machine's numbers. These steps use the usual ones (WS-D1 is account 7, machine 7; WS-D2 is machine 8). If yours differ, use yours.

**Window 3, you, the Admin.** Run this once; the commands below are typed at its prompt.

```powershell
environ-operator\Scripts\python.exe -m operator_client --config data\admin.json --connect
```

`--config data\admin.json` matters: this PC's default console settings still point at the old Super User account, which is refused, as it should be.

`<F>` below means the full path to `data\hands-on`, as window 2 printed it. Falcon's own files show up in a moment; allow about 10 seconds after each action.

---

## 1. Task: is the work really seen?

The file tracked: `<F>\WS-D1\Documents\sales.txt`. The program: Notepad, or anything else that opens a text file, because Falcon follows the file, not the program.

| Do | You should see |
|---|---|
| `task propose 7 Update sales.txt by Friday` | One row: file, update, `sales.txt`, with a `file_index_id` (it found the real file). `deadline (final): 'by Friday'` and the date. Takes about 15 seconds: the local model is reading it. |
| `task create` | `task <id> created`. Note the id. |
| `task stack <id>` | `sales.txt`, status `pending`. |
| Open `sales.txt` in Notepad. Look, change nothing, close it. | |
| `task <id>` | Under **recent signals**: `file_opened`. The stack still says `pending`: opening a file is a sign, not proof. |
| Open it again, add a line, save. | |
| `task stack <id>` | `passed`, and `file_modified` under signals in `task <id>`. |
| `task verify <id> complete` | It closes. **Only this closes a task**: a passed check never does. |

**Also try:** `task propose 7 Does this work, testing`. It should say this is not work to give anyone and offer an example, and it should not make a task. `task help` shows the guidance.

---

## 2. Restricted: is a file kept where it belongs?

The file tracked: `<F>\ADM-01\Restricted\payroll.txt`, on the Admin's workstation. Marking only works on your own workstation.

| Do | You should see |
|---|---|
| `mark <F>\ADM-01\Restricted\payroll.txt keep=path` | `kept to only in its place`. |
| `marks` | One mark, `Only in its place`, 0 copies. |
| In File Explorer, copy `payroll.txt` into `<F>\ADM-01\Other`. Rename the copy to `pay-copy.txt`. | |
| `issues type=file` | An open issue on ADM-01, **medium**: a copy elsewhere on the same PC. It was matched by what is inside the file, so the new name does not hide it. |
| `issue <id>` | Where it was found, and three choices: `delete`, `rule`, `allow`. |
| `issue act <id> delete` | It says `Waiting`, the copy really goes from `Other`, and a moment later the issue is gone from the open list. |
| Copy `payroll.txt` into `<F>\WS-D1\Elsewhere`. | |
| `issues type=file` | A new issue on WS-D1, **high**: it left the machine it was kept to. |
| Change a word in the *original* and save. Then copy it to `Other` again. | Still caught: the mark remembers every version. |

**Also try:** `mark remove <mark_id>` when you are done. Its open issues close, and the history stays.

---

## 3. Flow: does a file arrive, changed as asked?

The folders: `<F>\WS-D1\Outbox` goes to `<F>\WS-D2\Inbox`, as PDF.

| Do | You should see |
|---|---|
| `flow create src=7:<F>\WS-D1\Outbox dest=8:<F>\WS-D2\Inbox@0 stage=conversion.to_pdf:if_not=copy` | The flow, with its destination's check `passed` and its `stage` filled in. **The `@0` matters:** it puts the destination after the step. Without it the file arrives unconverted. |
| In Notepad, save a file `letter.txt` in `Outbox`. | `letter.pdf` in `Inbox`, a real PDF: open it. |
| Save `sheet.xlsx` in `Outbox` (an empty file named that is enough). | It arrives as it is: this PC has no Office or LibreOffice, and the flow does not stop for it. |
| Edit `letter.txt` and save. | `letter.pdf` updates. |
| Edit `letter.pdf` in `Inbox` yourself (or replace it), then edit `letter.txt` again. | Your edit is kept beside the new one: a flow never overwrites what it did not write. |
| `flow pause <id>`, save a new file in `Outbox`. | Nothing arrives. |
| `flow resume <id>` | It arrives now. |

`flow steps` lists every step there is. If `flow create` says the destination collides with existing content, empty `Inbox` first: that is the check doing its job.

---

## 4. Detective: does it notice, and tell the difference?

The files: 60 contracts in `<F>\WS-D1\Documents\Old`. In a **fourth window**, from the Falcon folder, run the `hands_on.py` commands below.

| Do | You should see |
|---|---|
| In File Explorer, select everything in `Old`, delete it. | |
| `detective noted` | A case on WS-D1. If Falcon judged it done **by hand**, it is level `noted`, kept quietly and off the plain `detective` list, because a person deleting sixty files can be a clean-up. If it says **not by hand**, it is `urgent`. Tell me which you get: the same PowerShell delete was read both ways in rehearsal, and File Explorer was not tried. |
| `environ-operator\Scripts\python.exe scripts\hands_on.py refill`, wait 10 seconds, then `...hands_on.py wipe` | |
| `detective` | A case on WS-D1, `urgent`, Wrecking things: "**not by hand**". A program did it. |
| `detective case <id>` | The story in order, what makes it look bad, and what could make it harmless. It says *Detective's reading of the evidence, not proof*. |
| `detective review <id> dismissed it was a test` | `recorded`. |
| `refill`, wait 10 seconds, `wipe` again, then `detective status=open` | **A new case.** One false alarm must not blind it. This was a real bug until 5 Nov 2026, and was found by doing exactly this. |

**With a USB stick (not rehearsed: none was to hand):** in `Documents`, copy several files into a new folder, zip it, plug in the stick, copy the zip to it, then delete the zip. Run `detective noted` and tell me what it shows. This is the first real run of that path.

**To see the whole leak story without a stick:** `scripts\detective_demo.py --list` plays a scripted person. It sends messages only and touches no files.

---

## When you are done

Ctrl+C in windows 2 and 1. If something does not match, the most useful things to send are the command, what it showed, and `data\drill\<machine>\worker.log`.

**What this cannot show:** Word, Excel and PowerPoint (not installed here), two separate PCs, the Worker's windows and tray on a real desktop (these run without them), and a second Windows user being refused a Private file. Those are in `docs/VM-TEST-PLAN.md`.
