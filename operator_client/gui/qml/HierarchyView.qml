import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// The selected account/PC as the system sees it: who is there, which session holds it, how long
// is left, and the levers you have on it (traverse, block-or-end, end, extend, names, assisted
// access, rekey, offboard). The selection itself lives in the rail; this page is its detail.
Item {
    id: page
    readonly property var sel: root.selected
    readonly property var session: sel ? sel.session : null
    readonly property bool occupied: !!session
    readonly property bool occupiedByOther: occupied && session.occupied_via !== "native"
    readonly property bool iAmThere: !!falcon.session && !!sel && falcon.session.pc_id === sel.pc_id

    // deadline countdown for the session shown (theirs, or mine when I am the occupant)
    property int secondsLeft: -1
    function tick() {
        var s = page.session
        if (!s || !s.deadline_at) { page.secondsLeft = -1; return }
        page.secondsLeft = Math.max(0, Math.round((new Date(s.deadline_at) - new Date()) / 1000))
    }
    Timer { interval: 1000; running: page.occupied && !!page.session.deadline_at; repeat: true; triggeredOnStart: true; onTriggered: page.tick() }
    onSessionChanged: tick()
    function clock(secs) {
        if (secs < 0) return "—"
        var m = Math.floor(secs / 60), s = secs % 60
        return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s
    }

    // --- empty state -------------------------------------------------------------------------
    ColumnLayout {
        anchors.centerIn: parent
        visible: !page.sel
        spacing: Theme.space1
        Label { text: "No account selected"; color: Theme.textDim; font.pixelSize: Theme.fontLarge; font.bold: true; Layout.alignment: Qt.AlignHCenter }
        Label { text: "Choose an Admin or Client PC in the hierarchy on the left."; color: Theme.textFaint; font.pixelSize: Theme.fontSmall; Layout.alignment: Qt.AlignHCenter }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space4
        spacing: Theme.space3
        visible: !!page.sel

        // --- who ---------------------------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space3
            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true
                RowLayout {
                    spacing: Theme.space2
                    Label { text: page.sel ? page.sel.name : ""; color: Theme.text; font.pixelSize: Theme.fontHuge; font.bold: true; elide: Text.ElideRight }
                    StatePill { text: page.sel ? Theme.roleLabel(page.sel.role) : ""; tint: page.sel ? Theme.roleTint(page.sel.role) : Theme.textFaint }
                }
                Label {
                    text: page.sel ? page.sel.hostname + "  ·  pc " + page.sel.pc_id + "  ·  account " + page.sel.account_id + "  ·  " + page.sel.department_name + " (dept " + page.sel.department_id + ")" : ""
                    color: Theme.textFaint; font.pixelSize: Theme.fontSmall; font.family: Theme.mono
                }
            }
            StatTile {
                label: "Session"
                value: !page.occupied ? "FREE" : page.session.occupied_via.toUpperCase()
                tint: Theme.sessionTint(page.session)
                valueSize: Theme.fontLarge
            }
            StatTile {
                label: "Occupant"
                value: page.occupied ? (page.session.occupant_name || "—") : "—"
                unit: page.occupied && page.session.occupant_role ? page.session.occupant_role : ""
                tint: page.occupied ? Theme.roleTint(page.session.occupant_role) : Theme.textFaint
                valueSize: Theme.fontLarge
            }
            StatTile {
                label: "Time left"
                value: page.clock(page.secondsLeft)
                unit: page.occupied && page.session.extended_count ? "extended ×" + page.session.extended_count : ""
                tint: page.secondsLeft < 0 ? Theme.textFaint : (page.secondsLeft < 300 ? Theme.danger : Theme.warn)
            }
        }

        // --- levers -------------------------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space3

            Section {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                title: "Traversal"
                hint: page.iAmThere ? "You are inside this PC's view. The deadline is the Traversal Time Limit; extend it or end the session."
                    : page.occupiedByOther ? "Occupied. A vertical superior may block-or-end to enter; a peer is refused; a Super User occupancy cannot be evicted."
                    : page.occupied ? "The native user is at this PC. Traversing blocks them until your session ends or expires."
                    : "Free. Traversing opens a timed session inside this PC's view."
                accent: page.iAmThere ? Theme.warn : "transparent"
                RowLayout {
                    spacing: Theme.space2
                    Btn { text: "Traverse"; tint: Theme.accent; visible: !page.iAmThere
                          onClicked: falcon.call("hierarchy.traverse", {pc_id: page.sel.pc_id, force: false}, page.afterTraverse) }
                    Btn { text: "Block-or-end and enter"; danger: true; visible: !page.iAmThere && page.occupied
                          onClicked: falcon.call("hierarchy.traverse", {pc_id: page.sel.pc_id, force: true}, page.afterTraverse) }
                    Btn { text: "Extend my time"; tint: Theme.warn; visible: page.iAmThere
                          onClicked: falcon.call("hierarchy.extend_session", {session_id: falcon.session.session_id}, function(ok, r) { root.notify(ok ? "deadline now " + r.deadline_at.substring(11, 16) + " (extended " + r.extended_count + "×)" : r.message, !ok); rail.refresh() }) }
                    Btn { text: "End my session"; danger: true; visible: page.iAmThere
                          onClicked: falcon.call("hierarchy.end_session", {session_id: falcon.session.session_id}, page.afterSimple) }
                    Btn { text: "End their session"; danger: true; visible: page.occupiedByOther && !page.iAmThere
                          onClicked: falcon.call("hierarchy.end_session", {session_id: page.session.session_id}, page.afterSimple) }
                }
            }

            Section {
                Layout.preferredWidth: 360
                Layout.alignment: Qt.AlignTop
                title: "Names"
                hint: "A display name is private to your view and never propagates. Your self name is what those below you see."
                RowLayout {
                    spacing: Theme.space2
                    Field { id: label; Layout.fillWidth: true; placeholderText: "call " + (page.sel ? page.sel.name : "them") + " …" }
                    Btn { text: "Name"; enabled: label.text.length > 0
                          onClicked: falcon.call("hierarchy.set_display_name", {account_id: page.sel.account_id, label: label.text},
                                                 function(ok, r) { root.notify(ok ? "account " + r.account_id + " is now '" + r.label + "' in your view" : r.message, !ok); if (ok) { label.text = ""; rail.refresh() } }) }
                }
                RowLayout {
                    spacing: Theme.space2
                    Field { id: selfName; Layout.fillWidth: true; placeholderText: "your self name" }
                    Btn { text: "Set"; enabled: selfName.text.length > 0
                          onClicked: falcon.call("hierarchy.set_self_name", {label: selfName.text}, function(ok, r) { root.notify(ok ? "your self name is now '" + r.label + "'" : r.message, !ok); if (ok) selfName.text = "" }) }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space3

            Section {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                visible: falcon.role === "admin"
                title: "Assisted access"
                hint: "Admin ↔ Admin help across departments, by consent. A separate state from traversal: the helper gets a narrowed ceiling, never yours."
                RowLayout {
                    spacing: Theme.space2
                    CheckBox { id: avail; text: "I am available to help"; font.pixelSize: Theme.fontBody
                               onToggled: falcon.call("assisted_access.set_available", {available: checked}, function(ok, r) { root.notify(ok ? (r.available ? "available for assistance" : "not available") : r.message, !ok) }) }
                    Item { Layout.fillWidth: true }
                    Btn { text: "Request help for my department"; tint: Theme.assist
                          onClicked: falcon.call("assisted_access.request", {}, function(ok, r) { root.notify(ok ? (r.matched ? "offered to " + r.helper_name + " (request " + r.request_id + ")" : r.message) : r.message, !ok) }) }
                }
                RowLayout {
                    spacing: Theme.space2
                    Field { id: reqId; Layout.preferredWidth: 110; placeholderText: "request id" }
                    Btn { text: "Accept"; tint: Theme.assist; enabled: reqId.text.length > 0; onClicked: falcon.call("assisted_access.accept", {request_id: parseInt(reqId.text)}, function(ok, r) { root.notify(ok ? "assisting: session " + r.session_id : r.message, !ok); rail.refresh() }) }
                    Btn { text: "Decline"; enabled: reqId.text.length > 0; onClicked: falcon.call("assisted_access.decline", {request_id: parseInt(reqId.text)}, page.afterSimple) }
                    Btn { text: "Close"; enabled: reqId.text.length > 0; onClicked: falcon.call("assisted_access.close", {request_id: parseInt(reqId.text)}, page.afterSimple) }
                }
            }

            Section {
                Layout.preferredWidth: 360
                Layout.alignment: Qt.AlignTop
                title: "Provisioning"
                hint: "Rekeying invalidates this PC's client key and drops its connection; the new key is shown once. Offboarding deactivates the account — nothing is deleted."
                accent: Theme.danger
                RowLayout {
                    spacing: Theme.space2
                    Btn { text: "Issue new key"; tint: Theme.warn
                          onClicked: falcon.call("hierarchy.pc_rekey", {pc_id: page.sel.pc_id}, function(ok, r) {
                              if (!ok) { root.notify(r.message, true); return }
                              issued.text = "pc " + r.pc_id + "  (key generation " + r.key_generation + ")\nclient_id:  " + r.client_id + "\nclient_key: " + r.client_key
                              root.notify("pc " + r.pc_id + " rekeyed — give the new key to that install", false) }) }
                    Btn { text: "Offboard account"; danger: true
                          onClicked: falcon.call("hierarchy.account_offboard", {account_id: page.sel.account_id}, function(ok, r) { root.notify(ok ? "account " + r.account_id + " " + r.status : r.message, !ok); rail.refresh() }) }
                }
                TextArea { id: issued; visible: text.length > 0; Layout.fillWidth: true; readOnly: true; selectByMouse: true
                           font.family: Theme.mono; font.pixelSize: Theme.fontSmall; color: Theme.ok; wrapMode: TextEdit.NoWrap
                           background: Rectangle { color: Theme.canvas; radius: Theme.radius; border.width: 1; border.color: Theme.border } }
            }
        }

        Item { Layout.fillHeight: true }
    }

    function afterTraverse(ok, r) {
        if (!ok) { root.notify(r.message, true); return }
        var s = r.session
        root.notify((r.already_occupying ? "already inside" : "entered") + " pc " + s.pc_id + " — session " + s.session_id + ", until " + s.deadline_at.substring(11, 16)
                    + (s.restricted_view ? " (restricted view)" : ""), false)
        rail.refresh()
    }
    function afterSimple(ok, r) { root.notify(ok ? falcon.pretty(r) : r.message, !ok); rail.refresh() }
}
