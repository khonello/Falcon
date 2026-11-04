# Engine work found while building the UI

The GUI rebuild (step 3 onwards) keeps UI and Engine work apart: whatever a page needs from the Engine or
the Worker Client that is not there is written here and fixed in one pass later. Mundane, simple fixes are
done inline and are not listed. Each entry: what is missing, why it matters, where it was found.

**How the Worker reaches the OS** (decided 9 Oct 2026). Nobody using a machine needs to be a Windows administrator;
Falcon's Admin is its own role. The Worker Client runs as a Windows service under the system account, installed once
with admin rights (Phase 9 packaging, as any management agent), and does the OS-level work from there: kernel event
tracing (ETW) for file opens and process starts, process and USB and network state, no Windows audit policy to switch
on by hand. Windows keeps services out of the signed-in person's desktop (session 0), so whatever must draw on their
screen or capture it -- the lock overlay, messages, screenshots -- runs as the Worker's helper windows, started by the
service inside that person's session.

**Packaging and installation are on hold** (the user, 10 Oct 2026): nothing here starts them until the project is given
a clear green flag (PHASES.md, Phase 9). Where an item below mentions the service, the session or an installer, that
part is recorded for later, not built.

## Open

1. **OS signals from the Worker: native for drives, sign-ins and the network; programs still compared** (9-10 Oct
   2026). Built and tested: the Engine tells a machine which signals its automations wait for
   (`control.signal_interest`, and `control.interest_changed` when one is created, changed or disabled);
   `worker_client/ossignals.py` watches only those and relays them through `control.signal`:
   `usb.inserted/removed`, `network.connected/disconnected`, `program.launched/exited` (a program match is applied on
   the Worker) and `user.login/logout`. Each signal is the difference between two looks; the first is a baseline.
   **Native:** `worker_client/winnotify.py` (ctypes) is a hidden message window that Windows tells when a drive or
   volume arrives or leaves and when anyone signs in, out or locks, plus `NotifyIpInterfaceChange` for the network;
   each only nudges the watcher to look at once, so a missed notification costs one safety-net look (30 s) and never a
   wrong signal. **Instant programs (done 12 Oct 2026):** `worker_client/etw.py` starts a real-time ETW session on
   Microsoft-Windows-Kernel-Process only while an automation waits for `program.launched` / `program.exited`, so every
   start and stop is seen the moment Windows creates or ends the process, including one that lives under 3 s; the
   3-second comparison stays as the fallback and is skipped while the trace is live (nothing is said twice). Windows lets
   only an elevated process, or a member of "Performance Log Users", start a trace: the Worker service (system account)
   can; run as an ordinary user it says so once and keeps the fallback. `python scripts/etw_check.py` shows it working
   from an elevated prompt. *Found:* Automation (AU08), 27 Sep 2026.
2. **A file being opened (done 12 Oct 2026)** (the Engine half was done earlier: `file.accessed` is relayable and part of
   the interest list). The Worker now produces it, as decided (the user, 9 Oct 2026): from Windows' own kernel file events
   (`Microsoft-Windows-Kernel-File`, create events), no audit policy switched on by hand, in the Worker service (system
   account). `worker_client/etw.py` filters inside the trace callback by the paths and suffixes automations named, so
   the flood of every open on the machine never leaves the Worker; folders, Falcon's own opens and the several creates
   of one open are dropped; a rule that names only a resource tier cannot be decided on the Worker and is not watched
   live (it says so in the log). The kernel's `\Device\HarddiskVolumeN` paths are turned into drive letters.
   Without the privilege to trace it stays unavailable (the log says why). *Found:* Automation (AU08).
3. **Protection gets a third tag, "Private"** (the user, 21 Oct 2026).
   - **The three tags.** A protected thing (a file, folder or program) carries exactly ONE of them. The target is chosen first, then its tag.
     - **Watch:** free to go and to open; every open and move is noted. This is today's watched.
     - **Private:** only the people the owner names may open the file or folder, or run the program. Anyone else, or a
       program running as them, is refused, and the refusal is noted. This one is new.
     - **Restricted:** it never leaves its place; a copy elsewhere is caught. This is today's restricted.
   - **What was ruled out.** A combined form ("watched + optional guards") was declined, so the tags never combine. "Ask
     first" (every open waits for a yes) was tried and replaced by Private: it made the owner a gate on every open and
     could not answer for background programs. Nobody can ask to be added to a Private item; only the owner changes who
     is named.
   - **Background programs** (backup, antivirus) run as the machine's own system account. Per item, the owner chooses
     whether that account may read it. If it may not, the program is refused like anyone else.
   - **The Engine needs:**
     - a `protection_tag` on marks (watch, private, restricted);
     - marks on programs as well as files and folders;
     - a named-people list per Private mark, plus the system-account choice;
     - a refusal record (who, what, which machine, when) for the audit and the page.
   - **The Worker needs** to refuse the open or the program start when the person is not named, using the kernel file
     and process events it already watches. How the refusal is shown to that person is still to be decided.
   - **Flow consent** (`engine/flow/guard.py`) stays as it is, for Restricted things.
   - **Built 2 Nov 2026** (the user: "established mechanisms"; migration 050, `engine/resource/private.py`, `worker_client/privacy.py`): marks
     carry `protection` (watch / private / restricted); every restriction check reads restricted marks only. Private: the Worker sets
     Windows' own permissions (icacls) so only the named people -- and the system account when the owner allows it -- may open or run it,
     saving the original to put back on unmark; refusals are Windows' "access denied", read from its audit of failed opens (Security 4656)
     and noted on the mark, in the audit trail, to the owner, and as a quiet note to the person refused. `marks.create {protection, readers,
     allow_system}`, `marks.readers` (the owner only). A program is private the same way (its .exe). Not tried for real yet: a second Windows
     user on a machine being refused (the VM plan).
   - *Found:* the Super User's Protected page.
4. **Group conversations for the Super User** (the user, 22 Oct 2026). Messaging several people at once, or every Admin of a department, is now ONE group conversation in which everyone sees what everyone writes. It no longer copies the message into each person's own conversation.
   - **A department's group** exists while the department has two or more Admins. Its members follow the department: an Admin who joins is added, and one who leaves is removed.
   - **Other groups** are made by writing to a set of people. Writing again to the same set reuses that group.
   - **The page shows** who has answered since your last message.
   - **The Engine needs:**
     - a conversation with members, instead of a pair;
     - a membership that follows a department's Admins;
     - a quick ask to several people that lands in their group.
   - *Found:* the Super User's Messages page.
5. **Drop the one-message-per-turn lock on Message Channels, and message requests** (the user, 22 Oct 2026: the lock "can be frustrating real quick").
   - **Engine: done 22 Oct 2026** (`engine/resource/assistance.py`, `tests/test_resource_assistance.py`).
     - `assistance.message` accepts a message from either party while the channel is open.
     - The channel's `turn` now only says who owes an answer, so `my_turn` means "waiting on me".
     - **Requests:** `assistance.respond` is the accept. Super User → Admin through `assistance.ping` opens the channel at once and returns `channel_id`; the Admin has nothing to accept, and the Admin's own pending request is answered with it.
     - **Admin → Admin** requests are allowed (`may_message`), and either Admin may close.
     - Found on the way and fixed: when the superior asked first, the channel's initiator and superior are the same account. `open_channel_between` and `channels_for` (`engine/database.py`) missed such a channel for the other party; both now look through the request's two ends.
   - **Clients: done 22 Oct 2026.**
     - **The Engine decides who may message whom and who may close.** New `assistance.people` lists who you may message, with `request` (whether they must accept first). `can_close` is part of `assistance.channel`.
     - **`MessagesPage.qml`:**
       - the box is always open;
       - a request has Accept, and writing back accepts it too;
       - "New message" lists `assistance.people`. For the Super User it says "Open the conversation" and selects the new channel; for everyone else it says "Send the request".
       - Close follows `can_close`.
       - It and `IssuesPage.qml` sent `text` where the Engine reads `body`, so a message from the GUI never went through. Both are fixed.
     - **The Operator TUI** has a new `people` command, and `ping` opens the channel when the Super User writes to an Admin. Its wording and push lines no longer mention turns.
     - **The Worker TUI and window** use the same wording.
     - Tests: `tests/test_resource_assistance.py` (`people`, `can_close`), `tests/test_operator_gui.py` (writing back accepts and sends `body`) and `tests/test_operator_client.py`.
6. **What the Super User sends reaches the Admin** (the user, 22 Oct 2026; drawn on the concept's Admin level, v293).
   - **A banner across the Admin's console** for each new directive *and* each new notice, with Open and "I've seen it". The console's banner covers directives only.
     - Notices need a per-Admin "seen" record, so the Super User can see who has read one, just as they see it for directives.
   - **The Admin's conversation with the Super User is always there**, with no request, and it carries cards for what the Super User sent outside it: each directive given to them (with "I've seen it" and "Open in Tasks") and each notice that went out.
     - The Engine needs to list directives and notices together with a channel's messages, or the client needs to merge them.
   - **A quick ask to one Admin** lands in that Admin's conversation with what it is about, attached. Messages need an optional `about` field.
   - **Group conversations** show in each member Admin's Messages, and any member can write in them (item 4).
7. **Sending a file in a conversation** (the user, 22-23 Oct 2026; drawn on the concept, v296).
   - **How it works:** anyone in an open conversation or group sends one file, once, up to 100 MB. It arrives as a card with Save, which puts it in `Downloads\From Falcon` on the receiver's machine.
   - **Asking:** there is no separate step to ask for a file. People ask in an ordinary message, and the other side answers with a file.
   - **Sending is intentional access**, and what it means is said before it is sent:
     - **Private:** sending adds the receiver to who may open the file.
     - **Restricted:** sending is the owner's consent for that one copy.
     - **Not the owner:** if the sender does not own the protection, the owner is asked first, and the file goes once they agree.
   - **Refused:**
     - programs and scripts (`.exe`, `.msi`, `.bat`, `.cmd`, `.ps1`, `.py`, `.vbs`, `.js`), because a script runs as a Custom Action, where it is checked first;
     - anything over 100 MB, which goes by a Flow instead.
   - **The Engine needs:**
     - a relay that pulls the file from the sender's Worker, holds it until delivered (7 days at most) and then drops the bytes, while the transfer record stays;
     - a message with a file;
     - consent requests to an owner;
     - adding a person to a Private mark;
     - the delivered copy indexed with its origin (sender, conversation), so Protected and the Detective see a handed-over copy, not a stray one;
     - an audit entry for each transfer.
   - Decided by the user, 2 Nov 2026: an admin-tier file may go to a Worker. **Built 2 Nov 2026** (migration 049, `engine/resource/chatfiles.py`,
     `worker_client/chatfiles.py`): `chat.send_file`, `chat.file_consent`, `chat.file_save`, `chat.files`; held on the Engine's disk 7 days at
     most; each saved copy recorded (`chat_file_saves`) and read by Restricted as "handed over in a conversation"; a restricted copy allowed
     where it lands. Not yet: adding the receiver to a Private file's readers (Private, #3, is next).
8. **A description is always one task** (the user, 24 Oct 2026; the concept's New task, Admin v70). **Done 1 Nov 2026:** the split step is gone from
   `llm_graph.py`, `proposed_split` from `task.propose`, the TUI and `NewTaskPage.qml`; the cases carry no split field. Benchmark with the 1.7B after it:
   tuned 32/32, held-out 31/31.
   - `engine/task/llm_graph.py` proposes a split when two or more files are joined by "and also / then / ;" (`proposed_split`). That step goes.
   - All targets go onto the one task. A part that names nothing to check stays in the description, for the assigner to judge at verification.
   - `tasks.py` stops returning `proposed_split`, and the clients drop the "split / keep as one" choice.
   - `scripts/llm_cases.py` has split cases. Move them to one-task expectations; they are rules, not held-out measurements.

9. **What the Machines page shows about one machine** (the user, 24 Oct 2026; the concept's Machines, Admin v87). Each item says what the Engine must keep, and for how long. The Worker already knows most of it.
   **Done 1 Nov 2026** (`machines.get`; migration 042; `worker_client/protected.py`): `running_now` (the seven busiest, from the snapshot, which now
   leaves out Windows' own processes, the machine's service accounts and the Worker itself; `kill_process` refuses those even by pid), `about` (OS,
   memory, disk size and percent, last boot, registered: the Worker says them at connect), `keyboard` (in use / idle / offline now, and today's
   quarter hours of use: a metrics report with input in the last minute marks its quarter), `check_ins` (seven days, yes or no: a connect or a report
   that day). Days and quarters are the Engine host's local time. Entered was already `sessions`. *Not built:* "Never allow it" is a rule the console
   prepares with the existing `program.launched` condition and `kill_process` + `notify`; nothing new in the Engine. The `pc_days` rows (one per machine per day)
   are asked about on the 90-day clock (3 Nov 2026, `engine/console/retention.py`): an issue offers Delete them or Keep them (asked again in 30 days).
   - **Running now:** the seven busiest programs, with CPU and memory, from a snapshot the Worker sends with its metrics (psutil). Keep only the latest snapshot. System processes and the Worker itself are left out of the snapshot, so they can never be ended from here.
   - **End a program** (the user, 24 Oct 2026). The built-in `kill_process` (by name) already exists. Ending runs it as a manual action, so it is audited. It is followed by a `notify` on that machine telling the person the Admin ended it. The Worker refuses to end anything on its protected list, even when asked directly.
   - **Never allow it:** "never allow it" prepares a rule switched off: when the program starts on any machine, end it and tell the person. This needs a program-started condition; check what OS signals (item 1) already give.
   - **At the keyboard:** in use or idle now, plus today's quarter hours of use from 08:00. The Worker's idle detection reports it; keep one day.
   - **Storage:** percent used and the disk's size. Size is new; percent is already a metric.
   - **About the machine:** OS, memory, last boot, registered date. Reported once at connect and kept on the machine's row; the registered date comes from `pcs`.
   - **Entered:** when and for how long, from sessions on that PC. No names on this page.
   - **Check-ins this week:** one yes or no per machine per day, for the last week. A check-in is the machine's Worker reaching the Engine: the PC is on and connected, whether or not anyone is signed in. It comes from connect times; keep a week.

10. **PCs found but not registered** (the user, 24 Oct 2026; the Add a machine drawer, Admin v100). The drawer offers PCs the system has noticed but nobody registered, and picking one fills in its name.
   **Knocked: done 1 Nov 2026** (`registry.knocked`, TUI `knocked`): by the name the PC gave, address, tries, first and last; a name registered since
   drops out. Not cut by department: in version 1 the Admins are IT over every department, and departments keep no address range. *Seen on the
   network* is **dropped** (the user, 3 Nov 2026): a machine with Falcon installed joins with its licence code; no network scan.
   - **Knocked:** a Worker that tried to connect without a valid key. The handshake already records `auth.failed`, and the Super User's Refused list reads it. The Admin needs the same list, cut to unregistered names and the department's address range, with tries and last try.
   - **Seen on the network:** a PC with no Worker yet. This is new. It needs discovery on the department's subnet, from the Engine or a registered Worker: ARP or NetBIOS/mDNS names, passive where possible. It reports name, address and when first seen. **To decide with the user:** whether discovery is allowed at all (it is a network scan), which machine does it, and how often.
   - Registering a found PC uses the existing `hierarchy.pc_register`. Nothing about keys changes.

11. **A flow's last sync, as a diff** (the user, 24 Oct 2026; the Admin's Flows, v116). **Done 1 Nov 2026** (migration 045, `flow.runs`, TUI
   `flow runs`): the destination's Worker reports each file's size before and after; the log keeps new / changed / kept beside; a run is the writes
   two minutes apart at most; what the flow holds now (a destination away, a consent asked) is `waiting`, not a per-file row. For each sync run of a flow, keep:
   - when it ran;
   - each file it handled: new, changed, kept beside a changed copy, held for consent, or waiting for a destination;
   - each file's size before and after at the destination.

   The page shows the last run in full, then the runs before it as counts and bytes. The run boundaries and sizes come from what the Worker reports when it writes (`flow.conflict` already carries kept-beside). Keep runs on the 90-day clock.

12. **What the Admin's Restricted page shows** (the user, 24 Oct 2026; the concept's Restricted, Admin v125). **Done 1 Nov 2026** (`marks.get`):
   each copy's `came_by` (a flow, a USB drive the machine has seen, a network path, Downloads or a mail or browser cache, another place on the same
   machine; else "arrived from another machine" marked not sure), `allowed` (with the reason typed), `lately` (two weeks of changed, copied, files
   added, moved, a flow held at it) and `flows_allowed` (since when; `flow.revoke` takes it back). Restricting only on the PC you are at is the
   console's limit, as written below. An Admin restricts only what is on the PC they are at (the user, 25 Oct 2026, to avoid confusion). `resource.tag` allows any machine of the department today, so the console limits it. The file or folder is found by searching that PC's entries in the file index, or picked in Explorer (a native file dialog in the Operator Client). For each copy caught, and each mark, keep:
   - **how the copy got there:** copied over the network, from a USB drive, saved from an email or a download, or delivered by a flow. Read it from the file events that led to the copy.
   - **a copy allowed where it is,** with the reason the owner typed. It stays on the record, quiet, and is not caught again.
   - **what happened to the mark lately:** opened, changed, copied, files added, a flow held at it.
   - **the flows the owner allowed,** per flow, with since when, and taking that consent back. Copies already delivered are then caught like any other.

13. **What the Admin's Automation page is still missing** (the user asked for an opinion, 25 Oct 2026; Admin v138). The page says what fired and whether it worked. It does not yet say these four things. They are proposals, not decided:
   **What runs next: done 1 Nov 2026**, because the concept draws Coming up (`automation.board`: each rule's `next_at`, and `coming_up`, the next ten
   scheduled runs across the rules that are on). **Try it first: done 3 Nov 2026** (the user's pick): `control.rule_try`, TUI `event try`.
   **What a run produced** and **too quiet or too loud: dropped** (the user, 3 Nov 2026).
   - **What a run produced.** A screenshot, a list of a USB drive's files, a log line: the page says "screenshot taken" but you cannot see it. Each run should link to its output. Keep outputs on the 90-day clock, as run outputs already are.
   - **What runs next.** Each scheduled rule's next time, and the next few runs across all rules, so "Next: Daily maintenance tomorrow at 09:00" is a fact the Engine gives, not a sentence the page guesses.
   - **Try it before switching it on.** Run a new or edited rule once, on one machine you pick, and show the result before it goes live. Nothing about the rule is saved until you confirm.
   - **Too quiet or too loud.** Say when a rule fires far more than its usual week (31 times against 3), or has not fired in weeks while its event surely happened. This needs each rule's weekly count kept, so a week can be compared with the usual.

14. **What the Admin's Actions page needs** (the user, 28 Oct 2026; the concept's Actions, Admin v159). **Done 1 Nov 2026** (migration 043):
   `output_kind` on a custom action (`control.action_create/update`; the Engine makes the summary and the rows by it, and `control.execution` says it);
   `action.status` now carries each machine's `pc_id`, `outcome`, `exit_code` and `seconds` as it finishes; `control.terminate_run {execution_ids}`
   stops what still runs; `control.action_try` runs an unsaved script once on one machine (the run is real and audited as `action.tried`; its action
   row is archived as it is made, so it is never in the library). TUI: `action try`, `terminate run`, `action custom ... reports=`.
   - **What a custom action reports back.** Its author picks one of three, and it is kept with the action:
     - **text:** what it prints is shown as it is, and the first line is the summary;
     - **a list:** each line printed is a row, a tab splits the columns, and the summary counts the rows;
     - **only whether it worked:** the output is not shown, and exit 0 counts as worked.

     The Engine stores the choice with the action. The console shows a run's output the way the choice says.
   - **A run by hand reports back machine by machine.** As each machine finishes, push its outcome, exit code and time, so the picked machines can fill in while the run is going. Stopping a run by hand ends what is still running; it is recorded as stopped, not failed.
   - **A test run of a custom action before it is saved.** Run the script once, on one machine the author picks, and return what it printed, its exit code and its time. Nothing about the action is saved until the author confirms. This is the same idea as "try it before switching it on" for rules (item 13). The test is a real run, so it is recorded with the author's name.
15. **A case told in words** (the user, 29 Oct 2026; the concept's Detective, Admin v171). **Done 3 Nov 2026** (the user chose the first way,
   then a pass to make it natural; `engine/detective/telling.py`, migration 051): `detective.case` returns `telling`, the Engine's account with
   every fact a marked part; the model may rewrite one paragraph at a time with the facts hidden behind markers, and its paragraph is kept only
   if every marker survives once each in order, with no new number, name or blame word and the same number of "not"s. TUI `detective case`.
   - **What it is.** "What Detective noticed" is no longer a list of findings. It is a few paragraphs, written by the local model from the case's evidence, telling what went on: who was signed in, on which machine, when it started, how long it took, what was done to which files, what makes it worth a look, and what would make it innocent. People, files, machines, programs and times are marked in the text, the way the task box marks them.
   - **This goes against a rule in CLAUDE.md, so it needs a decision.** The model is only ever asked narrow questions (pick from a list, or extract text that is then checked word for word), never to write freely. A free account from a 1.7B model can say something the evidence does not, about a named person. Two ways to keep it honest:
     - the model writes only the joining words, and every fact (a name, a file, a time, a count) is filled in from the case, never by the model; or
     - the model writes freely, and every name, file, time and number in its text is checked against the case before it is shown; anything it cannot back is dropped, or the account falls back to the findings.
   - **Where it comes from.** A case needs who was signed in at the time (from sessions), not who is signed in now, and the duration from first to last event. Both are in the Engine already.
   - The account is labelled as the model's reading, not proof, and nobody at the machine is told.
16. **Detective weighs what was carried, not the drive** (the user, 29 Oct 2026; the concept's Detective, Admin v179). **Done 1 Nov 2026**
   (`common/detective.py`): a new drive is shown ("not weighed") and adds nothing; a known drive, an exception or a rule lowers ordinary files only;
   ordinary files to a drive start at 0.18 (outside the person's work 0.30, restricted 0.45). The trusted-drive actor was a pinned blind spot and is now
   caught every run. `detective.case` returns `glance` (stage and next, restricted, who was signed in when it began, earlier cases here and their
   outcomes, when raised, how long it lasted).
   - **The rule.** When files leave a machine, the weight comes from what they are: restricted, marked, or from a folder outside the person's work. Whether the drive is new to the machine is context only. A new drive carrying ordinary files raises little or nothing. A drive the machine knows well carrying restricted files still counts in full.
   - **Said to be fine follows the same rule.** An exception for a drive, a program or a folder lets ordinary files pass. It never lets restricted files pass: copying restricted files to an excused drive still counts in full.
   - **Today** "a drive this machine has not seen before" is one of the reasons a finding counts (the drive-after-staging and to-drive findings). It should be kept as a fact that is shown, and stop adding to the weight on its own.
   - **What the At a glance panel needs for each case:**
     - how far it got, as the last stage reached and the next one;
     - whether restricted files are involved;
     - who was signed in at the time, which may not be who is signed in now;
     - the earlier cases on the same machine and their outcomes;
     - when it was raised.

     Most of these are in the case already. Who was signed in at the time comes from sessions, and the earlier cases come from the cases table.

17. **An Admin's own to-dos, and conversations without the Super User** (the user, 29 Oct 2026; the concept's Tasks, Overview, Calendar and Messages, Admin v199). Version 1 has no Super User, so what came from them on the Admin's pages became the Admin's own.
   **To-dos: done 1 Nov 2026** (migration 041, `engine/task/todos.py`: `todo.list` with `strip`, `todo.add`, `todo.done {done}`; on `calendar.board`
   as kind `todo` and on `overview.admin` as `todos_due` / `todos_overdue`; TUI `todo add|done|undo`, `todos`). **Messages: done 1 Nov 2026**
   (migration 044, `engine/resource/conversations.py`: `chat.list|people|open|get|send|read`, pushes `chat.message` and `chat.read`; TUI `chats`,
   `chat with|send|who`, `chat <id>`). A pair is made the first time either writes; the group of every Admin reads its members from the accounts, so
   it follows who is an Admin. A machine's person answers but does not start one. *Not built:* the Worker's own program does not show these yet (it
   still shows the help channel).
   - **To-dos.** A to-do has an owner (the Admin), a line of text, when it is due, and when it was done. Nothing else: no checks, no assignee, no seen or ongoing. Only its owner sees it, adds it, ticks it and takes the tick back.
     - It shows on Tasks (Your to-dos), the Overview, the Calendar, and the strip across the console when it is due within a day or past its date.
     - The Engine has nothing like it today: every Task goes from one person to another and is closed by verification. This is a new small table and three handlers (list, add, done), not a kind of Task.
     - "Not now" on the strip is the console's own and needs nothing from the Engine.
   - **Messages.** An Admin talks to the other Admins and to whoever is signed in on a machine. A group of every Admin exists once there are two or more. There is no request to talk before writing, since help requests are out of version 1. A conversation is only what was written in it.
     - What the Engine has today is the help-ping channel (a request, then one message each way, closed by the higher party), plus the Super User's groups. The Admin's page needs a plain conversation between two people, and a group of Admins, with read times kept per person.
   - **Owners moved.** In the concept's sample data, the flows, rules and folder asks that belonged to the Super User now belong to other Admins (A. Quaye, K. Boateng). Nothing in the Engine changes for this. A thing made by another Admin stays theirs to change.

18. **Version 1: IT Admins only, the Super User parked** (the user, 1 Nov 2026; `docs/design/v1-it-admin.md`). **Steps 4-5 done 1 Nov 2026:** the Super User's code is in `parked/` (`parked/README.md`), its role is refused at sign-in, `require_head` gives its organisation-wide powers to any Admin, and the console is one level. **Steps 1-3 done 1 Nov 2026.** One switch, `FALCON_ADMIN_SCOPE` (`engine/permissions.py`: `org_wide`, `kept`, `own_department`,
`in_scope`), defaults to `organisation`; `department` keeps the full design for later and is what the older tests run under (a test marked
`organisation` runs as version 1: `tests/test_v1_scope.py`). Admins make departments and other Admins, take one away (never themself),
promote and demote; a department needs no Admin of its own; every issue starts unassigned for any Admin to take; reports reach every
Admin. `engine setup` / `bootstrap` make the first IT Admin in a department named IT. Flows: only onto another Admin's machine needs consent,
and that Admin names the folder as they agree (`let_them_choose` at creation, `destination_path` in `flow.consent`); a Worker's folder is
named by the maker. A flow's source may be one file (`source_kind: file`, migration 046): a move at the source takes the flow along, and its
copy moved at a destination is where the next change is written (`followed_path`). TUI: `flow create ... file`, `dest=<pc>:` to let them
choose, `flow consent <id> yes folder=..`. Steps 4-6 are next. The plan, in order:
   - Admins reach every department (`admin_scope`, fixed to organisation); department and Admin creation are Admin handlers; reports and issues
     reach every Admin, with Take; Admin to Admin on a machine stays refused.
   - `engine setup` / `bootstrap` make the first IT Admin; `make_org.py`, `.env.example` and `GETTING-STARTED.md` follow.
   - Flows: consent only Admin to Admin, the destination Admin choosing the folder; Worker destinations picked by the maker; restricted consent
     from the marker kept.
   - **A single-file flow**: the source is one file followed by its index identity (a rename or move on its machine keeps it syncing), and the
     destination copy is followed the same way (written where it now is). New: a source kind and file id on `flows`; the destination's current
     path from move events against the sync log's `written_path`.
   - Park the Super User: its handlers, QML pages, TUI commands, preview data, installer role, handover and their tests go to `parked/`; every
     reference is stripped from what ships.
   - Settled and built: an Admin leaving is known by another Admin offboarding the account (the machine stays and says nothing); what the account still owns (restrictions, flows, rules, actions, tasks to verify, issues) is handed to another Admin with a tool, not a page: TUI `account owns <id>` and `account handover <from> <to>` (`hierarchy.ownership`, `hierarchy.hand_over`; decided 1 Nov 2026).

19. **The Worker's side, as the Worker concept draws it** (the user, 1-2 Nov 2026; `docs/design/concepts-worker.html`, the
    "Falcon Concepts · Worker" artifact, v13; the Admin concept's Messages, Admin v237). The concept is the source of truth for what the
    person at a machine sees; this is what the Engine and the Worker Client need for it.
   - **A Worker replies to an Admin's message.** Today the message window (`worker_client/windows`, kind `message`) only has OK. The reply
     goes into that Admin's conversation with the person, from the window and from the program's Messages tab. Admin → Worker still opens at
     once, with no request.
   - **A request to talk** (decided 2 Nov 2026: part of Messages only; the Assistance feature, shared-resource search and help as its own
     thing, stays cut). The person sends one line from the program ("Ask IT"); every IT Admin sees it; one accepts it, as Take on an issue,
     and the conversation opens with that line in it; or an Admin closes it with a reason the person reads. One open request per person.
     Needs: a request record (from, line, sent, accepted by / closed with reason), handlers to send / accept / close, a push to every Admin
     and back to the person, the Admin's Messages count including waiting requests. Automation's `help` trigger becomes "A person at a
     machine asks to talk" and the sample rule "Requests to talk are accepted" (expect: an Admin accepts the request).
   - **Remove "Ask for help"**: the program's My machine button and the `ask` window kind (`Program.qml`, `windows/qml/Window.qml`,
     `windows/__init__.py`) are Assistance and go; Ask IT in Messages replaces them.
   - **The program** (`worker_client/program`): one wide window. Today shows tasks, messages and announcements side by side, most urgent
     first; tabs Tasks (to start, started, closed this month; the picked task with its targets and whether each has changed), Messages
     (conversations, the waiting request, Ask IT), Announcements (all, with kind), My machine.
   - **My machine shows what IT asks for on the phone**: name, department, IP address, Windows edition and version, Falcon version and
     whether it is up to date, the account signed in and since when, the last restart, free space on C:, connected since, and the IT
     Admins; "Copy these details" puts them on the clipboard. Not a history of Admin visits (the user rejected that). The local app view
     (`worker_client/localapp.py`) needs these fields.
   - **The covers** say when: an Admin inside shows came in / leaves by (the session's `deadline_at`); locked shows locked at / unlocks at
     and the Admin's reason.
   - **The Worker's command line** is not part of the product the person sees. It stays as IT's and the tests' tool; its Assistance commands
     (search, ping) go, and a messages / reply pair comes in.
   - **Open, not decided:** when the Admin's PC dies mid-session the Worker stays covered until the deadline (30 min by default, longer if
     extended), because a dropped connection is not special-cased (`engine/hierarchy/traversal.py`). Options raised: end the session after a
     short grace (~2 min) once the Admin's console is gone, or keep the deadline and have the cover say the Admin's connection dropped and
     when the machine frees itself. Also: the cover only returns after the Worker reconnects, so a restarted machine is usable for those
     seconds.

20. **What the console's pages draw that the Engine cannot do yet** (2 Nov 2026, the QML rebuilt from the version 1 Admin concept). Each
    control is drawn disabled with this reason on it, never faked:
   - **End one program on a machine** (Machines, "Running now", End). There is a `kill_process` built-in action, but no call ends one
     program on one machine from the console; the concept also offers "never allow it", a rule prepared in Automation.
   - **Register a machine without a department** (Machines, Add a machine). `hierarchy.pc_register` still requires `department_id`; in
     version 1 a machine is only registered there and gets its department on Departments. The drawer keeps the department field until then.
   - **Update a machine now** (Machines, an expanded card). The Engine retries on its own schedule only.
   - **Remind someone** about a task (Tasks, a late task) or an Admin about a flow waiting for their folder (Flows, the gate).
   - **Start a stopped flow again** (Flows, Resume on a stopped flow). Stop sets it inactive (`flow.delete`), which cannot be undone yet.
   - **Take back an allowance** on a restricted copy (Restricted, Allowed copies).
   - **Delete or ask to delete a restricted copy**, and accept or put back a deviation, where `issues.get` marks the option `cannot`.

21. **No ownership of issues between Admins** (the user, 2 Nov 2026: "the idea of ownership between admins, i hate it"). The console no
    longer takes, gives back or shows who has an issue; any Admin acts on any issue (`issues.act` never checked the owner). For the Engine
    session, when it suits: `issues.assign`, the `owner` filter of `issues.list` and `owner` on each issue can go; `issues.get`'s story
    still writes "Assigned to ..." for an issue someone took before this; the TUI's `issue take / give / free` go with them. Nothing in
    the console calls them now.

22. **What the concept's pages draw that the Engine cannot do yet, found matching the pages to the concept** (2 Nov 2026). Each
    is drawn disabled with the reason, or drawn from what the Engine has:
   - **A case told in words** (Detective, What Detective noticed): the concept shows a short telling by the local model, with the
     people, files, times and programs marked. `detective.case` has no telling; the page writes the findings out instead and does
     not claim the model wrote them.
   - **Run a rule again where it went wrong** (Automation, an opened run): only on the machines where an action failed or timed out.
   - **Skip one scheduled run** (Automation, Coming up).
   - **The next scheduled runs** come from `calendar.board`'s rule items; a rule's own next run would be clearer.
   - **Worker service** (seen in the test run, not a UI matter): `worker_client/winnotify.py:112` (`_window_thread`) takes a Windows
     access violation during `tests/test_worker_client.py`; the tests still pass.

23. **What the console now calls that the Engine must answer (the user, 3-4 Nov 2026: "build exactly as the concept says, no compromises,
    just put into the engine docs that it needs to cover this so that session handles it").** The QML is built to the concept with these
    controls live, not disabled: until a handler exists, the button fails with the Engine's "unknown request" message. This replaces
    the "drawn disabled" lines of #20 and #22 for these items. Names are the QML's; change them with the UI session if another name is better.
   - **Any Admin verifies a task.** The concept gives every Admin Verify on Overview and Complete / Incomplete on Tasks, on tasks other
     Admins gave ("Only you close it"). `task.verify` must accept any Admin in version 1. **This changes an invariant** ("only manual
     verification by the assigner closes a task"): CLAUDE.md and `task-natural-combo.md` need the same change, confirmed with the user.
   - `task.remind {task_id}`: Remind on a late task.
   - **Requests to talk** (the rest of #19): `chat.requests {}` -> `{requests: [{id, from, account_id, host, at, line}]}`,
     `chat.request_accept {request_id}` -> `{conversation}`, `chat.request_close {request_id, why}`. The Messages section appears once
     `chat.requests` answers. (Correction: only a Worker writing back is built; a Worker asking is not.)
   - **Small groups:** `chat.open` with several people, and a group of them; today only the group of every Admin exists.
   - `issues.list` carries each issue's `detail` (a file issue's card says "in C:\\Users\\Ama\\Documents"; it is only on `issues.get`).
   - `issues.act` key `rule`: "Delete this every time from now on": fixes this one and makes the Automation rule.
   - **The file play in the concept's words:** no `ask` option (the QML hides it), `delete` resolves the issue; the timeline's second line is
     "Report written; every Admin sees it, and any of them may act on it" and the raised line "<type label> raised on <host>: <subject>".
   - `flow.remind {flow_id}`: remind whoever must pick a folder, for every waiting flow (today only through a flow issue).
   - `flow.keep {flow_id, path, keep: "new" | "both"}`: settle a file kept beside.
   - `flow.start {flow_id}`: start a stopped flow again.
   - `flow.list`: `sources[k].pause_reason` and `paused_at` (one source of several gone, the rest still go), each flow's `created_at`,
     each destination's `owner_account_id`; "A destination is off" reads the Admin's workstation from `hierarchy.tree`.
   - `update.now {pc_id}`: Update now on a machine behind on the version.
   - `machines.end_program {pc_id, name}`: End on a running program, then a notice on the person's screen.
   - `machines.get`: eight days of `check_ins` (the concept's week has eight columns; it sends seven).
   - `automation.run_again {event_id, at}` and `automation.skip {event_id, at}`.
   - `automation.board`'s `last_run` should say "20 succeeded", not "20 success" (the QML rewrites it for now).
   - `marks.allow_revoke {mark_id, allowance_id}`: Take it back on an allowed copy (`marks.get`'s `allowed` carries `allowance_id`).
   - **Rules:** `automation.skip {event_id, at, undo?}`, and `coming_up[k].skipped`, so a skip shows after a reload. `control.event_history`'s firings need
     `detail` (the sentence "Samsung BAR Plus 128 GB inserted", where `subject` is only a name) and `by_hand: true` for a rule run by hand, which the week's bars count apart.
     The rule sentence needs two more kinds of start, `printer.offline` ("a shared printer stops responding") and `threshold.signin` {count, window_s}
     ("5 sign-ins fail within 10 minutes"). The concept says only a rule's maker runs, edits or skips it ("only A. Quaye changes it"): `control.event_update`,
     `control.event_test` and `automation.skip` should refuse anyone else, and `control.event_list` must keep `created_by_account_id`.
   - **Actions:** `control.action_list` needs `impact` (the line after the description, "Users are not interrupted..."), `risky` (the red Run button) and
     `created_by_name` on a custom action. `actions.runs` needs `who` for a run by hand ("You" for the asker), which also groups one run across machines.
   - **Restricted:** `marks.get`'s `lately` needs `who` and `where` beside `what` ("Ama copied it to OPS-07"). `flows_allowed` needs `flow` (its name), `what`, `from`, `to`,
     `today` and `last_at`; `flow.restricted_waiting` needs `what`, `from` and `to`.
   - **Detective:** `detective.cases` rows need `restricted`, so every card can say "restricted files involved" (today only `detective.case`'s glance has it).
     The concept says "in the local model's words" and "Written by the local model": the page says so only when `telling.smoothed` is true, and with `SMOOTHING` off it
     says "from what Detective found" with the Engine's own `note`. Either the concept or `SMOOTHING` has to change for the two to agree.
   - **The editors (drawers, built 4 Nov 2026):** `control.event_create` / `event_update` send `action_limits {action_id: seconds}`, each action's limit in this rule
     ("Gets up to"); the Engine keeps only the action's own. Make a rule offers `printer.offline`, `threshold.signin {count, window_s}`, `threshold.disk` and
     `user.login` with `{outside_hours: true}`. `time.scheduled`'s `at` is an ISO date and time. Make a flow sends each asked destination a `note` ("A line for them"),
     `from_flow`, and `let_them_choose` with the Admin's workstation as `destination_pc_id`. `flow.create` keeps `on_source_delete` at "keep": the concept's drawer does not ask.
   - **The concept itself still shows "Sort by file type" and "sort"** in Flows, which `flow.steps` dropped on 3 Nov: the concept needs that change
     before the QML follows it.

## Done inline (for the record)

- **Registering machines by asking** (was #15, done 10 Oct 2026). A new Worker runs `python -m worker_client --engine
  host:port --ca engine.crt --enroll [--department ID] [--level worker|admin]`: it asks (`enroll.request`, one of only
  two requests accepted before the handshake, the other being `enroll.wait`), shows a four-digit code on its own screen
  (console and a Worker window), and waits. Nothing registers itself: the request waits in `enrollments` (migration
  019) and the Super User sees all of them, an Admin the ones for their department (`enroll.list`, with no code in it).
  Whoever confirms types the code (`enroll.confirm {enrollment_id, code, department_id?, level?}`); an Admin confirms
  only Workers in their own department, an Admin workstation needs the Super User; five wrong codes refuse it; it can
  be refused (`enroll.refuse`) and expires after 24 h. The account and PC are made by the same `provision()` as
  `hierarchy.account_create`. The machine is nudged (`enroll.decided`) and collects its client id and key with its
  token, once, ever (`collected` afterwards -- an Admin rekeys); they are written into its config and it carries on as a
  Worker. The confirmer never receives the key. Asks are rate-limited to five waiting per address and 100 in all, and
  audited (`enroll.requested/confirmed/refused/collected`). TUI: `enroll`, `enroll confirm <id> <code>`, `enroll
  refuse <id>`. The typed-name registration still works as the fallback. Not built (the console, not the Engine):
  the "Waiting to be registered" list on the department page and Must see. The Worker finds the Engine from the install
  package's address (`--engine`); a LAN broadcast to find it without one is not built. *Test:* `tests/test_enrollment.py`,
  `test_worker_client.py::test_a_new_worker_registers_itself_by_asking_and_then_runs`,
  `test_operator_client.py::test_scripted_enrollment`.

- **Everything the OS reports about files, recorded and used** (follow-up to #9, done 10 Oct 2026; the user: the OS emits
  move, rename and more, so cover what it emits rather than being narrow). *The gap that was there:* the Worker already
  sent a move with `old_path`, but the Engine used only the new path -- a move looked like a new file, the old place
  stayed in the index as if the file were still there, and a delete left no mark. *Now:* the Engine uses `old_path`,
  marks a place a file has left as `gone_at` (row kept) and keeps an append-only `file_events` history (migration 020) of
  create, move/rename, copy, delete, edit (once per ten minutes per file), **attribute changes** (read-only, hidden) and
  **permission/owner changes**, for files and for **folders** (created, moved/renamed, deleted; never index rows). The
  Worker's watcher (`worker_client/watcher.py`, `fsmeta.py`) tells a content edit from an attribute flip or a
  permission change by comparing two looks of the file (size and last write; attribute flags; a hash of owner, group
  and access list read with `GetFileSecurityW`), reports folder events, and in the polling fallback tells a move from a
  delete plus a create by the file's own identity (verified on this machine: read-only flag -> `attrib`, edit ->
  `modify`, an ACL change -> `security`, real renames/moves/folder events through the native watcher). The journey now
  shows renamed, moved, edited, attributes changed, permissions changed and deleted. Automations can wait on the new
  signals: `file.attributes_changed`, `file.permissions_changed`, `folder.created`, `folder.moved`, `folder.deleted`
  (a move's signal carries `old_path`). Flow, Resource and Task still hear only content changes. A place a file has
  left no longer counts as a collision, a copy elsewhere, a search hit or a folder entry. *Still open:* a file being
  *opened* (#2: the kernel trace, blocked); a folder renamed above a file is now followed into that file's journey (12 Oct 2026: the journey says "Its folder was renamed/moved" and does not count the same file under the new folder as a copy); the
  polling fallback sees no folders or permissions; `file_events` has no retention job yet. *Test:*
  `test_worker_client.py` (real filesystem: native and polling), `test_resource_assistance.py` (journey, automations).
- **A file's journey** (was #9, done 10 Oct 2026; the user decided: the journey only, not "required on every machine").
  `resource.journey {file_index_id}` follows a file by its CONTENT (the hash), because a copy has another path and
  sits on another machine, and returns its places and a timeline, oldest first: `first_seen` and `copied` (each place
  the same content was indexed, by when it first appeared there -- the index now keeps `first_seen_at`, migration
  018), `tagged` (audit, with who), `flagged` and `owner_told` (a Restricted File Tracking violation, and the person
  told), `resolved` (audit, with who) and `synced` / `conflict` (the flow sync log: a flow carried it to a machine, or an
  outside edit was in the way). Each event has a plain sentence. The Super User sees everything; an Admin only what
  happened on their own department's machines (a file with no place in it is "not found" to them); names are the
  caller's. Workers may not ask. TUI: `journey <file_index_id>`. Not covered: a rename or move is not a recorded event
  (a moved file is a new place with the same content). *Test:* `test_resource_assistance.py::test_a_files_journey_follows_its_content_and_stays_in_scope`,
  `test_operator_client.py::test_scripted_file_journey`.

- **Department tasks** (was #16, done 10 Oct 2026). A different thing from an Admin's task to a Worker (which keeps its
  checks; the old `task.propose`/`task.create` now refuse a Super User and point here). `task.dept_create
  {department_id, title, deadline_at, admin_ids?}` tells every Admin in the department, or only the ones picked
  (a department with no Admin is refused); `task.dept_mark {task_id, state: seen|ongoing|done}` is an Admin's own row
  only; the task *stands at* the furthest any Admin has got; `task.dept_complete` and `task.dept_reopen {note}` are the
  Super User who gave it only (reopen sends everyone who had finished back to ongoing, and every Admin on it gets the
  note); `task.dept_list` (the Super User: all; an Admin: the ones they were told, their own row only, and `unseen`
  for the strip across every page until they mark it seen) and `task.dept_get`. Pushes: `task.dept_assigned`,
  `task.dept_updated` (to the Super User), `task.dept_completed`, `task.dept_reopened`, `task.dept_deadline`. The one
  deadline is armed on create and on Engine start, and fires the `task.deadline_final` event (data `dept_task_id`).
  Tables `department_tasks`, `department_task_admins`, `department_task_notes` (migration 017). TUI: `dtask give|mark|
  complete|reopen`, `dtasks`, `dtask <id>`. *Test:* `test_task.py::test_a_department_task_is_not_an_admins_task`,
  `test_operator_client.py::test_scripted_department_task`.

- **A file action finds its file on each machine** (was #6, done 10 Oct 2026). `rename_file`, `restore_file` and
  `snapshot_file` name their file one of three ways: `path` (the same path on every machine, as before),
  `find_name` (a file name) or `find_hash` (a content hash); exactly one. For the last two the Engine looks the file up
  in the file index for each machine the action runs on and sends that machine its own path
  (`executions.locate_file`). A machine with no copy, or with several, is not guessed at: the run is recorded as failed
  with "the file is not on this machine" or "2 copies on this machine; name the path", audited as `action.not_run`, and
  nothing is sent. `control.file_locations {find_name|find_hash, pc_ids?}` previews it before anything runs: per
  machine found / missing / several, with the paths. TUI: `where <name> | hash=..`, and
  `action add control rename_file find_name=.. new_name=..`. (A department run includes the Admin's own workstation, as
  every department run does.) *Test:* `test_control_updates.py::test_a_file_action_uses_each_machines_own_path`.

- **Programs are picked, not typed** (was #5, done 10 Oct 2026). The Worker reports what runs (the process table
  grouped by program: name, how many, memory; every minute) and what is installed (Windows' own lists, read from the
  registry -- the Uninstall keys and App Paths -- with the program to start where it is known; on connect and every
  six hours): `control.inventory`. `control.programs {pc_ids?}` gives a console both, one row per program with how
  many machines it is on ("open on 5 machines"), most widespread first, scoped to the caller's department (the Super
  User: every machine); with one machine named it is exactly what is installed there. Installed programs are kept
  in `pc_programs` (migration 016); what runs is in memory and refilled within a minute after a restart. TUI:
  `programs [pcs=..]`. On this machine: 141 running programs, 96 installed (57 with a path to start).
  *Test:* `test_control_updates.py`, `test_worker_client.py`.

- **Actions that act on the person's screen, and a way to ask for help** (was #4 and #14, done 10 Oct 2026).
  `notify` takes `message` and `stay_s` (0 or absent: stays until the person closes it); `lock_session` takes
  `duration_s` and an optional `message` (the "Locked by your Admin" window for that long, then the screen is
  released); `reboot`/`shutdown` take `delay_s` (0-3600; the console offers 60 or 300) and a `message` beside the
  warning. The Engine checks the settings (`control.action_create/update`) and raises the run's timeout to the
  action's own length plus 30 s, so a lock is never cut short. The Worker runs them through the same detached
  path (`worker_client/builtins.py`), opening the message and locked windows, and says in the run's summary what
  happened ("closed by the person", "taken down after 20 s", "locked for 15 min"). Without PySide6 or with
  windows off, notify says "not shown" and a lock falls back to locking the workstation once. *Ask for help:* a
  tray icon (`worker_client/windows/tray.py`, started by the service) prints `ask` when clicked; the service
  asks `assistance.my_admins` (new: a Worker's department Admins, an Admin's Super User), opens the ask window
  (one button per Admin -- a help message carries no text, so there is no text box any more) and sends
  `assistance.ping`. TUI: `action add control notify message=.. stay_s=..`, `lock_session duration_s=..`,
  `reboot delay_s=..`; `actions` lists the optional settings. **A lock also blocks the keyboard and mouse at the OS level** (`BlockInput`) while its
  window holds; Windows ends the block if the process dies and Ctrl+Alt+Del always overrides it. Still for Phase 9: under the Windows service these
  windows and the tray must be started inside the person's session (a service has no desktop).
  *Test:* `test_control_updates.py`, `test_worker_client.py`, `test_resource_assistance.py`.

- **A machine's live state** (was #12, done 9 Oct 2026). Online means the machine's client holds an authenticated
  connection now (`Engine.online_pc_ids()`); `pcs.last_seen_at` (migration 015) records when it connected or dropped,
  and consoles get `pc.presence {pc_id, online}`. `hierarchy.traverse` refuses a machine that is not connected
  (`unavailable`, "FIN-02 is not reachable (last seen ...)"; `FALCON_REFUSE_UNREACHABLE=0` turns it off).
  `hierarchy.tree` rows carry `online` and `last_seen_at`; `hierarchy.pc_state {pc_id}` gives reachable, last seen,
  the latest levels and **what is in front**: the Worker now adds `foreground {program, title}` to `control.metrics`
  (`worker_client/foreground.py`, ctypes; under the Windows service this moves into the person's-session helper).
  TUI: `tree` shows online/offline, `pc state <pc_id>`.
  *Test:* `test_hierarchy.py::test_a_machine_that_is_not_connected_cannot_be_entered_and_says_since_when`.
- **What an action returned, kept with the run** (was #20, done 9 Oct 2026). A script (built-in or Custom) marks
  what it returns with lines the Worker strips from the text: `FALCON:summary <line>`, `FALCON:result <json>`,
  `FALCON:image <path>`. `control.execution_result` now stores the text (first and last 64 KB), the summary (on
  `action_executions.summary`, so every list has it) and the rows (`execution_outputs`, migration 014); the built-in
  monitoring actions return rows and a summary ("321 running · EXCEL.EXE uses the most memory"). Screenshots: the old
  PowerShell capture was blocked by Windows Defender as malicious, so `worker_client/screenshot.py` captures with GDI
  through ctypes, scales to 1600 px wide and fits 2 MB as PNG (stdlib only); the Worker sends it as
  `control.execution_image` before the result. `control.execution` returns output, result, `has_image`, `expired`;
  `control.execution_image_get` returns the picture (the run's department's Admins and the Super User, every view
  audited). After 90 days the audit retention job clears text, rows and picture (rows stay). TUI: `exec <id>`,
  `exec picture <id> <file>`. Still to do with packaging: under the Windows service the capture must run in the
  person's session as a helper. *Test:* `test_control_updates.py`, `test_worker_client.py` (executor).
- **A typical day for each level** (was #3, done 9 Oct 2026). `control.metrics` now also stores one sample per machine
  every 10 minutes in `metric_samples` (migration 013, never deleted); `control.levels` adds `typical`: the rolling
  7-day p10-p90 of processor, memory and idle across the same machines, with the sample count and since when (null
  until a sample exists). The min-max of now stays. TUI: `levels`.
  *Test:* `test_control_updates.py` (levels: a second report inside the interval is not stored).
- **A report keeps its words and each reader's "seen"** (was #7, done 9 Oct 2026). `reports.summary` holds the
  sentence `emit()` was given (migration 012); `reports.list` returns it with `seen_at` (this reader's first open,
  theirs alone) and `addressed_at`. `reports.seen {report_ids}` marks reports the reader can see; the first open is
  kept. Reports written before 012 have an empty summary. TUI: `report seen <ids>`.
  *Test:* `test_hierarchy.py::test_a_report_keeps_its_words_and_each_reader_sees_it_alone`.
- **Listeners from any department** (was #8, done 9 Oct 2026). `assistance.listener_candidates {channel_id}` lists
  every active Admin in every department, less the channel's two parties and those the caller already added, named
  as the caller names them; only a party may ask. TUI: `listen who <channel_id>`.
  *Test:* `test_resource_assistance.py` (HR's Admin offered to a Finance worker).
- **A task's checks in `task.list`** (was #11, done 9 Oct 2026). Every task row carries `checks_total` and
  `checks_passed`, so a list can say "2 of 3 checks passed" without a `task.get` per task; the TUI's `tasks` shows
  them as a `checks` column. *Test:* `test_task.py` (the list carries 0 of 2 after create).
- **An Admin belongs to one department** (was #13, closed 9 Oct 2026, the user's decision). Kept: assigning an Admin
  to a department without one means a new Admin account, or promoting one of its workers. The concept's "an Admin
  from another department, as well" option is removed.
- **The Super User watching every channel** (was #10, closed 9 Oct 2026, the user's decision). Not built: a channel
  is between two people, and a third party reads it only as a Listener added by a party (an Admin). The Super User's
  Messages page shows their own conversations with Admins.
- **A report category about an Admin, never routed; update escalations routed by default** (was #17, done 9 Oct
  2026). `about_admin` is a fixed category: `reports.routing_set` refuses it (FORBIDDEN) and `reports.routing_get`
  lists it under `fixed`. An Admin entering a machine outside working hours (`FALCON_WORKING_HOURS`, default
  06:00-18:00, the Engine host's local time; a span may cross midnight) raises one, to the Super User only. New
  departments start with `update_status` routed to them, and migration 011 gives existing departments the same
  default. *Test:* `test_about_admin_reports_reach_the_super_user_only_and_updates_route_by_default`.
- **Routing a kind of report, with or without what came before** (was #18, done 9 Oct 2026). A routed department used
  to see every report of the category, however old: visibility is read-time. `report_routing_config` gains
  `includes_earlier` (migration 010); `reports.routing_set` takes `include_earlier` (default true, the old
  behaviour) for the departments it adds, keeps the rows of departments already routed (so when each was routed and
  what it sees survive later edits), and answers `added`, `removed` and `earlier_unaddressed`. An empty list sends
  the category back to the Super User only; a removed department stops seeing it, and what it addressed stays in the
  Super User's View. Audited with all of it. TUI: `routing set <category> [ids] [earlier=no]`.
  *Test:* `test_routing_a_department_with_or_without_earlier_reports`.
- **A Super User automation seen from a department** (was #19, done 9 Oct 2026). An Admin could not see the Super
  User's organisation-wide automations at all. Now `control.event_list` and `control.dashboard` include those that
  reach the department (no machines named, or one of its machines named), marked `org_wide` / `read_only`;
  `control.event_update` and `control.event_delete` refuse them (FORBIDDEN); `control.event_history` counts runs on the
  department's machines only and says how many machines each firing reached (`machines`). Two more found on the way:
  the dashboard sent an Admin every running action in the organisation (now the department's only), and a Super
  User's timed automation with no machines named ran on none (it now runs on every department's machines).
  *Test:* `test_a_super_user_automation_is_seen_from_a_department_by_its_own_machines`.

- `control.event_history`, `control.levels`, `match.tier`, and time events firing on machine 0 (Automation).
- `flow.list` shapes and hostnames, `index.folders` (Flows).
- `resource.shelves`: files per tier across the department (Resources).
- `auth.respond` says a hostname mismatch back to the client; `hierarchy.session_state` says how long an Extend adds.

- **The session window under the Windows service** (12 Oct 2026, WP9). `worker_client/screenstream.py` captures the screen and applies input from the Worker process itself, which is right while the
  Worker runs in the person's session. As a Windows service (packaging, on hold) it runs in session 0, whose desktop is empty, so capture and input move into the person's-session helper like the
  `screenshot` built-in and the foreground reading: the Engine side (`session.screen`, `session.frame`, `session.input`) does not change.

- **Waiting on the user** (12 Oct 2026). (1) `file_events` has no retention job: the invariant is that the 90-day `audit_log` purge is the only hard delete, so purging this second history needs a decision. (2) A file being
  *opened* (kernel trace) and program starts caught at once were refused by the safety classifier and not retried; the 3-second look (and the native hooks that exist) stays.

- **The Worker as a service reaches the person's desktop by itself** (12 Oct 2026). `worker_client/winsession.py` starts a program on the signed-in person's desktop from the service
  (`WTSGetActiveConsoleSessionId`, `WTSQueryUserToken`, `CreateProcessAsUserW`, desktop `winsta0\default`, stdin/stdout pipes): the Worker's windows and tray, the desktop built-ins
  (`screenshot`, `notify`, `lock_session`, `start_process`, through `worker_client.runlogged`, which writes their output to the log the service reads) and a small helper
  (`worker_client/helper.py`, `userhelper.py`) that captures the screen and applies the console's input for the session window. Run as an ordinary user, none of it is used and a refusal
  never crashes anything. Nothing about the desktop needs setting up by hand. *Not exercised here:* the service-account path itself (this machine has no service installed; packaging is on hold).

- **File-event retention and the firewall** (13 Oct 2026). `file_events` now ages out on the audit trail's clock (`FALCON_AUDIT_RETENTION_DAYS`, 90): a file's journey reaches back as far as the trail does, and the one
  setting governs both; the "only hard delete" invariant in CLAUDE.md names both purges. `python -m engine setup` opens the Engine's port in a running `ufw` or `firewalld` on Linux (as root, else it prints the
  command); other firewalls are left alone and it says so; on a non-Linux machine it only says the Engine is meant for Linux. *Test:* `test_console_rollout.py`, `test_setup_firewall.py`.

- **The Worker as a Windows service: the necessary part of packaging, built and tested** (13 Oct 2026; the final packaging stays on hold). `python -m worker_client service install` (once, from an elevated prompt) registers the
  Worker as a service that starts with Windows, runs as the system account and restarts itself if it stops; `uninstall`, `start`, `stop`, `status` do the rest. `worker_client/winservice.py` speaks the service-control
  protocol through ctypes, so nothing extra is bundled; settings are the Worker's usual file (`%PROGRAMDATA%\Falcon\worker.json`), the log `%PROGRAMDATA%\Falcon\worker.log`. *Tested for real on this machine*
  (`test_worker_client.py`, elevated prompt only, each removing what it installed): a probe service reported that it runs as the system account in session 0, may trace programs and file opens, and started a program on the
  signed-in person's desktop; and the real Worker, installed as a service against a throwaway Engine, connected as FIN-01, appeared online with its version, OS and address, and went offline when stopped.
  *Not yet done (final packaging):* a bundled interpreter and installer, signing, the helper windows frozen as executables, and a pinned Engine certificate and key delivered with the install.

- **Flows: what the concept's Flows pages show that the Engine and Worker cannot do yet** (13 Oct 2026, found putting the concept's flow
  graph side by side with the QML). The console now keeps each step's name in its stage `config` as `op` (plus `by: "extension"` for
  Sort by file type, which the Worker already reads) and reads a flow's steps from the `parent_stage_id` tree: this is the smallest
  shape that lets a step come back as it was picked. The full `config` shape is still a deferred decision (spec §10), so it is for
  the user to confirm. **Built 2 Nov 2026** (migration 047; `flow.run`; `worker_client/pdf.py`): every step does what it says (Convert to
  PDF from text and JPEG only; Office formats need Office or LibreOffice and still say unsupported); a flow's name; real time, hourly or
  only when run; several sources merged into one flow (a further source is a flow of its own pointing at the first; a file of the same name
  from another source is kept beside, never overwritten); carrying on from another flow's destination; files copied per flow (all time and
  today); an edit retires the old steps. Still not: (4) below, and asking another Admin to pick the folder from the console (the TUI does it).
  Was open: (1) **the Worker carries out only Sort by file type.** Rename by date, Convert to PDF, Compress to ZIP and
  Sort by month are kept and drawn, but they leave the files as they are (`worker_client/flowsync.py` converts only txt/md/csv).
  (2) **An edit leaves the old stages on record.** `FlowsRepo.replace_structure` adds new `flow_stages` rows and keeps the old ones,
  and `flow.list` returns them all. The console counts only stages a live destination reaches, but the Engine should mark the old
  ones retired or leave them out of `shapes`. (3) **Not in the Engine, drawn disabled with the reason:** a flow's own name (flows are named
  `<source folder>-<id>`), several sources merging into one flow, carrying on from another flow, asking the Super User or another
  Admin to pick a folder on their own workstation, copying on a schedule or only when run, and the files-copied count per flow (the
  concept's "Files copied" column and figure; the console shows branches and the last copy instead). (4) A destination in remote
  storage (no machine) cannot be picked in the builder, so editing such a flow shows it as unset.

- **The console against the concept, page by page: what the Engine cannot back yet** (13 Oct 2026, found auditing every page at both
  levels against the published concept). Each is drawn disabled with the reason, or left out where the concept only decorates; nothing is faked.
  (1) **Rules:** a threshold on *disk* or *network* -- *built 2 Nov 2026:* `threshold.disk` (percent of the system drive) and `threshold.network` (KB/s received), from the readings the Worker already sends; `control.threshold_backtest` replays a threshold against the last week's stored readings (the rule builder's "would have fired").
  (2) **Actions:** *Test on one machine* for a script not saved yet: `control.action_run` takes a saved action id, so an unsaved draft cannot
  be tried; the button is disabled on New action. (3) **Tasks:** changing a department task after it is sent (Edit is disabled on the
  Super User's given tasks). (4) **Reports:** *Prompt the department* (the Super User nudging a department's Admins about a report they
  have not handled). (5) **History behind the headline figures:** the concept's small trends under the overview figures need a few days of
  each figure (KPI histories); the overviews show today's figure without a trend. Likewise a week of sessions and assisted access per
  department for the Departments page's day view beyond today. (6) **Flows** — see the entry above (names, files copied per flow,
  several sources, carrying on from another flow, asking someone to pick a folder, schedules).

- **The indexer and the event tracker run as their own supervised programs** (13 Oct 2026; decided in `docs/PACKAGING-PLAN.md`). `worker_client/indexer.py` (the
  file watcher and idle sweep, below-normal priority) and `worker_client/tracker.py` (the kernel trace and Windows notifications) are started by the service
  (`childproc.Supervised`), restarted when they die (1, 2, 5, 10, 30 seconds, back to the start after a minute of steadiness) and called unhealthy after five
  deaths in five minutes. They hold no Engine connection: what they report goes to the service over stdin/stdout and out through its one connection. Always so as
  a Windows service; `--separate` (or `separate_programs` in the settings) elsewhere; off for tests that drive the pieces directly. An unhealthy part is told to the
  Engine (`control.component_status`, migration 030) and is an issue on that machine ("Part of the Worker"), closed when it is steady again. *Tested:*
  `tests/test_children.py` (real child processes: killed and restarted, still reporting; a program that cannot start becomes unhealthy; the issue raised and
  closed), and for real as an installed service (elevated prompt): both parts run under it, a killed tracker comes back, a file the indexer saw reaches the
  Engine, and both go when the service stops. *Not done:* the UI helper is still started by the service on demand as before (already its own program).

- **The Worker's overlays and the keyboard, tried for real** (13 Oct 2026). With the windows installed (`PySide6-Essentials` is all the Worker's windows need; the `worker-ui` extra
  now asks for that, ~170 MB lighter than all of PySide6), entering a machine in *see* mode puts "<name> is viewing your screen" at the top of the person's desktop, and
  in *control* mode a card "<name> is using this machine · you can use it again when they leave, about 30 minutes" over it; both go when the session ends (picture taken from the
  desktop itself). The keyboard path was checked with `scripts/keyboard_check.py`: the Worker's input code typed text (including é and 中), Shift+A, ordinary keys and
  Backspace into a real window. Mouse control had been tried through the console. *Still only by a second machine:* the console's own key presses arriving through the session
  window (on one PC the viewer is its own target).

- **The installers' code, written and tested** (13 Oct 2026; compiling it into executables stays on hold). `installers/`: `roles.py` (what each installer carries), `payload.py`
  (a role's packages, the libraries read from `pyproject.toml`, a manifest of hashes; refuses any secret, test or cache), `bundle.py` (the Engine's address and certificate,
  no key, with its fingerprint), `engine/install.py` (Linux: user, folders, runtime, a PostgreSQL role with a made password, settings, `engine setup`, ownership, the bundle,
  a hardened systemd unit; plus `debian/` and `build_deb.sh`), `windows/install.py` (worker, admin, superuser: code, runtime, the public and the private folders with real ACLs,
  the service, the console shortcut, the Super User's own settings, a receipt, uninstall that keeps the key) and `windows/falcon.iss` (the wrapper for the later `setup.exe`).
  See `installers/README.md`. Machines register by probation, as decided: a service installed with no key asks, shows the code in the person's session (again if nobody was
  there), and keeps the key it is handed in the closed folder. An Admin's console holds no key: the service answers the Engine's challenge for it over a named pipe
  (`common/signpipe.py`). *Tested:* `tests/test_installers.py` (including, from an elevated prompt, an Admin workstation installed as a service that registers itself and
  whose keyless console signs in), `test_signpipe.py`, `test_enrollment.py`. *Run for real:* the Engine's installer on Linux (WSL), twice, with a Windows client connecting over the bundle's pinned certificate; the second run changed nothing. *Not run for real:* the Windows runtime venv with real wheels
  and the `.deb` build (the VMs); a non-administrator Windows user opening the pipe (the VM). *Still open:* a bundled interpreter, frozen helper windows, signing, the update pipeline, and whether
  the Super User's PC is also a managed machine.

- **Flow, Restricted and Task tried live, and what that found** (14 Oct 2026). `python scripts/live_drill.py flow|restricted|task|gui` runs real Worker processes on this PC against a running
  Engine and says PASS or FAIL per behaviour (28, 26, 26 and 36 checks; all pass now). It found and fixed: **Flow** -- a file over ~3 MB never arrived (one message longer than a
  connection reads; now chunks both ways, `CHUNK_BYTES`), a destination that was away lost what it missed with no status (now paused as `destination:unreachable`, resumed when it
  returns, and caught up: `flow.list` / `flow.listing`, `flow_sync_log.source_hash`, migration 031), a flow made over files already in the source folder or resumed after a pause sent
  nothing of what was missed (same catch-up), a file being written was read at every event (now once, `FALCON_FLOW_SETTLE_SECONDS`), unfinished transfers lived forever (failed after ten
  minutes); **Restricted** -- renaming or moving the marked original raised a copy issue against itself (the mark now follows a move: a move event, or a delete and a create of the same
  content within ten seconds; a folder move takes its marks along), an allowance matched by path alone so other restricted content saved there went unreported (now that content on that
  machine); **Task** -- `index.search` (the Task page's find-an-existing-file) failed on timestamps; **the index** -- files deleted while a Worker was away stayed "present" and
  caused false collisions, so a complete idle sweep now marks what it did not see as gone (`index.sweep_done`). *Open, decided by the user:* a file deleted at the source is not deleted
  at the destinations (the design says "updated to match source"); the index of a machine learns of offline deletions only at its next complete idle sweep; the console's forms
  (New flow, New task, Mark files) are tested against faked answers, and every page loads clean against the live Engine, but filling a form through the real console is not scripted;
  Task proposals were tried with the 0.6B model (the default 1.7B is not on this machine).

- **Proactive first, reactive second: the core heals itself** (16 Oct 2026, the user's rule). Events are the fast path; they are never the only path.
  *The index:* each Worker keeps what the Engine was last told (`worker_client/snapshot.py`, sqlite beside its settings) and `Watcher.reconcile()` compares its
  folders with it on connect, on a timer (`reconcile_seconds`) and after a failed report, sending exactly what appeared, changed or went as `index.catchup` events the
  Engine ingests as if they had happened live -- so Flow, Restricted and Task react to what happened while the machine was off or the Engine unreachable. The first look is a
  full baseline. A file is recorded only after the Engine took the report. *The Engine looks again by itself:* `flow.heal` (every running flow is caught up, 20 min),
  `marks.heal` (every marked content against everything the index holds, 30 min), `tasks.heal` (a file a task asked for that is already there is bound, 10 min), on top of
  the catch-up on create, resume, return and consent. *Collisions:* a flow never overwrites a file it did not write: the Engine tells the destination what the flow last
  wrote there (`previous`) and the Worker keeps anything else beside the new file as `<name>-modified` and says so (`flow.conflict`); a source file deleted and brought back
  finds its destination copy still there (deletes are not propagated) and no collision. *Also found and fixed on the way:* a stop that never finished (Python 3.10's
  `wait_for` can swallow a cancellation, so `task.cancel()` + `gather` hung the service; `worker_client/stopping.stop_tasks` cancels until it really stops), a modified
  file reported as deleted by the first reconcile, deadlines set in the console failing ("must be ISO 8601": JavaScript's `...Z` is refused by Python 3.10; `engine/isotime.py`),
  and the New flow form turning a collision into an error instead of the question it should be. *Tried live through the real console:* `python scripts/live_drill.py forms`
  (New flow with and without files at the destination, New task read by the 1.7B model, Mark files). The default 1.7B model is on this machine now.
