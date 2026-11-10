# Hands-on scenarios

*All four were run end to end on 5 Nov 2026 with real Notepad and File Explorer, driven by keystroke, and passed. Copying out was tried on a real USB stick and a real USB hard disk.*

*On 10 Nov 2026 the user copied a restricted file by hand three times in File Explorer (to another folder, to the USB hard disk, to a pendrive), copying other text in between. Each copy raised its own issue, and each issue's Delete this copy removed it. The pendrive copy read as "done by a program the person started": who was at the keyboard was asked only once the copy had settled, by when the hands were off. Fixed the same day (fb81ca8): it is asked when the file first appears.*

You will use Falcon the way real people would, and check it notices. There are four scenarios, about 50 minutes in all. Do them in order. Each one stands alone, so you can stop between them.

| | Scenario | What it proves | Time |
|---|---|---|---|
| 1 | Task | Falcon sees a file being opened and changed, and only a person closes a task | 10 min |
| 2 | Restricted | A file marked to stay in one place is caught anywhere else, under any name | 10 min |
| 3 | Flow | A file arrives at the other machine, converted, and nobody's work is overwritten | 10 min |
| 4 | Detective | It notices mass deleting, tells a person from a program, and a false alarm does not blind it | 15 min |

**You need:** only Notepad and File Explorer. Nothing is installed and nothing outside the Falcon folder is touched.

**The three "machines":** they all run on this PC, each with its own folders. Each folder set below stands for a separate PC.

| Machine | Stands for | Its folders are in |
|---|---|---|
| WS-D1 | A person's PC | `data\hands-on\WS-D1` |
| WS-D2 | A second person's PC | `data\hands-on\WS-D2` |
| ADM-01 | The Admin's workstation (you) | `data\hands-on\ADM-01` |

---

## Setup (5 minutes)

### A. Open four PowerShell windows as administrator

Do this four times: press the Windows key, type `PowerShell`, right-click **Windows PowerShell**, pick **Run as administrator**, and click Yes.

Check that each title bar starts with **Administrator:**. This matters: without it, Falcon cannot see files being opened.

In **each** window, paste this and press Enter:

```powershell
cd C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon
```

To paste into a window, right-click in it.

### B. Window 1: the Engine

```powershell
environ-engine\Scripts\python.exe -m engine
```

**Wait for** a line containing `Engine listening on`. Lines will keep scrolling here. Leave this window alone until the end.

### C. Window 2: the machines

```powershell
environ-operator\Scripts\python.exe scripts\hands_on.py
```

**Wait for** `The machines are running.` (about 15 seconds). You should see:

```
WS-D1  account 7  machine 7
WS-D2  account 8  machine 8
ADM-01  machine 5
```

If your numbers differ, use yours wherever a step says `7` or `8`. Leave this window alone until the end.

Each time this starts, it rebuilds all the folders and clears earlier marks, flows and Detective cases.

### D. Window 3: you, the Admin

```powershell
environ-operator\Scripts\python.exe -m operator_client --config data\admin.json --connect
```

**Wait for** the prompt `admin>`. Every step marked **Type** goes here. Type or paste it, then press Enter.

### E. Window 4: for a few commands

Leave it open at the Falcon folder. Steps marked **Window 4** go here.

### How to read the steps

- **Wait 10 seconds** after each change to a file before checking. Falcon is quick, but this leaves it time.
- **`<id>`** means a number Falcon shows you. Each step says where to read it. Type only the number, with no brackets.
- **Lines appear in window 3 by themselves**, starting with a dot, such as `audit.event {...}` or `pc.presence {...}`. That is Falcon reporting live, and you can ignore them. If one lands in the middle of what you are typing, carry on typing: your text is safe. If a result scrolls past among them, scroll up.
- A grey bar at the bottom of window 3 shows who you are. Ignore it.
- Long paths are cut short with `…` in tables. That is only the display.

---

## Scenario 1: Task

**The story:** you give the person at WS-D1 a task on a file. They open it, then change it.

**File tracked:** `C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\WS-D1\Documents\sales.txt`

**1. Propose the task. Type:**
```
task propose 7 Update sales.txt by Friday
```
It takes about 15 seconds, because the local model is reading it. **You should see** one row: `file`, `update`, `sales.txt`, with a number under `file_index_id`, meaning it found the real file. Below it, `deadline (final): 'by Friday'` and a date.

**2. Give the task. Type:**
```
task create
```
**You should see** `task <id> created for WS-D1-...`. **Write this id down.** Older tasks from my rehearsal may be listed elsewhere: ignore them and use this one.

**3. Wait 10 seconds**, so the machine hears there is a file to watch.

**4. Check where it stands. Type** (with your id):
```
task stack <id>
```
**You should see** `sales.txt` with status `pending`.

**5. Open the file and change nothing.**
- Press Windows + R, paste the line below, press Enter. Notepad opens it.
```
notepad C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\WS-D1\Documents\sales.txt
```
- Close Notepad without saving. Wait 10 seconds.

**6. Type:**
```
task <id>
```
Scroll up to **recent signals**. **You should see** `file_opened`. In `verification stack` it should still say `pending`: opening a file is a sign of work, not proof of it.

**7. Change the file.** Open it the same way, add a line such as `East,700`, press Ctrl+S, close Notepad. Wait 10 seconds.

**8. Type:**
```
task stack <id>
```
**You should see** status `passed`. The task is still not closed: only a person closes a task.

**9. Close it. Type:**
```
task verify <id> complete
```

**10. Type:**
```
tasks all
```
**You should see** your task with status `completed`.

**11. Try something that is not a task. Type:**
```
task propose 7 Does this work, testing
```
**You should see** no rows, and under `needs your decision`: *This reads like a question or a test, not work for someone to do*, with an example. Nothing has been given to anyone.

**12. Try work with no file named. Type:**
```
task propose 7 Work on a spreadsheet
```
It takes up to 30 seconds. **You should see** `(none)` and, under `needs your decision`: *No verification target detected -- None? -- confirm with `task create none`*. So it found no file, guessed nothing, and is asking you.

**Do not run `task create none`.** That would give a task with nothing to check. Just move on: nothing has been given to anyone.

**Passed if:** steps 6, 8, 10, 11 and 12 all matched.

---

## Scenario 2: Restricted

**The story:** payroll must stay in one folder on your workstation. Copies get made anyway.

**File tracked:** `C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\ADM-01\Restricted\payroll.txt`

**1. Mark it. Type:**
```
mark C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\ADM-01\Restricted\payroll.txt keep=path
```
**You should see** `kept to only in its place`.

**2. Type:**
```
marks
```
**You should see** one mark: `payroll.txt`, `Only in its place`, 0 copies. **Write down the number in the `id` column:** this is your mark id.

**3. Copy it elsewhere on the same machine, under another name.**
- Press Windows + R, paste this, press Enter. File Explorer opens the folder.
```
C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\ADM-01
```
- Open `Restricted`, click `payroll.txt`, press Ctrl+C.
- Go back up, open `Other`, press Ctrl+V.
- Click the copy, press F2, rename it `pay-copy.txt`, press Enter. Wait 10 seconds.

**4. Type:**
```
issues type=file
```
Older rows marked `Resolved` are from my rehearsal: look for the row marked **Open**. **You should see** `medium`, machine `ADM-01`, *Restricted file copied where it isn't allowed*. Falcon matched what is inside the file, so the new name did not hide it. **Write down its `id`** (the first column).

**5. Type** (with that id):
```
issue <id>
```
**You should see** that it found `pay-copy.txt` in `Other`, and three choices: `delete`, `rule`, `allow`.

**6. Delete the copy. Type:**
```
issue act <id> delete
```
**You should see** `Waiting`. Wait 10 seconds, then look in the `Other` folder: **`pay-copy.txt` is gone.** The file is really deleted from that machine, and `issues type=file` no longer shows it as Open.

**7. Now copy it to another machine.** In Explorer, copy `payroll.txt` from `Restricted` as before, and paste it into this folder (paste the path in Explorer's address bar and press Enter):
```
C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\WS-D1\Elsewhere
```
Wait 10 seconds.

**8. Type:**
```
issues type=file
```
**You should see** an Open row, **`high`**, machine `WS-D1`. It is more serious because the file left its machine.

**9. Change the original, then copy the new version.**
- Open `payroll.txt` from `Restricted` in Notepad, add a line such as `Yaw,3900`, press Ctrl+S, close it. Wait 10 seconds.
- Copy it into the `Other` folder again. Wait 10 seconds.

**10. Type:**
```
issues type=file
```
**You should see** a new Open row, `medium`, on `ADM-01`. The mark remembers every version, so editing the original does not let a copy slip through.

**11. Finish. Type** (with your mark id from step 2):
```
mark remove <id>
```
**You should see** `unmarked; 2 copy issue(s) closed`.

**Passed if:** steps 4, 6, 8, 10 and 11 all matched.

---

## Scenario 3: Flow

**The story:** whatever is saved in WS-D1's `Outbox` should reach WS-D2's `Inbox` as a PDF.

**Keep two Explorer windows open for this one** (Windows + R, paste, Enter, once each):
```
C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\WS-D1\Outbox
```
```
C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\WS-D2\Inbox
```

**1. Make the flow. Paste this as one line, then press Enter:**
```
flow create src=7:C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\WS-D1\Outbox dest=8:C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\WS-D2\Inbox@0 stage=conversion.to_pdf:if_not=copy
```
**You should see** `flow <id> active (consent: not_required)`, and a `destinations` table with `passed` under `check` and a number under `stage`. **Write down this id.** The `@0` near the middle puts the destination after the conversion: leave it in.

**2. Wait 5 seconds** for both machines to hear about the flow.

**3. Save a letter into Outbox.**
- Open Notepad. Type `Dear Ama`.
- Press Ctrl+S. In the **File name** box, paste this, and press Enter:
```
C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\WS-D1\Outbox\letter.txt
```
- Leave Notepad open. Wait 10 seconds.

**You should see** `letter.pdf` appear in `Inbox`. Double-click it: it is a real PDF saying *Dear Ama*.

**4. Send something it cannot convert. Window 4:**
```powershell
Set-Content data\hands-on\WS-D1\Outbox\sheet.xlsx "not really a spreadsheet"
```
Wait 10 seconds. **You should see** `sheet.xlsx` in `Inbox`, unconverted. This PC has no Office, and the flow carries on rather than stopping.

**5. Someone edits the copy at the destination. Window 4:**
```powershell
Set-Content data\hands-on\WS-D2\Inbox\letter.pdf "my own edit"
```
Wait 10 seconds.

**6. Change the letter at the source.** In Notepad, add a line, press Ctrl+S. Wait 10 seconds.

**You should see** two files in `Inbox`: `letter.pdf` (the new version) and **`letter-modified.pdf`**. Right-click `letter-modified.pdf`, pick **Open with**, then Notepad: it says *my own edit*. A flow never overwrites what it did not write.

**7. Pause the flow. Type:**
```
flow pause <id>
```
**You should see** `flow <id> paused`.

**8. Window 4:**
```powershell
Set-Content data\hands-on\WS-D1\Outbox\paused.txt "written while paused"
```
Wait 10 seconds. **You should see** nothing new in `Inbox`.

**9. Resume it. Type:**
```
flow resume <id>
```
Wait 10 seconds. **You should see** `paused.pdf` arrive in `Inbox`. Nothing was lost.

**Passed if:** steps 3, 4, 6, 8 and 9 all matched.

---

## Scenario 4: Detective

**The story:** 60 contracts get deleted, first by a person, then by a program. You dismiss one alarm as false, and it happens again.

**Files tracked:** the 60 contracts in `C:\Users\Khonello\Documents\Developer\Languages\Multi\Falcon\data\hands-on\WS-D1\Documents\Old`

**1. Delete them by hand.**
- Press Windows + R, paste the path above, press Enter.
- Click any file, press Ctrl+A, then **Shift+Delete**, and confirm Yes. Wait 15 seconds.

**2. Type:**
```
detective status=open
```
**You should see** `(no cases)`. That is right: someone deleting 60 files from one folder may just be tidying up, so it is not put in front of an Admin.

**3. Now look at what it kept quietly. Type:**
```
detective noted status=open
```
**You should see** a case on `WS-D1`, level `noted`. `detective case <id>` says the documents were deleted **by hand**: Falcon saw real keyboard use in File Explorer just before.

**3b. Put the contracts back, and wait. Window 4:**
```powershell
environ-operator\Scripts\python.exe scripts\hands_on.py refill
```
**You should see** `refill: done, 60 contracts`. **Wait 2 minutes 30 seconds.** Detective looks at two-minute bursts, so if you go sooner, this round counts as part of the last one and reads as by hand.

**4. Now a program deletes them. Window 4:**
```powershell
environ-operator\Scripts\python.exe scripts\hands_on.py wipe
```
**You should see** `wipe: done, 0 contracts`. Wait 15 seconds.

**5. Type:**
```
detective status=open
```
**You should see** a case on `WS-D1`: `urgent`, `Wrecking things`. It may be the same case as step 3, now raised because a program did this. **Write down its `id`.**

**6. Read it. Type:**
```
detective case <id>
```
**You should see** what happened in order, "not by hand" in the summary (beside your earlier "by hand"), what could make it harmless, and *Detective's reading of the evidence, not proof*.

**7. Call it a false alarm. Type:**
```
detective review <id> dismissed it was a test
```
**You should see** `recorded`.

**8. Do it again. Window 4:** run the `refill` command from step 3b, wait 10 seconds, then the `wipe` command from step 4. Wait 15 seconds.

**9. Type:**
```
detective status=open
```
**You should see** a case with a **new id**, `urgent`, on `WS-D1`. This is the most important check here: one dismissed alarm must not blind Detective. Until 5 Nov 2026 it did.

**Passed if:** steps 2, 3, 5, 6 and 9 all matched.

Deleting with plain Delete, to the Recycle Bin, behaves the same as Shift+Delete.

**Optional, with a USB stick or USB hard disk:** copy `payroll.txt` from `ADM-01\Restricted` to the drive under another name, while it is still marked (Scenario 2, before step 11). Type `issues type=file`: **you should see** an Open row, `high`, on `WS-D1`. Type `detective noted status=open`, then `detective case <id>`: **you should see** *Taking data out* and *was copied to a removable drive*. Delete the copy afterwards. A plug-in or a removal is recorded, but it is not a line in the case's story.

---

## When you finish

1. Window 3: type `quit`.
2. Window 2: press Ctrl+C.
3. Window 1: press Ctrl+C.
4. Close the windows.

To go again from scratch, start from Setup step B.

---

## If something looks wrong

| What you see | What it means | What to do |
|---|---|---|
| `this account's role is not part of this version` | `--config data\admin.json` was left out | Run Setup step D exactly as written |
| A window says something like `is not recognized`, or a file is not found | That window is not in the Falcon folder | Run the `cd` line from Setup A |
| Window 3 cannot connect | The Engine is not running | Check window 1 says `Engine listening on` |
| An error about the address or port 7400 being in use | An Engine is already running | Close all four windows, reopen them, and start again. If it persists, restart the PC |
| `A machine did not come online` | A machine failed to start | Press Ctrl+C in window 2, run it again. If it repeats, send me `data\drill\WS-D1\worker.log` |
| No `file_opened` in Scenario 1 | Usually window 2 is not running as administrator | Check its title bar. If it is, wait another 10 seconds and repeat the step |
| `conflict: destination path collides` | `Inbox` already has files in it | Empty `Inbox` and run the `flow create` line again |
| `no such ...` or a usage message | The id was mistyped, or `<id>` was typed literally | Check the number and type it without brackets |
| Nothing has changed after 10 seconds | It may be busy | Wait another 20 seconds and check again. If there is still nothing, it is a finding: note the step |
| The power goes out | Everything stops, and no harm is done | Reopen the windows and start from Setup. Setup rebuilds everything, so redo the scenario you were on |

## Telling me how it went

Just send the scenario and step number, and what you saw instead. If everything matched, "all passed" is enough.

## What this cannot show

Word, Excel and PowerPoint (not installed here), two separate PCs, the Worker's windows and tray on a real desktop (the machines here run without them), and a second Windows user being refused a Private file. Those are in `docs/VM-TEST-PLAN.md`.
