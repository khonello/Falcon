import QtQuick
import "."

// WHEN THIS HAPPENS, DO THAT. One sentence per row, because that is all an automation is: something
// the machine notices, the machines it is watched on, and the Actions that follow in order.
Item {
    id: root

    property var events: []
    property var types: ({})
    property bool loaded: false
    property var chosen: null
    property var history: null

    readonly property var rows: events.map(function (e) {
        var spec = e.condition_spec || {}
        var acts = e.actions || []
        return { event_id: e.id, enabled: e.enabled,
                 when: Doing.eventName(spec.type),
                 where: Doing.scope(spec),
                 then: acts.length === 0 ? "nothing yet"
                       : acts.map(function (a) { return Doing.actionName(a) }).join(", "),
                 stateWord: e.enabled ? "on" : "off",
                 stateTone: acts.length === 0 ? "warn" : "",
                 lastFired: e.last_fired_at ? Task.when(e.last_fired_at) : "never",
                 polled: root.types[spec.type] === "polled",
                 event: e }
    })
    readonly property int idle: rows.filter(function (r) { return r.then === "nothing yet" }).length

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("control.event_list", {}, function (ok, r) {
            root.loaded = true
            if (!ok) return
            root.events = r.events || []
            root.types = r.types || ({})
        })
    }
    function open(row) {
        chosen = row
        history = null
        detail.open()
        falcon.call("control.event_history", { event_id: row.event_id }, function (ok, r) {
            if (ok) root.history = r
        })
    }
    function act(type, payload, said) {
        falcon.call(type, payload, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "It did not go through"); return }
            Msg.ok(said)
            detail.close()
            root.refresh()
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.events = []; root.loaded = false }
        function onPushReceived(type) { if (String(type).indexOf("event.") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s3

        PageHeader {
            width: parent.width
            title: "Automation"
            subtitle: root.rows.length + " automations"
                      + (root.idle > 0 ? " · " + root.idle + " with nothing to run" : "")
            Btn {
                objectName: "newEvent"
                kind: "primary"
                iconName: "plus"
                text: "New rule"
                onClicked: maker.open()
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - y
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Table {
                objectName: "automationTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 12
                rows: root.rows
                emptyText: "No automations yet"
                emptyHint: "An automation is one sentence: when something happens, run these Actions."
                onRowActivated: function (row) { root.open(row) }
                onRowToggled: function (row, on) {
                    root.chosen = row
                    root.act("control.event_update", { event_id: row.event_id, enabled: on },
                             on ? "On" : "Paused")
                }
                onRowAction: function (key, row) {
                    root.chosen = row
                    if (key === "out") retire.open()
                    else root.open(row)
                }
                columns: [
                    { title: "", key: "enabled", width: 56, toggle: function (r) { return r.enabled } },
                    { title: "When", key: "when", width: 240, strong: true },
                    { title: "On", key: "where", width: 130,
                      tone: function () { return "mid" } },
                    { title: "Run", key: "then",
                      tone: function (r) { return r.then === "nothing yet" ? "warn" : "mid" } },
                    { title: "Last time", key: "lastFired", width: 150, mono: true,
                      tone: function () { return "mid" } },
                    { title: "", key: "event_id", width: 44, menu: function (r) {
                        return [{ key: "open", label: "Open" },
                                { key: "out", label: "Take it out", danger: true, divided: true }]
                      } }
                ]
            }
        }
    }

    NewEvent {
        id: maker
        objectName: "newEventModal"
        page: root
        types: root.types
        onMade: root.refresh()
    }

    Confirm {
        id: retire
        objectName: "disableConfirm"
        page: root
        title: "Take this automation out"
        cost: "It stops firing. What it has already done stays on the record and keeps its reference, "
              + "so nothing in the trail goes missing -- but the rule does not come back on its own."
        verb: "Take it out"
        destructive: true
        onAccepted: root.act("control.event_delete", { event_id: root.chosen.event_id }, "Automation out")
    }

    Drawer {
        id: detail
        objectName: "eventDrawer"
        page: root
        title: root.chosen ? root.chosen.when : ""
        subtitle: root.chosen ? ("on " + root.chosen.where) : ""

        Descriptions {
            width: parent.width
            items: root.chosen ? [
                { label: "State", value: root.chosen.stateWord, tag: true },
                { label: "Noticed by", value: root.chosen.polled ? "asking, every so often"
                                                                 : "the machine, as it happens" },
                { label: "Last time", value: root.chosen.lastFired, mono: root.chosen.lastFired !== "never" }
            ] : []
        }

        Txt {
            width: parent.width
            text: "What it runs, in order"
            tone: "mid"
            font.pixelSize: Theme.fSmall
        }
        Column {
            width: parent.width
            spacing: 0

            Repeater {
                model: root.chosen && root.chosen.event ? (root.chosen.event.actions || []) : []
                delegate: Item {
                    required property var modelData
                    required property int index
                    width: parent.width
                    height: 32

                    Txt {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        text: (index + 1) + ".  " + Doing.actionName(modelData)
                        font.pixelSize: Theme.fSmall
                    }
                    Txt {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.timeout_seconds + "s"
                        tone: "quiet"
                        mono: true
                        font.pixelSize: Theme.fSmall
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
            visible: root.chosen && root.chosen.then === "nothing yet"
            text: "Nothing to run"
            hint: "It notices, and then does nothing. Attach an Action or take the rule out."
        }

        Alert {
            width: parent.width
            visible: root.history !== null && (root.history.firings || []).length === 0
            kind: "note"
            text: "It has never fired."
        }

        // the Drawer's footer is a Row: order places these, not anchors
        footer: [
            Btn {
                objectName: "disableEvent"
                danger: true
                text: "Take out"
                onClicked: retire.open()
            },
            Btn {
                objectName: "toggleEvent"
                kind: "primary"
                text: root.chosen && root.chosen.enabled ? "Pause" : "Turn on"
                onClicked: root.act("control.event_update",
                                    { event_id: root.chosen.event_id, enabled: !root.chosen.enabled },
                                    root.chosen.enabled ? "Paused" : "On")
            }
        ]
    }
}
