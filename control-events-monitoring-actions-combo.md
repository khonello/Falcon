# Control, Events, Monitoring & Actions Natural Combo

## Overview

This combo enables automated workflows and operational control through event-triggered actions. Users define what to monitor (Monitoring Actions), what to control (Control Actions), and what triggers them (Events). Together, they create an adaptive system that responds to conditions and gathers intelligence. A unified dashboard displays the output and status of all running automations.

**Interface Scope:** This entire combo — Control, Monitoring, Events, and Custom Actions — lives at the **Admin interface only**. There is no separate or parallel version for Super User. If a Super User wants to create or manage automations, they traverse down into a specific Admin's interface and operate there, exactly as they would for any other Admin-level function. This keeps the Super User interface focused on reports, audits, and status — not operational configuration.

---

## Core Concepts

### Action

**Definition:** A discrete operation or task that performs something—either controlling behavior or gathering data.

**Properties:**
- Belongs to **Control** or **Monitoring**
- Can execute **immediately** or **scheduled/automated**
- Can be triggered by an **Event** or run on a **schedule**
- Has **output** (results, data, status)
- Has a **timeout** — if exceeded, the action is terminated
- Can be **manually terminated** once started, independent of the timeout

**Execution Timing:**
- **Immediate:** Execute now
- **Scheduled:** Execute at specific time(s)
- **Delayed:** Wait X seconds/minutes before executing
- **Recurring:** Repeat on schedule (hourly, daily, weekly, etc.)

**Status Values:** Success, Failed, Pending, Terminated (via timeout or manual stop)

---

## Control

**Definition:** Actions that actively intervene and control system behavior.

**Control Actions:**
- **Mouse and Keyboard Control:** Remote input on client PCs
- **Shutdown:** Power down system
- **Reboot:** Restart system
- **Run Script:** Execute custom scripts or commands
- **Process Control:** Start, stop, or manage running processes
- **Configuration Change:** Modify system settings
- **File Operations:** Create, delete, move files
- **etc.**

**Purpose:** Actively manage and direct PC behavior and operations.

**Execution:**
- Triggered by Events or scheduled time
- Can be immediate or delayed
- Logged for audit trail

### Control Action Examples

**General (not software-specific):**
- Mouse/keyboard remote control
- Run script
- Shutdown/Reboot
- Process kill
- File operations (create, delete, move)
- Application launch/close

**Combo-Based (dependent on other combos):**
- Rename `-modified` files (Resource conflict handling)
- Restore from backup (Resource protection)
- Cancel running flow (Flow)
- Lock/unlock task (Task)
- Send alert to hierarchy (Hierarchy)

---

## Monitoring

**Definition:** Actions that passively observe and gather data about system state and activity.

**Monitoring Actions:**
- **System Usage Metrics:** CPU, memory, disk, network usage
- **Diagnostic Report:** System health snapshots
- **Screenshot:** Capture screen at moment of trigger
- **File Stalking:** Monitor specific file for changes (creation, modification, deletion)
- **Program Stalking:** Track when specific program is opened, closed, running
- **Pattern Matched Key-logging:** Capture keystrokes matching specific patterns (e.g., passwords, URLs)
- **Network Activity:** Monitor connections, bandwidth usage
- **Process Monitoring:** Track running processes and resource usage
- **etc.**

**Purpose:** Gather intelligence and visibility into system state and user activity.

**Execution:**
- Triggered by Events or scheduled time
- Results/data stored and displayed
- Can run continuously or on-demand

### Monitoring Action Examples

**General (not software-specific):**
- Screenshot
- System metrics (CPU, memory, disk, network)
- Active processes
- Network connections
- Logged-in users
- System logs

**Combo-Based (dependent on other combos):**
- Task target file/program activity (tracked via the Global File Index and OS events)
- Flow sync status
- Resource violation scan
- Help ping response time

---

## Custom Actions

**Definition:** User-authored actions that extend the built-in Control and Monitoring libraries with arbitrary PowerShell or Python code.

**How It Works:**
- Admin writes or pastes a PowerShell or Python script into the system
- Python is bundled with the program at install time — no separate dependency setup needed on target PCs
- Script is saved as a new Action, listed under a distinct **Custom** category in the action library (alongside Control and Monitoring, not merged into either)
- Integrates with Events exactly like built-in actions — any event can trigger it, same execution timing options (immediate, delayed, scheduled)

**Creation Authority:**
- **Admin only** — custom actions involve arbitrary code execution, so creation is restricted to the Admin interface
- Super User does not get a separate custom action tool; to create or manage one, they traverse into an Admin's interface

**Execution Model (v1):**
- **No sandboxing.** Custom Actions run with the same trust level as any other Control action created by that Admin. Since only Admin can author them, and Admin is already a trusted role in the hierarchy, accountability comes from the **audit trail** rather than execution isolation — every custom action logs who authored it, who/what triggered it, when, and on what target, making responsibility traceable without restricting what the code itself can do.
- **Standard library + Windows-native only.** The software targets Windows exclusively. Scripts (Python or PowerShell) are restricted to the language's standard library plus modules/libraries natively available on Windows — no external package installation. This avoids dependency/supply-chain risk without needing sandboxing to cover it, and keeps the bundled runtime self-contained.
- **Timeout and termination** apply the same as any Action (see Core Concepts) — a hanging script is terminated on timeout, and can also be manually stopped once running.

**Properties:**
- Name, description, script language (PowerShell or Python)
- Script content
- Execution timing (same as any Action)
- Output: captured and shown on the Dashboard like built-in Monitoring actions (script output, exit status, errors)

---

## Events

**Definition:** Triggers that listen for specific conditions; when they occur, associated actions execute.

**Evaluation Mechanism — Two Categories:**

Events aren't evaluated through one single mechanism — each event, based on what it's watching, falls into one of two categories:

- **Native/Pushed:** for events the OS already emits on its own — file system changes, USB insert/remove, login/logout, and similar. The system subscribes to these signals rather than checking for them, so there's no polling cost.
- **Polled/Evaluated:** for events that represent a *state* rather than a discrete occurrence — thresholds (CPU >80%), idle duration, scheduled time. These require a check on some interval since there's no native signal to subscribe to.

Since the full breadth of event types isn't pinned down yet, this is a governing principle rather than an exhaustive classification — each event type, as it's defined, gets classified into whichever mechanism actually fits how it's detected.

**Event Types:**
- **System Events:** USB inserted, file accessed, program launched, network connected, system idle
- **Time Events:** Scheduled time reached, recurring schedule triggered
- **Monitoring Events:** Threshold exceeded (CPU >80%), file changed, pattern detected
- **User Events:** Login detected, logout detected, action completed
- **etc.**

**Event Structure:**
- Define event condition (e.g., "USB inserted")
- Attach one or more Actions to execute when event fires
- Actions can be Control or Monitoring actions
- Attached actions execute independently of one another (see Actions + Events = Automation)

### Event Examples

**General (not software-specific):**
- USB inserted/removed
- File accessed/modified/deleted
- Program launched/closed
- System idle (X minutes)
- Login/logout
- Network connected/disconnected
- Threshold exceeded (CPU >80%, disk >90%)
- Time-based (daily, weekly, scheduled)

**Combo-Based (dependent on other combos):**
- Task started
- Task file appears
- Flow sync completed
- Flow sync error
- Resource file unauthorized access
- Help ping received
- Expectation signal triggered

**Example:**
```
Event: "USB Device Inserted"
  → Action 1: Take screenshot (Monitoring)
  → Action 2: Snapshot USB contents (Monitoring)
  → Action 3: Log event details (Monitoring)
  → Execution: Immediate for all actions
```

---

## Actions + Events = Automation

**Workflow Pattern:**

1. **Define an Event:** Specify condition to listen for (e.g., "Verification target file modified")
2. **Attach Actions:** Choose which actions to execute when event fires
3. **Set Timing:** Immediate, delayed, or scheduled execution
4. **Enable:** Activate the automation
5. **Monitor Output:** Dashboard shows when event fires, actions executed, results

**Actions Execute Independently — No Output Piping (v1):**

To keep the first iteration simple, actions attached to the same event do **not** pass output into one another. Each action runs with its own configured inputs and produces its own output/status, regardless of what other actions attached to the same event are doing.

- **Order is for display/sequencing clarity, not a data dependency.** Listing actions as 1, 2, 3 shows the order they're presented and triggered in, but action 2 doesn't wait on or receive anything from action 1's result to run correctly.
- **A failed action doesn't block others in the same chain.** Since there's no data dependency between them, one action failing has no technical reason to stop another from running. Each action's success/failure is tracked as its own independent status.

**Complex Automation:**
- Event A fires → Actions 1, 2, 3 each execute independently, each producing its own output
- A separately defined Event B (watching its own condition) can trigger further actions — this is still two independent events, not one action's output feeding the next event

**Examples:**

**Example 1: Task Completion Alert**
```
Event: "Verification target file appears (Create intent)"
  → Action 1: Screenshot (Monitoring)
  → Action 2: Send notification to Admin (Control)
  → Timing: Immediate
  → Result: Admin sees screenshot when file arrives
```

**Example 2: Resource File Protection**
```
Event: "File modified in /resources/restricted/"
  → Action 1: Snapshot original file (Monitoring)
  → Action 2: Rename modified file to -modified (Control)
  → Action 3: Restore from backup (Control)
  → Timing: Immediate
  → Result: Restricted files auto-protected
```

**Example 3: Daily System Audit**
```
Event: "Every day at 9 AM"
  → Action 1: Capture system metrics (Monitoring)
  → Action 2: Run diagnostic report (Monitoring)
  → Action 3: Check resource compliance (Monitoring)
  → Timing: Scheduled
  → Result: Dashboard shows daily audit results
```

---

## Dashboard

**Definition:** Unified operational view showing the output and status of all running automations and events.

**Dashboard Display:**

**Events Section:**
- List of all active events
- Status: Enabled/Disabled
- Last triggered: Timestamp
- Next scheduled: (if applicable)

**Actions Section:**
- List of all enabled actions
- Associated event(s)
- Last executed: Timestamp
- Status: Success/Failed/Pending/Terminated
- Execution timing: Immediate/Scheduled/Delayed

**Action Outputs:**
- Screenshots (if screenshot action triggered)
- Metrics/data (system usage, diagnostics)
- Logs (file changes, program access)
- Status messages (action completed, errors)
- Timestamps of execution

**View Options:**
- Filter by event, action type, or status
- Sort by latest, most frequent, or alphabetical
- Drill down into action results

**Toggle Modes:**

| Mode | Purpose | View |
|------|---------|------|
| **Editing Mode** (Toggle OFF) | Build and configure events/actions | Tabs (Events, Control, Monitoring) with libraries and configuration modals |
| **Dashboard Mode** (Toggle ON) | Monitor what's running and see results | Single-page dashboard showing active automations and outputs |

---

## User Interface Structure

### Editing Mode (Configuration)

**Lives at the Admin interface only** (see Interface Scope in Overview).

**Tabs:**
- **Events Tab:** Browse events, create new, configure triggers
- **Control Tab:** Library of control actions, enable/disable, configure
- **Monitoring Tab:** Library of monitoring actions, enable/disable, configure
- **Custom Tab:** Library of user-authored PowerShell/Python actions, create new, enable/disable, configure

**Event Tab Interaction:**
1. Select or create an event
2. Click [ + Action ] to attach actions (grows vertically)
3. Select action from library
4. Modal/section opens for execution timing (immediate, delayed, scheduled)
5. Configure timing and save
6. Actions stack vertically under event showing chain

**Action Configuration Modal:**
- Action name and description
- Execution mode: Immediate / Delayed (X seconds) / Scheduled (time/recurring)
- Parameters specific to action (if applicable)
- Save/Cancel buttons

### Dashboard Mode (Operational View)

**Single-Page Dashboard:**
- Shows only enabled events and their actions
- Displays real-time status of automations
- Shows outputs (screenshots, metrics, logs)
- Timestamps for when events fired and actions executed
- Live updates as events trigger and actions complete

**Example Dashboard Display:**
```
ENABLED AUTOMATIONS:

Event: USB Device Inserted (Last: 10 min ago)
  ├─ Action: Screenshot → SUCCESS (outputs displayed)
  ├─ Action: Snapshot USB Contents → SUCCESS (file list shown)
  └─ Action: Log Event → SUCCESS

Event: Daily 9 AM Audit (Next: Tomorrow 9 AM)
  ├─ Action: System Metrics → Last run yesterday 9 AM (metrics displayed)
  ├─ Action: Diagnostic Report → Last run yesterday 9 AM (report shown)
  └─ Action: Resource Compliance → Last run yesterday 9 AM (results shown)

Event: File Modified in /resources/restricted/ (Last: 5 hours ago)
  ├─ Action: Snapshot Original → SUCCESS (file hash shown)
  ├─ Action: Rename Modified File → SUCCESS
  └─ Action: Restore from Backup → SUCCESS
```

---

## Integration with Other Combos

**With Task:**
- Monitor event: "Task started" → Action: take screenshot, log event
- Monitor event: "Verification target file appears" → Action: notify admin
- Control event: "Task marked complete" → Action: archive files

**With Flow:**
- Monitor event: "Flow sync completed" → Action: verify destination files
- Monitor event: "File sync error" → Action: send alert, capture logs
- Control event: "Sync conflict detected" → Action: rename -modified file

**With Resource:**
- Monitor event: "File accessed from restricted folder" → Action: log access, take screenshot
- Control event: "Unauthorized access detected" → Action: revoke access, alert admin
- Monitor event: "Daily 9 AM" → Action: scan all PCs for resource violations, using the same Global File Index Resource's compliance detection already relies on

**With Hierarchy:**
- This combo's interface lives at the Admin level only (see Interface Scope in Overview) — Super User creates or manages automations by traversing into a specific Admin's interface, not through a separate system-wide tool
- Alerts from Actions propagate through system alerts
- Monitoring actions on admin PCs provide super user visibility once traversed in
- Custom Action executions are attributable to the authoring Admin via the audit trail, consistent with Hierarchy's traceability-over-restriction approach

---

## Key Principles

1. **Actions are Atomic:** Each action does one thing (monitor OR control)
2. **Events are Triggers:** Listen for conditions, fire when met — via native/pushed signals or polled evaluation, depending on what the event watches
3. **Actions Run Independently:** Multiple actions attached to one event each execute on their own, with no output piping between them (v1); listed order is for display, not a data dependency; one action failing doesn't block others
4. **Timing is Flexible:** Immediate, delayed, or scheduled execution
5. **Every Action Has a Timeout, and Can Be Manually Terminated:** applies uniformly, including Custom Actions
6. **Two Modes:** Edit mode for building, dashboard mode for operating
7. **Dashboard is Live:** Shows real-time status and outputs of automations (refresh mechanism: postponed, UI concern)
8. **Automation is Transparent:** All events, actions, and outputs logged and visible
9. **Hierarchy Respected:** Event/action creation authority follows role hierarchy
10. **Admin-Scoped Interface:** Control, Events, Monitoring, and Custom Actions live only at the Admin interface; Super User traverses in rather than getting a parallel tool
11. **Extensible via Custom Actions:** PowerShell/Python scripts (standard library + Windows-native only) extend the action library beyond built-ins, created by Admin only, integrating with Events the same way. No sandboxing in v1 — accountability comes from the audit trail, since only trusted Admins can author them.

**Postponed (tracked, not yet resolved):**
- Dashboard refresh mechanism (polling vs. push) — UI/implementation concern, addressed later
- Audit log retention policy — system-wide question, not specific to this combo; belongs in the Hierarchy document's Audit & Logging section

---

## Implementation Notes

- **Event Listener:** Native/pushed subscription for OS-emitted events (file system, USB, login/logout); polling loop for state-based/threshold/scheduled events
- **Action Execution:** Actions attached to one event run independently, no output piping between them (v1); each tracks its own status (Success/Failed/Pending/Terminated)
- **Timeout Enforcement:** Every action (including Custom) has a timeout; exceeding it terminates the action; manual termination also available once running
- **Custom Action Execution:** No sandboxing; runs at the authoring Admin's trust level; restricted to standard library + Windows-native modules only (no external package installation)
- **Output Storage:** Store action outputs (screenshots, logs, metrics) with timestamps
- **Audit Trail:** All events fired and actions executed logged with context (who, what, when, target) — this is the accountability mechanism for Custom Actions specifically
- **Performance:** Monitor resource usage of continuous monitoring actions
- **Security:** Restrict event/action creation by user role (Admin only, including Custom Actions)
- **Postponed:** Dashboard refresh mechanism; audit log retention policy (see Key Principles)
