import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Resource & Assistance: file search over the Global File Index, resource tags, violations,
// pings (unaddressed → respond opens a channel), turn-based message channels and listeners.
Item {
    id: view
    property var results: []
    property var pings: []
    property var channels: []
    property var channel: null      // {channel, messages}
    property var violations: []

    function refreshPings() { falcon.call("assistance.ping_status", {}, function(ok, r) { if (ok) view.pings = r.pings }) }
    function refreshChannels() { falcon.call("assistance.channels", {}, function(ok, r) { if (ok) view.channels = r.channels }) }
    function refreshViolations() { falcon.call("resource.violations", {include_resolved: showResolved.checked}, function(ok, r) { if (ok) view.violations = r.violations }) }
    function openChannel(id) {
        falcon.call("assistance.channel", {channel_id: id}, function(ok, r) { if (ok) view.channel = r; else root.notify(r.message, true) })
    }
    function refresh() { refreshPings(); refreshChannels(); refreshViolations() }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Connections {
        target: falcon
        function onConnected() { view.refresh() }
        function onPushReceived(type, p) {
            if (type.indexOf("assistance.") === 0) { view.refreshPings(); view.refreshChannels(); if (view.channel && p.channel_id === view.channel.channel.id) view.openChannel(p.channel_id) }
            if (type.indexOf("resource.") === 0) view.refreshViolations()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8
        RowLayout {
            Label { text: "Assistance & Resources"; font.pixelSize: Theme.fontLarge; color: Theme.text }
            SegmentedControl { id: tabs; segments: [{text: "Pings & channels"}, {text: "File search"}, {text: "Violations"}] }
            Btn { text: "Refresh"; onClicked: view.refresh() }
        }

        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            // --- pings & channels
            RowLayout {
                spacing: 10
                ColumnLayout {
                    Layout.preferredWidth: 420; Layout.fillHeight: true
                    RowLayout {
                        Eyebrow { label: "ping an account" }
                        Field { id: pingTo; Layout.preferredWidth: 70; placeholderText: "account" }
                        Btn { text: "Ping"; enabled: pingTo.text.length > 0
                                 onClicked: falcon.call("assistance.ping", {to_account_id: parseInt(pingTo.text)}, function(ok, r) { root.notify(ok ? "ping " + r.ping_id + " sent" : r.message, !ok) }) }
                    }
                    Label { text: "unaddressed pings to you (" + view.pings.length + ")"; color: Theme.textDim }
                    DataTable { id: pingTable; Layout.fillWidth: true; Layout.preferredHeight: 140; rows: view.pings
                                columns: ["id", "from_name", "sender_account_id", "sent_at"]; widths: ({id: 50, from_name: 150, sender_account_id: 70, sent_at: 130}); emptyText: "(none)" }
                    Btn { text: "Respond → open channel"; enabled: pingTable.selectedIndex >= 0
                             onClicked: falcon.call("assistance.respond", {ping_id: view.pings[pingTable.selectedIndex].id},
                                                    function(ok, r) { if (!ok) { root.notify(r.message, true); return } root.notify("channel " + r.channel_id + (r.opened ? " opened" : " already open"), false); view.refresh(); view.openChannel(r.channel_id) }) }
                    Eyebrow { label: "channels" }
                    DataTable { Layout.fillWidth: true; Layout.fillHeight: true; rows: view.channels
                                columns: ["id", "initiator_account_id", "superior_account_id", "turn", "opened_at", "closed_at"]
                                widths: ({id: 50, initiator_account_id: 70, superior_account_id: 70, turn: 80, opened_at: 130, closed_at: 130})
                                onRowClicked: function(row) { view.openChannel(row.id) } }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: Theme.surface; radius: Theme.radius; border.width: 1; border.color: Theme.border
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 6
                        RowLayout {
                            Label { color: Theme.text; font.bold: true
                                    text: view.channel ? "Channel " + view.channel.channel.id + " — " + (view.channel.channel.closed_at ? "closed" : (view.channel.channel.my_turn ? "your turn" : "waiting for the other party")) : "select a channel" }
                            Item { Layout.fillWidth: true }
                            Field { id: listener; Layout.preferredWidth: 70; placeholderText: "admin id"; visible: !!view.channel }
                            Btn { text: "Add listener"; visible: !!view.channel; enabled: listener.text.length > 0
                                     onClicked: falcon.call("assistance.add_listener", {channel_id: view.channel.channel.id, admin_account_id: parseInt(listener.text)}, function(ok, r) { root.notify(ok ? (r.added ? "listener added" : "already listening") : r.message, !ok) }) }
                            Btn { text: "Listeners"; visible: !!view.channel
                                     onClicked: falcon.call("assistance.my_listeners", {channel_id: view.channel.channel.id}, function(ok, r) { root.notify(ok ? "listeners: " + (r.listeners.map(function(l) { return l.name + " (" + l.listener_account_id + ")" }).join(", ") || "none") : r.message, !ok) }) }
                            Btn { text: "Close"; visible: !!view.channel && !view.channel.channel.closed_at
                                     onClicked: falcon.call("assistance.close_channel", {channel_id: view.channel.channel.id}, function(ok, r) { root.notify(ok ? "channel closed" : r.message, !ok); view.refresh(); if (ok) view.openChannel(r.channel_id) }) }
                        }
                        ListView {
                            id: msgs
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4
                            model: view.channel ? view.channel.messages : []
                            delegate: Label {
                                required property var modelData
                                width: msgs.width; wrapMode: Text.Wrap; color: Theme.textDim
                                text: modelData.sent_at.substring(11, 16) + "  " + (view.channel.channel.names[String(modelData.sender_account_id)] || modelData.sender_account_id) + ": " + modelData.body
                            }
                            onCountChanged: positionViewAtEnd()
                        }
                        RowLayout {
                            visible: !!view.channel && !view.channel.channel.closed_at
                            Field { id: body; Layout.fillWidth: true; placeholderText: view.channel && view.channel.channel.my_turn ? "your message" : "not your turn"; enabled: !!view.channel && view.channel.channel.my_turn
                                        onAccepted: sendBtn.clicked() }
                            Btn { id: sendBtn; text: "Send"; enabled: body.enabled && body.text.length > 0
                                     onClicked: falcon.call("assistance.message", {channel_id: view.channel.channel.id, body: body.text},
                                                            function(ok, r) { if (ok) { body.text = ""; view.openChannel(view.channel.channel.id) } else root.notify(r.message, true) }) }
                        }
                    }
                }
            }

            // --- file search + tagging
            ColumnLayout {
                RowLayout {
                    Field { id: query; Layout.fillWidth: true; placeholderText: "file name or path fragment"; onAccepted: searchBtn.clicked() }
                    Btn { id: searchBtn; text: "Search"; enabled: query.text.length > 0
                             onClicked: falcon.call("assistance.search", {query: query.text}, function(ok, r) { if (ok) view.results = r.results; else root.notify(r.message, true) }) }
                }
                DataTable { id: resultTable; Layout.fillWidth: true; Layout.fillHeight: true; rows: view.results
                            columns: ["id", "pc_id", "path", "resource_tag", "resource_tag_scope_department_id", "last_seen_at"]
                            widths: ({id: 60, pc_id: 50, path: 500, resource_tag: 90, resource_tag_scope_department_id: 60, last_seen_at: 130}); emptyText: "(no results)" }
                RowLayout {
                    Label { text: resultTable.selectedIndex >= 0 ? "tag file " + view.results[resultTable.selectedIndex].id : "select a file to tag"; color: Theme.textDim }
                    Picker { id: tag; model: ["admin", "restricted", "workers", "common"]; Layout.preferredWidth: 120 }
                    Field { id: tagDept; Layout.preferredWidth: 70; placeholderText: "dept (opt)" }
                    Btn { text: "Tag"; enabled: resultTable.selectedIndex >= 0
                             onClicked: falcon.call("resource.tag", {file_index_id: view.results[resultTable.selectedIndex].id, tag: tag.currentText, scope_department_id: tagDept.text ? parseInt(tagDept.text) : null},
                                                    function(ok, r) { root.notify(ok ? "file " + r.file_index_id + " tagged " + r.tag : r.message, !ok); if (ok) searchBtn.clicked() }) }
                }
            }

            // --- violations
            ColumnLayout {
                RowLayout {
                    CheckBox { id: showResolved; text: "include resolved"; onToggled: view.refreshViolations() }
                    Item { Layout.fillWidth: true }
                    Btn { text: "Resolve"; enabled: vTable.selectedIndex >= 0
                             onClicked: falcon.call("resource.resolve", {violation_id: view.violations[vTable.selectedIndex].id}, function(ok, r) { root.notify(ok ? "violation " + r.violation_id + " resolved" : r.message, !ok); view.refreshViolations() }) }
                }
                DataTable { id: vTable; Layout.fillWidth: true; Layout.fillHeight: true; rows: view.violations
                            columns: ["id", "hostname", "filename", "expected_tag", "detected_via", "detected_at", "resolved_at", "report_id", "path"]
                            widths: ({id: 50, hostname: 100, filename: 160, expected_tag: 90, detected_via: 100, detected_at: 130, resolved_at: 130, report_id: 70, path: 400}); emptyText: "(no violations)" }
            }
        }
    }
}
