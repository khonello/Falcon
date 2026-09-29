import QtQuick
import QtQuick.Controls.Basic
import "."

// PROPOSE, NEVER SILENTLY RESOLVE. The model reads the description and proposes what would show the
// task was done; it commits nothing. This modal is that rule made visible: ask, then read what came
// back, then commit it yourself. Two steps, and the second one cannot be skipped.
Modal {
    id: root
    width: 560
    title: root.proposal ? "What would show it is done" : "New task"
    subtitle: root.proposal ? "Read this before you commit it. Nothing is saved yet."
                            : "Say it the way you would say it to them."
    closePolicy: root.busy ? Popup.NoAutoClose : Popup.CloseOnEscape

    signal created()

    // step one
    property string description: ""
    property var assigneeId: null
    property bool tried: false
    // step two
    property var proposal: null
    property bool keepStack: true
    property bool keepSoft: true
    property bool keepFinal: true

    property bool busy: false
    property string problem: ""
    property var people: []                  // [{account_id, name, role, department}]

    readonly property string whoProblem: assigneeId === null ? "Pick who it is for." : ""
    readonly property string whatProblem:
        description.trim().length < 8 ? "Say what needs doing, in a sentence." : ""
    readonly property bool valid: whoProblem === "" && whatProblem === ""

    readonly property var peopleOptions: people.map(function (p) {
        return { value: p.account_id, label: p.name + "  ·  " + p.department }
    })
    readonly property var items: proposal && proposal.items ? proposal.items : []

    function reset() {
        what.text = ""
        description = ""
        assigneeId = null
        who.value = null
        tried = false
        proposal = null
        keepStack = true
        keepSoft = true
        keepFinal = true
        busy = false
        problem = ""
        loadPeople()
    }
    onAboutToShow: reset()

    // Super User assigns to Admins; an Admin assigns to Workers in their own department. The Engine
    // enforces that -- this only offers the people it would accept.
    function loadPeople() {
        if (!falcon.isConnected) return
        var want = falcon.role === "super_user" ? "admins" : "workers"
        falcon.call("hierarchy.tree", {}, function (ok, r) {
            if (!ok) return
            var out = []
            var depts = r.departments || []
            for (var i = 0; i < depts.length; i++) {
                var members = depts[i][want] || []
                for (var j = 0; j < members.length; j++)
                    if (members[j].status !== "suspended")
                        out.push({ account_id: members[j].account_id, name: members[j].name || "unnamed",
                                   role: members[j].role, department: depts[i].name })
            }
            root.people = out
        })
    }

    function propose() {
        tried = true
        if (!valid || busy) return
        busy = true
        problem = ""
        falcon.call("task.propose", { description: description.trim(),
                                      assignee_account_id: assigneeId }, function (ok, r) {
            root.busy = false
            if (!ok) { root.problem = r && r.message ? r.message : "Nothing came back."; return }
            root.proposal = r
            root.keepStack = (r.items || []).length > 0
        })
    }

    function commit() {
        if (busy) return
        busy = true
        problem = ""
        var payload = { description: description.trim(), assignee_account_id: assigneeId,
                        verification_mode: keepStack ? "stack" : "none" }
        if (keepStack) payload.items = items
        else payload.confirm_none = true
        if (keepSoft && proposal.soft_deadline) payload.soft_deadline_at = proposal.soft_deadline
        if (keepFinal && proposal.final_deadline) payload.final_deadline_at = proposal.final_deadline
        falcon.call("task.create", payload, function (ok, r) {
            root.busy = false
            if (!ok) { root.problem = r && r.message ? r.message : "It was not created."; return }
            Msg.ok("Task assigned")
            root.created()
            root.close()
        })
    }

    // --- step one: who, and what ------------------------------------------------------------------
    FormRow {
        width: parent.width
        visible: !root.proposal
        label: "For"
        required: true
        problem: root.tried ? root.whoProblem : ""
        Select {
            id: who
            objectName: "assigneeSelect"
            width: parent.width
            options: root.peopleOptions
            placeholder: falcon.role === "super_user" ? "Which Admin" : "Which worker"
            invalid: root.tried && root.whoProblem !== ""
            onPicked: function (v) { root.assigneeId = v }
        }
    }
    FormRow {
        width: parent.width
        visible: !root.proposal
        label: "What needs doing"
        required: true
        hint: "Naming the file and the program is what makes the checks worth having."
        problem: root.tried ? root.whatProblem : ""
        Area {
            id: what
            objectName: "descriptionArea"
            width: parent.width
            placeholderText: "Reconcile the Q3 invoices in reconciliation.xlsx by Friday"
            onTextChanged: root.description = text
        }
    }
    Alert {
        width: parent.width
        visible: !root.proposal && root.busy
        kind: "note"
        text: "Reading it. The model runs on the Engine, so this takes a few seconds."
    }

    // --- step two: what came back, and what of it you keep -----------------------------------------
    Alert {
        width: parent.width
        visible: root.proposal !== null && !root.proposal.llm_available
        kind: "warn"
        text: "The model is not reachable, so nothing was proposed. Assign it with nothing to check."
    }
    Alert {
        width: parent.width
        visible: root.proposal !== null && root.proposal.llm_available && root.proposal.needs_assigner
        kind: "warn"
        text: "Some of this was a guess. Read every line before you commit it."
    }
    Alert {
        width: parent.width
        visible: root.proposal !== null && (root.proposal.collisions || []).length > 0
        kind: "danger"
        text: root.proposal ? ((root.proposal.collisions || []).length
                               + " of these names already exist on their PC. Change the words and ask again.")
                            : ""
    }
    Alert {
        width: parent.width
        visible: root.proposal !== null && (root.proposal.proposed_split || []).length > 1
        kind: "warn"
        text: "This reads like more than one task. Assign it as one, or go back and split it yourself."
    }

    Column {
        width: parent.width
        visible: root.proposal !== null && root.items.length > 0
        spacing: 0

        Repeater {
            model: root.items
            delegate: Item {
                required property var modelData
                width: parent.width
                height: 34

                Txt {
                    anchors.left: parent.left
                    anchors.right: from.left
                    anchors.rightMargin: Theme.s2
                    anchors.verticalCenter: parent.verticalCenter
                    text: Task.say(modelData)
                    tone: root.keepStack ? "ink" : "quiet"
                    font.pixelSize: Theme.fSmall
                }
                Tag {
                    id: from
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.populated_by === "llm" ? "proposed" : "yours"
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.split
                }
            }
        }
    }
    Empty {
        width: parent.width
        visible: root.proposal !== null && root.items.length === 0 && root.proposal.llm_available
        text: "Nothing to check"
        hint: "Nothing in the description names a file or a program, so there is nothing to watch for."
    }

    FormRow {
        width: parent.width
        visible: root.proposal !== null
        label: "Check it"
        hint: root.keepStack ? "The Engine watches for these; only you close the task."
                             : "Nothing will be watched. You are saying so on purpose."
        Select {
            objectName: "modeSelect"
            width: parent.width
            value: root.keepStack
            options: [{ value: true, label: "Watch for the lines above" },
                      { value: false, label: "Nothing to check" }]
            onPicked: function (v) { root.keepStack = v }
        }
    }

    Column {
        width: parent.width
        spacing: 0
        visible: root.proposal !== null
                 && ((root.proposal.soft_deadline || "") !== "" || (root.proposal.final_deadline || "") !== "")

        Repeater {
            model: root.proposal ? [
                { label: "Nudge on", iso: root.proposal.soft_deadline || "", soft: true },
                { label: "Due by", iso: root.proposal.final_deadline || "", soft: false }
            ].filter(function (d) { return d.iso !== "" }) : []
            delegate: Item {
                required property var modelData
                width: parent.width
                height: 34

                readonly property bool kept: modelData.soft ? root.keepSoft : root.keepFinal

                Txt {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    tone: "mid"
                    font.pixelSize: Theme.fSmall
                }
                Txt {
                    anchors.right: drop.left
                    anchors.rightMargin: Theme.s2
                    anchors.verticalCenter: parent.verticalCenter
                    text: Task.when(modelData.iso)
                    tone: parent.kept ? "ink" : "quiet"
                    mono: true
                    font.pixelSize: Theme.fSmall
                }
                Btn {
                    id: drop
                    kind: "text"
                    small: true
                    text: parent.kept ? "Drop" : "Keep"
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: modelData.soft ? root.keepSoft = !root.keepSoft
                                              : root.keepFinal = !root.keepFinal
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.split
                }
            }
        }
    }

    Alert {
        width: parent.width
        visible: root.problem !== ""
        kind: "danger"
        text: root.problem
    }

    footer: [
        Btn {
            objectName: "taskBack"
            text: root.proposal ? "Back" : "Cancel"
            visible: !root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: go.left
            anchors.rightMargin: Theme.s2
            onClicked: root.proposal ? root.proposal = null : root.close()
        },
        Btn {
            id: go
            objectName: "taskSubmit"
            kind: "primary"
            text: root.proposal ? "Assign" : "Read it"
            loading: root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: Theme.s5
            onClicked: root.proposal ? root.commit() : root.propose()
        }
    ]
}
