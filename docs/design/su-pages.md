# The Super User's pages (settled 21–23 Oct 2026)

The concept (`docs/design/concepts-snapshot.html`, published as "Falcon Concepts", v296) is the source of truth; this
records what each Super User page is for and the shape that was approved, so the QML can be built from it and nothing
has to be re-argued. Code names are the concept's components.

## The idea

The Super User is the organisation's CEO. Their pages read as an executive briefing, not a clerk's queue:

- **The situation first, in one sentence** (`SitBar`: an aim icon, a soft accent tint, "as of HH:MM").
- **Every decision comes with a recommendation**, taken only from that decision's own options (never invented), so the
  choice is "approve" or "see the alternatives".
- **Routine is batched; only exceptions are shown**, with how long they have waited and what waiting costs.
- **The page's input sits at its foot** (`og-change`: an accent dot and a faint tint so it is not skipped).
- **Colour is calm.** Red means act now, blue means yours to decide, everything else is neutral.
- **Lists that scale beat drawings.** Every page still carries at least a minimal visual (a thin bar, a tree, a map).

The Overview is the exception: it is the front door and a picture, with no sentence and no input.

## How the pages were made

Layout first, with no content: labelled regions only, agreed before anything is filled in. Then the content is grown
into exactly the approved regions and columns. A missing figure is proposed, never added silently. When the user names
one correction, only that correction is made. Three earlier redesigns were rejected on 21 Oct 2026 (department cards
and tracks; a rebuild; a desk of decision sheets and a kanban of letters), which is why the process is strict.

## The pages

### Overview (`OverviewHome`, `ovh-*`)
- **Waiting on you:** a rail of up to four decision cards. Each card shows its kind, how long it has waited, the
  recommendation, and Approve or Other options. After them comes "+N more in Inbox".
- **The organisation:** one row per department, with its machines as tiles. It is calm: only lagging machines (red)
  and offline ones (dashed) are marked. A department shows at most two rows of tiles plus "+N", and the map is paged
  four departments at a time.
- **Four tiles** beside the map: Directives, Admins, Protected and Departments. Each has a figure, a line, and a
  breakdown in words. There are no colour bars, because their meaning was unclear.
- **Your day** (`DayStrip`, 23 Oct 2026): seven two-hour columns with **Now kept in the middle**. The strip moves with the
  clock, so what is coming shows as it becomes relevant and the past columns fade. Each column shows at most two items,
  then "+N more". At the foot: "‹ N earlier, still open" and "N later ›", both opening Calendar. Its items are directive
  deadlines and scheduled notices. The Admin's Overview uses the same strip for "Today in the department".

### Inbox (`Inbox2`, `ib-*`)
- The situation sentence.
- **Decide today:** up to three memos, the issue on the left and the recommendation (with Approve and Other options)
  on the right. Beside them, "What waiting costs" and "Hand it to someone".
- **Routine, approve together.**
- At the bottom, "For your awareness" and "Decided by you".
- An Admin is recommended for an empty department only if:
  - their own department keeps another Admin;
  - they are not the subject of a report;
  - they have not been proposed twice.

### Directives (`Directives3`, `dv-*`)
- The situation sentence.
- **Back for your sign-off:** who did it and when, whether before or after its date, how long it has waited on you,
  and each Admin's state, with Complete and Send back.
- **How they stand:** four counts, each with a thin proportion bar.
- **Everything out:** one line per directive, grouped by deadline (past its date, today, this week, later), with pages.
- **Notices going out:** write a notice and schedule it, see what is scheduled, and see what was sent with
  **who has seen it**: "Seen by N of M Admins", a bar, who has not seen it, and a "Remind them" quick ask.
- At the foot, **Give a directive**.

### Departments (`DepartmentsBrief`, `og-*`)
- The situation sentence.
- A full-width **tree**: you at the root, then each department as a branch no taller than the root (40px pills), with
  its Admins as leaves and its lagging machines drawn.
- **Where it is thin.**
- **Machines refused at the door.** Registering is the Admin's work, so the Super User only sees refusals:
  - an unknown machine has **Send it to a department**;
  - a machine with an old key has **Ask its Admin(s)** to re-key it;
  - an impersonation has **Block it**;
  - every row has **Keep refusing**.
- At the foot, **Change the organisation**.

### Admins (`AdminsBrief`, `ad-*`, `al-*`)
- The situation sentence.
- **One line per Admin** with the columns Department, Machines, Directives out, Directives late, and Right now.
  Opening a line shows what is between you.
- **Needs a word from you:** one card per person with the reason and a Message button.
- **Who carries the most.**
- At the foot, **Change who looks after what**.

### Protected (`ProtectedLevels`, `PT_LV`, `PtTag`, `pt-*`, `pp-*`)
- **Three separate tags.** A file, folder or program carries exactly one, chosen after the target:
  - **Watch:** grey with an eye. Free to go and open; every open and move is noted.
  - **Private:** blue with a lock. Only the people you name may open or run it; anyone else is refused and noted.
    Nobody can ask to be added.
  - **Restricted:** red with a stop sign. It never leaves; copies are caught.
- **The list** is six per page, and the first item is open by default. An opened item holds its own settings (what it
  covers, who may open it, where it may be, Stop protecting) and its history. A stopped item is flagged, never deleted.
- **Waiting on you:** each entry starts with its item's name and tag, and clicking it picks the item in the list.
- **People around what you protect:** one line per person, with opened, refused and copies caught, the ones who stand
  out first. Its Person column lines up under the list's Tag column.
- At the foot, **Protect something**.

### Audit log (`AuditBrief`)
Approved as published (v257).

### Messages (`MessagesBrief`, `ms-*`)
- The situation sentence.
- **Conversations:** Unread (anything written since you last opened it), then Read. Rows carry a label when something
  is open with that person ("2 directives late"). Searching also finds people you have not talked to yet.
- **Groups:**
  - Choosing a department, or several people, makes one group chat.
  - Every department with two or more Admins has its own group.
  - A group shows stacked faces and who wrote each line.
  - Its members are listed in its header; click one to write to them alone.
  - The header also says how many answered your last message.
- **Requests:** an Admin's request to talk shows as a card with Accept, and writing back accepts it too. The Super
  User writing to an Admin needs no request.
- **No turn lock:** either side writes whenever they like.
- **Files:**
  - A paperclip in the message box sends one file, once, up to 100 MB. It arrives as a card with Save.
  - Sending is intentional access. Before sending, the page says what it means:
    - a Private file adds the receiver to who may open it;
    - a Restricted file's sending is the owner's consent for that copy.
  - If the sender is not the owner, the owner is asked first.
  - Programs and scripts are refused.
- At the foot, **Start a conversation**. One person goes to their own conversation; several people, or a department,
  go to a group.

### Calendar (`CalendarBrief`)
- The week-ahead sentence.
- The shared month (`CalendarPage` with `level=null`), with quieter grid lines than the Admin's.
- At the foot, **Put something on the calendar**: a directive or a notice, with a date picker.

## Rules that span pages

- **Quick asks** (Remind, Ask its Admin(s), Message about a reason) open in place as a short ready-made message with
  the context attached. It can be edited, and it lands in that person's conversation.
- **"Message them"** opens Messages with that person picked.
- **One waiting bar everywhere** (the user, 23 Oct 2026; `WaitBar`, `WaitAxis`, `waitSay`, `ibShould`). Every bar on a
  page covers the same fixed window, drawn once above the bars:
  - **The windows:** a week on the Inbox ("What waiting costs"), a day on the Admin's Issues queue.
  - **The bar fills from the left as time passes.** The line in the middle is the deadline, at the same place on every
    bar: reaching it is due, and the red past it is past due. The left end is half the window before the deadline (3½
    days on the Inbox, 12 hours on Issues), so an item with more time left than that shows no fill yet. A › means past
    the right end.
  - **The label** beside each bar reads the same thing in words: "1 day left", "3 days over", "due now", or "took 40m".
  - **"Should take"** is the item's own target where it has one (every issue does). Otherwise it goes by severity: 24h
    critical or high, 72h medium, 120h low.
  - **Tasks are the exception** (the user, 23 Oct 2026): a task carries its own timing, so its bar is measured against
    the task itself (`TaskBar`). The left half runs from when it was given to its final deadline; the line in the
    middle is that deadline, as on every bar; the right half is the same span again, for time over (red); a small tick
    marks the soft deadline;
    and a handed-in task's bar stops where it was handed in. There is no shared window.

## What the Admin receives (drawn on the Admin level, 22 Oct 2026)

- **A banner across the Admin's console** for every new directive and every new notice, with Open and "I've seen it".
  When more than one is new, it says "see all N".
- **The conversation with the Super User** is always present, with cards for directives and notices. Anything not seen
  yet is listed at the top, and each card has "I've seen it". This is where an Admin finds whatever they skipped.
- **Tasks → From the Super User** lists directives and the last two weeks of notices, with anything not seen first.
- **Department group conversations** appear in each member's Messages.

## Engine work this needs

Noted, not built: `docs/ENGINE-GAPS.md` items 3 (the Private tag), 4 (group conversations), 6 (what the Super User
sends reaches the Admin, including "seen" for notices) and 7 (sending a file). Item 5 (requests, no turn lock) is done
in the Engine and the clients.

## Next

The Admin's pages get their own pass. The Admin runs one department hands-on, so their pages are workbenches, not
briefings. Then the QML is brought up to the concept.
