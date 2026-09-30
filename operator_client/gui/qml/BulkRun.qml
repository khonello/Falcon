import QtQuick
import QtQuick.Controls.Basic
import "."

// ONE ACTION, ON THE MACHINES YOU CHOSE. The Engine runs an Action against one PC or one whole
// department -- never an arbitrary set -- so this sends one call per machine and says so. Each is its
// own execution with its own timeout, which is the design, not a shortcut.
Modal {
    id: root
    width: 480
    title: "Run on the chosen machines"
    subtitle: Theme.many(root.hosts.length, "machine") + ", each on its own"
    closePolicy: root.busy ? Popup.NoAutoClose : Popup.CloseOnEscape

    property var targets: []              // [{pc_id, host}]
    property var library: []
    property var actionId: null
    property bool tried: false
    property bool busy: false
    property int done: 0
    property int failed: 0
    property string problem: ""

    signal ran()

    readonly property var hosts: targets.map(function (t) { return t.host })
    readonly property var options: library.map(function (a) {
        return { value: a.id, label: Doing.actionName(a) + "  ·  " + a.timeout_seconds + "s" }
    })
    readonly property var chosenAction: {
        for (var i = 0; i < library.length; i++)
            if (library[i].id === actionId) return library[i]
        return null
    }

    function reset() {
        actionId = null
        pick.value = null
        tried = false
        busy = false
        done = 0
        failed = 0
        problem = ""
        load()
    }
    onAboutToShow: reset()

    function load() {
        if (!falcon.isConnected) return
        falcon.call("control.action_list", {}, function (ok, r) {
            if (!ok) return
            var g = r.actions || {}
            root.library = (g.control || []).concat(g.monitoring || [], g.custom || [])
        })
    }

    function run() {
        tried = true
        if (actionId === null || busy || targets.length === 0) return
        busy = true
        problem = ""
        done = 0
        failed = 0
        for (var i = 0; i < targets.length; i++)
            falcon.call("control.action_run", { action_id: actionId, pc_id: targets[i].pc_id },
                        function (ok, r) {
                if (ok) root.done += 1
                else { root.failed += 1; root.problem = r && r.message ? r.message : "One did not start" }
                if (root.done + root.failed === root.targets.length) {
                    root.busy = false
                    if (root.failed === 0) {
                        Msg.ok("Started on " + Theme.many(root.done, "machine"))
                        root.ran()
                        root.close()
                    }
                }
            })
    }

    FormRow {
        width: parent.width
        label: "Action"
        required: true
        problem: root.tried && root.actionId === null ? "Pick what to run." : ""
        Select {
            id: pick
            objectName: "bulkAction"
            width: parent.width
            options: root.options
            placeholder: "Which action"
            invalid: root.tried && root.actionId === null
            onPicked: function (v) { root.actionId = v }
        }
    }

    FormRow {
        width: parent.width
        label: "On"
        Flow {
            width: parent.width
            spacing: Theme.s1
            Repeater {
                model: root.hosts
                delegate: Tag { required property var modelData; text: modelData }
            }
        }
    }

    Alert {
        width: parent.width
        visible: root.chosenAction !== null
        kind: root.chosenAction && root.chosenAction.action_kind === "custom" ? "warn" : "note"
        text: root.chosenAction
              ? ("It starts on all " + root.targets.length + " the moment you press Run, and each gives up "
                 + "after " + root.chosenAction.timeout_seconds + "s."
                 + (root.chosenAction.action_kind === "custom"
                    ? " It is a script, and it runs unsandboxed." : ""))
              : ""
    }
    Progress {
        width: parent.width
        visible: root.busy || root.failed > 0
        value: root.targets.length === 0 ? 0 : (root.done + root.failed) / root.targets.length
        caption: root.done + " started"
    }
    Alert {
        width: parent.width
        visible: root.failed > 0
        kind: "danger"
        text: Theme.many(root.failed, "machine") + " did not start. " + root.problem
    }

    footer: [
        Btn {
            text: root.failed > 0 ? "Close" : "Cancel"
            visible: !root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: go.left
            anchors.rightMargin: Theme.s2
            onClicked: root.close()
        },
        Btn {
            id: go
            objectName: "bulkRunSubmit"
            kind: "primary"
            text: "Run"
            loading: root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: Theme.s5
            onClicked: root.run()
        }
    ]
}
