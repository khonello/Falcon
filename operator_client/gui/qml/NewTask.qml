import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// DESCRIBING A TASK (board TK05). Side by side: your words, and the structure the local model filled from them.
//
// The model PROPOSES, never settles (task-natural-combo.md). Whatever it could not settle is a DECISION: a deadline you
// gave two of, a new file whose name already exists, a file it could not find, no target at all, a description that
// reads as two tasks. Decisions are worked down ONE AT A TIME (the strip says which), each answered on the line it is
// about. "Confirm and assign" waits for all of them. "No verification applies" is always an explicit choice.
RowLayout {
    id: root

    property var tree: []
    property var proposal: null
    property var items: []                  // the working stack: proposed items, edited by your decisions
    property var resolved: ({})             // decision key -> true
    property bool noVerification: false
    property string finalText: ""
    property var assignee: null             // { account_id, name, hostname }
    property var pendingSplits: []          // parts still to describe after this one
    property bool proposing: false
    // a check added by hand: what kind of thing, and what must be true of it. Held as words on the page
    // and sent as the Engine's own terms (PATTERNS 11: nothing a person fills in reads as code)
    property string addKind: "file"
    property string addIntent: "create"
    readonly property var addIntents: addKind === "file"
        ? [{ v: "create", t: "is created" }, { v: "update", t: "is updated" }, { v: "exists", t: "exists already" }]
        : [{ v: "used", t: "was used" }, { v: "installed_available", t: "is installed" },
           { v: "closed_not_running", t: "is closed" }, { v: "running", t: "is running" }]
    function addIntentText(v) {
        for (var i = 0; i < addIntents.length; i++) if (addIntents[i].v === v) return addIntents[i].t
        return addIntents[0].t
    }
    function setAddKind(k) { addKind = k; addIntent = k === "file" ? "create" : "used" }
    signal created(int id)

    spacing: 20

    function reset() {
        proposal = null; items = []; resolved = ({}); noVerification = false; finalText = ""; pendingSplits = []
        desc.text = ""
    }

    // who can be given a task: an Admin gives to their department's workers; a Super User to Admins
    readonly property var people: {
        var out = []
        for (var i = 0; i < tree.length; i++) {
            var list = falcon.role === "super_user" && !shell.insideNow ? tree[i].admins : tree[i].workers
            for (var j = 0; j < list.length; j++) out.push(list[j])
        }
        return out
    }

    // --- the decisions, in order ------------------------------------------------------------------------
    readonly property var decisions: {
        if (!proposal) return []
        var out = []
        var flags = proposal.flags || []
        for (var i = 0; i < flags.length; i++) {
            var f = flags[i]
            out.push({ key: "flag" + i, kind: f.kind, flag: f,
                       label: f.kind === "ambiguous_deadline" ? "Which deadline"
                            : f.kind === "file_not_indexed" ? "Which " + f.name
                            : f.kind === "no_target" ? "What to check"
                            : f.kind === "contradiction" ? "A contradiction" : "Something unclear" })
        }
        var cols = proposal.collisions || []
        for (var c = 0; c < cols.length; c++)
            out.push({ key: "col" + c, kind: "collision", collision: cols[c], label: "A name that exists" })
        var split = proposal.proposed_split || []
        if (split.length >= 2) out.push({ key: "split", kind: "split", split: split, label: "Two tasks" })
        return out
    }
    readonly property var open: decisions.filter(function (d) { return !root.resolved[d.key] })
    readonly property var current: open.length > 0 ? open[0] : null
    function settle(key) { var r = {}; for (var k in resolved) r[k] = resolved[k]; r[key] = true; resolved = r }
    function setItem(i, patch) {
        var copy = items.slice()
        var o = {}; for (var k in copy[i]) o[k] = copy[i][k]
        for (var p in patch) o[p] = patch[p]
        copy[i] = o
        items = copy
    }

    function propose() {
        if (!assignee || desc.text.length === 0 || proposing) return
        proposing = true
        falcon.call("task.propose", { description: desc.text, assignee_account_id: assignee.account_id }, function (ok, r) {
            root.proposing = false
            if (!ok) { shell.notify(r.message, true); return }
            root.proposal = r
            root.resolved = ({})
            root.noVerification = false
            root.items = (r.items || []).map(function (i) {
                return { target_type: i.target_type, intent: i.intent, name: i.name, path: i.path || null,
                         linked_item_index: i.linked_item_index === undefined ? null : i.linked_item_index,
                         file_index_id: i.file_index_id === undefined ? null : i.file_index_id,
                         populated_by: "llm", removed: false }
            })
            root.finalText = r.final_deadline || ""
        })
    }
    function create() {
        var iso = finalText ? falcon.resolveDeadline(finalText) : ""
        if (finalText && !iso) { shell.notify("That deadline isn't a day and time Falcon can read", true); return }
        var soft = proposal && proposal.soft_deadline ? falcon.resolveDeadline(proposal.soft_deadline) : ""
        var kept = items.filter(function (i) { return !i.removed }).map(function (i) {
            return { target_type: i.target_type, intent: i.intent, name: i.name, path: i.path,
                     linked_item_index: i.linked_item_index, file_index_id: i.file_index_id, populated_by: i.populated_by }
        })
        var none = noVerification || kept.length === 0
        falcon.call("task.create", {
            assignee_account_id: assignee.account_id, description: desc.text,
            verification_mode: none ? "none" : "stack", confirm_none: none, items: none ? [] : kept,
            soft_deadline_at: soft || null, final_deadline_at: iso || null
        }, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            shell.notify("Given to " + (r.task.assignee_name || "them"), false)
            if (root.pendingSplits.length > 0) {                  // the next part of a split, described next
                desc.text = root.pendingSplits[0].description
                root.pendingSplits = root.pendingSplits.slice(1)
                root.proposal = null
                root.propose()
                return
            }
            root.created(r.task.id)
            root.reset()
        })
    }

    // ========================================================================================================
    // you write
    GridCell {
        objectName: "newTaskWords"
        Layout.preferredWidth: 440
        Layout.fillHeight: true
        topAlign: true
        title: "You write"
        narration: ({ brief: "plain language", state: "ok" })
        Column {
            width: parent.width
            spacing: 14
            Row {
                spacing: 10
                Txt { text: "For"; color: Theme.faint; font.pixelSize: Theme.fRow; anchors.verticalCenter: parent.verticalCenter }
                SentenceSlot {
                    objectName: "newTaskFor"
                    text: root.assignee ? root.assignee.name + (root.assignee.hostname ? " · " + root.assignee.hostname : "") : "choose someone"
                    tone: root.assignee ? "accent" : "warn"
                    onClicked: whoMenu.open()
                    Menu {
                        id: whoMenu
                        y: parent.height + 4
                        Repeater {
                            model: root.people
                            delegate: MenuItem {
                                required property var modelData
                                text: (modelData.name || "") + (modelData.hostname ? "  ·  " + modelData.hostname : "")
                                onTriggered: root.assignee = modelData
                            }
                        }
                    }
                }
            }
            Rectangle {
                width: parent.width
                height: 250
                radius: 12
                color: Theme.pane
                border.width: 1
                border.color: desc.activeFocus ? Theme.accent : Theme.line2
                TextArea {
                    id: desc
                    objectName: "newTaskText"
                    anchors.fill: parent
                    anchors.margins: 6
                    wrapMode: TextEdit.Wrap
                    placeholderText: "Say what needs doing, the way you would tell them."
                    font.family: Theme.sans
                    font.pixelSize: Theme.fRow
                    color: Theme.ink
                    background: null
                }
            }
            Row {
                spacing: 10
                TBtn { text: root.proposal ? "Propose again" : "Propose"; iconName: "pulse"; enabled: !!root.assignee && desc.text.length > 0 && !root.proposing
                       onClicked: root.propose() }
                Txt { text: root.proposing ? "The local model is reading it…" : "Nothing is assigned until you confirm."
                      color: Theme.faint; font.pixelSize: Theme.fMeta; anchors.verticalCenter: parent.verticalCenter }
            }
            Txt { visible: root.proposal && !root.proposal.llm_available; width: parent.width; wrapMode: Text.WordWrap; color: Theme.warn
                  font.pixelSize: Theme.fMeta; text: "The local model isn't available, so the structure was filled without it. Check each line." }
            Txt { visible: root.pendingSplits.length > 0; color: Theme.accent; font.pixelSize: Theme.fMeta
                  text: root.pendingSplits.length + (root.pendingSplits.length === 1 ? " more part" : " more parts") + " of the split to describe after this one" }
        }
    }

    // ========================================================================================================
    // it fills
    GridCell {
        objectName: "newTaskFills"
        Layout.fillWidth: true
        Layout.fillHeight: true
        topAlign: true
        title: "It fills"
        narration: ({ brief: !root.proposal ? "" : root.open.length === 0 ? "ready" : root.open.length + (root.open.length === 1 ? " decision left" : " decisions left"),
                      tone: root.proposal && root.open.length > 0 ? "warn" : "ok",
                      state: root.proposal ? "ok" : "empty", note: "Nothing proposed yet",
                      sentence: "Write what needs doing, choose who it's for, then Propose." })
        Column {
            width: parent.width
            spacing: 10

            // the decisions, one at a time
            Row {
                visible: root.decisions.length > 0
                spacing: 18
                Repeater {
                    model: root.decisions
                    delegate: Row {
                        required property var modelData
                        required property int index
                        readonly property bool done: !!root.resolved[modelData.key]
                        readonly property bool now: root.current && root.current.key === modelData.key
                        spacing: 7
                        Rectangle { width: 22; height: 22; radius: 11; anchors.verticalCenter: parent.verticalCenter
                                    color: parent.now ? Theme.warn : parent.done ? Theme.okSoft : Qt.rgba(1, 1, 1, 0.08)
                                    Txt { anchors.centerIn: parent; visible: !parent.parent.done; text: String(index + 1); font.pixelSize: Theme.fMeta
                                          font.weight: Font.Bold; color: parent.parent.now ? "#0d1018" : Theme.faint }
                                    Icon { anchors.centerIn: parent; visible: parent.parent.done; name: "check"; size: 12; color: Theme.ok; weight: 2.4 } }
                        Txt { text: modelData.label; font.pixelSize: Theme.fBody; anchors.verticalCenter: parent.verticalCenter
                              color: parent.now ? Theme.ink : Theme.faint; font.weight: parent.now ? Font.DemiBold : Font.Normal }
                    }
                }
            }
            Rectangle { visible: root.decisions.length > 0; width: parent.width; height: 1; color: Theme.line }

            // the structure, each line with its decision on it
            Repeater {
                model: root.items
                delegate: Column {
                    required property var modelData
                    required property int index
                    readonly property var col: root.current && root.current.kind === "collision" && root.current.collision.item_index === index ? root.current : null
                    readonly property var missing: root.current && root.current.kind === "file_not_indexed" && root.current.flag.item_index === index ? root.current : null
                    width: parent.width
                    spacing: 6
                    visible: !modelData.removed
                    Row {
                        spacing: 10
                        Txt { text: ({ create: "Create", update: "Update", exists: "Exists", used: "Used", used_with_file: "Used with",
                                       installed_available: "Installed", closed_not_running: "Closed", running: "Running" })[modelData.intent] || modelData.intent
                              color: Theme.tone(modelData.intent === "create" ? "ok" : "accent"); font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold
                              width: 70; anchors.verticalCenter: parent.verticalCenter }
                        Txt { text: modelData.name; color: Theme.ink; font.pixelSize: Theme.fRow - 1; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
                        Txt { text: modelData.file_index_id ? "found in the index" : modelData.target_type === "program" ? "a program on their machine"
                                    : modelData.intent === "create" ? (modelData.path ? "in " + modelData.path : "name only; found wherever it's saved") : "not found yet"
                              color: Theme.faint; font.pixelSize: Theme.fMeta; anchors.verticalCenter: parent.verticalCenter }
                    }
                    // a new file whose name already exists
                    Column {
                        visible: parent.col !== null
                        width: parent.width
                        spacing: 6
                        leftPadding: 80
                        Txt { text: modelData.name + " already exists on their machine" + (parent.parent.col ? " — " + parent.parent.col.collision.existing[0].path : "")
                              color: Theme.danger; font.pixelSize: Theme.fBody; font.weight: Font.Medium }
                        Row {
                            spacing: 6
                            GBtn { text: "It means the existing file"; small: true
                                   onClicked: { var c = root.current.collision
                                                root.setItem(index, { intent: "update", file_index_id: c.existing[0].file_index_id })
                                                root.settle(root.current.key) } }
                            Field { id: rename; width: 180; placeholderText: "or a new name" }
                            GBtn { text: "Use it"; small: true; enabled: rename.text.length > 0
                                   onClicked: { root.setItem(index, { name: rename.text }); root.settle(root.current.key) } }
                        }
                    }
                    // a file the model named but could not find
                    Column {
                        visible: parent.missing !== null
                        width: parent.width
                        spacing: 6
                        leftPadding: 80
                        Txt { text: parent.parent.missing ? parent.parent.missing.flag.ask : ""; color: Theme.warn; font.pixelSize: Theme.fBody }
                        Flow {
                            width: parent.width - 80
                            spacing: 6
                            Repeater {
                                model: parent.parent.parent.missing ? parent.parent.parent.missing.flag.candidates : []
                                delegate: GBtn { required property var modelData; text: modelData.path; small: true
                                                 onClicked: { root.setItem(index, { file_index_id: modelData.file_index_id }); root.settle(root.current.key) } }
                            }
                            GBtn { text: "Remove this check"; small: true
                                   onClicked: { root.setItem(index, { removed: true }); root.settle(root.current.key) } }
                        }
                    }
                    Rectangle { width: parent.width; height: 1; color: Theme.line }
                }
            }

            // the deadline: one line; two phrases become a question on it
            Column {
                visible: root.proposal !== null
                width: parent.width
                spacing: 8
                Row {
                    spacing: 10
                    Txt { text: "Deadline"; width: 70; color: Theme.faint; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
                    Field { id: deadlineField; width: 200; text: root.finalText; placeholderText: "e.g. Friday 5pm"
                            onEditingFinished: root.finalText = text }
                    Txt { text: root.finalText ? (falcon.resolveDeadline(root.finalText) ? "→ " + String(falcon.resolveDeadline(root.finalText)).substring(0, 16).replace("T", " ") : "Falcon can't read that yet") : "none"
                          color: root.finalText && !falcon.resolveDeadline(root.finalText) ? Theme.warn : Theme.faint; font.pixelSize: Theme.fMeta
                          anchors.verticalCenter: parent.verticalCenter }
                }
                Rectangle {
                    visible: root.current !== null && root.current.kind === "ambiguous_deadline"
                    width: parent.width; height: 74; radius: 10; color: Theme.warnSoft
                    Column { anchors.fill: parent; anchors.margins: 12; spacing: 8
                        Txt { text: "You wrote more than one deadline — which applies?"; color: Theme.warn; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                        Row { spacing: 8
                            Repeater {
                                model: root.current && root.current.kind === "ambiguous_deadline" ? root.current.flag.candidates : []
                                delegate: TBtn { required property var modelData; text: String(modelData); tone: "warn"; small: true
                                                 onClicked: { root.finalText = String(modelData); root.settle(root.current.key) } }
                            }
                        }
                    }
                }
            }

            // something the model could not settle that isn't tied to one line
            Rectangle {
                visible: root.current !== null && ["unclear", "contradiction", "no_target"].indexOf(root.current.kind) >= 0
                width: parent.width; height: 82; radius: 10; color: Theme.warnSoft
                Column { anchors.fill: parent; anchors.margins: 12; spacing: 8
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.warn; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                          text: !root.current ? "" : root.current.kind === "no_target" ? "Nothing to check was found in the words."
                                : root.current.kind === "contradiction" ? String(root.current.flag.detail || "The words contradict each other.")
                                : String(root.current.flag.question || "Part of it is unclear.") }
                    Row { spacing: 8
                        TBtn { visible: root.current && root.current.kind === "no_target"; text: "No verification applies"; tone: "warn"; small: true
                               onClicked: { root.noVerification = true; root.settle(root.current.key) } }
                        GBtn { text: root.current && root.current.kind === "no_target" ? "I'll add a check below" : "Carry on as it is"; small: true
                               onClicked: root.settle(root.current.key) }
                        Txt { text: "or change the words and Propose again"; color: Theme.faint; font.pixelSize: Theme.fMeta; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }

            // the split, drafted as a concrete choice
            Rectangle {
                visible: root.current !== null && root.current.kind === "split"
                width: parent.width; height: 96; radius: 10; color: Theme.pane
                Column { anchors.fill: parent; anchors.margins: 12; spacing: 8
                    Txt { text: "This reads as " + (root.current && root.current.split ? root.current.split.length : 2) + " tasks."; color: Theme.ink
                          font.pixelSize: Theme.fRow - 1; font.weight: Font.DemiBold }
                    Row { spacing: 8
                        Repeater {
                            model: root.current && root.current.split ? root.current.split : []
                            delegate: Txt { required property var modelData; required property int index
                                            text: (index + 1) + " · " + String(modelData.description).substring(0, 36); color: Theme.dim; font.pixelSize: Theme.fMeta }
                        }
                    }
                    Row { spacing: 8
                        TBtn { text: "Split as shown"; small: true
                               onClicked: { var parts = root.current.split
                                            desc.text = parts[0].description
                                            root.pendingSplits = parts.slice(1)
                                            root.propose() } }
                        GBtn { text: "Keep as one"; small: true; onClicked: root.settle(root.current.key) }
                    }
                }
            }

            // a check added by hand (the correction path), read as a sentence with slots (PATTERNS 7)
            Row {
                objectName: "newTaskAddCheck"
                visible: root.proposal !== null
                spacing: 8
                Txt { text: "Also check that a"; color: Theme.dim; font.pixelSize: Theme.fBody
                      height: 34; verticalAlignment: Text.AlignVCenter }
                SentenceSlot {
                    objectName: "addCheckKind"
                    text: root.addKind === "file" ? "file" : "program"
                    onClicked: kindMenu.open()
                    Menu {
                        id: kindMenu; y: parent.height + 4
                        MenuItem { text: "file"; onTriggered: root.setAddKind("file") }
                        MenuItem { text: "program"; onTriggered: root.setAddKind("program") }
                    }
                }
                Field { id: addName; width: 190
                        placeholderText: root.addKind === "file" ? "its name, like report-q3.docx" : "its name, like excel.exe" }
                SentenceSlot {
                    objectName: "addCheckIntent"
                    text: root.addIntentText(root.addIntent)
                    tone: "ok"
                    onClicked: intentMenu.open()
                    Menu {
                        id: intentMenu; y: parent.height + 4
                        Repeater { model: root.addIntents
                                   delegate: MenuItem { required property var modelData; text: modelData.t
                                                        onTriggered: root.addIntent = modelData.v } }
                    }
                }
                GBtn { text: "+ Add a check"; small: true; enabled: addName.text.length > 0
                       onClicked: { root.items = root.items.concat([{ target_type: root.addKind, intent: root.addIntent, name: addName.text,
                                                                      path: null, linked_item_index: null, file_index_id: null, populated_by: "manual", removed: false }])
                                    addName.text = ""; root.noVerification = false } }
            }

            Item { width: 1; height: 8 }
            Row {
                visible: root.proposal !== null
                spacing: 10
                GBtn { text: root.noVerification ? "Verification: none (chosen)" : "No verification applies"
                       onClicked: root.noVerification = !root.noVerification }
                TBtn { objectName: "newTaskConfirm"; text: "Confirm and assign"; iconName: "check"
                       enabled: root.open.length === 0 && !!root.assignee
                       onClicked: root.create() }
                Txt { visible: root.open.length > 0; text: "after " + root.open.length + (root.open.length === 1 ? " decision" : " decisions")
                      color: Theme.faint; font.pixelSize: Theme.fMeta; anchors.verticalCenter: parent.verticalCenter }
            }
        }
    }
}
