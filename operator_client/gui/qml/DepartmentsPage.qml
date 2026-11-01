import QtQuick
import "."

// DEPARTMENTS (version 1, the user, 1 Nov 2026; docs/design/v1-it-admin.md). A department is a label an Admin makes and puts
// machines in, for grouping and filtering; it is never a wall, and every IT Admin reaches every one. On the left the
// departments as cards: a click picks one, Expand opens its name to change. On the right the picked one's machines as the
// Overview's tiles, and every other machine under where it is now: a click moves it in. Making an Admin is never here.
Page {
    id: page
    objectName: "departmentsView"

    property var sel: null                 // the picked department's id
    property var exp: null                 // the expanded one's id
    property string ren: ""
    property string nm: ""
    property string q: ""
    property bool more: false
    readonly property int cap: 40

    readonly property var depts: Fleet.depts
    readonly property var all: Fleet.machines
    readonly property var cur: { for (var i = 0; i < depts.length; i++) if (depts[i].id === sel) return depts[i]; return depts.length ? depts[0] : null }
    function inD(id) { return all.filter(function (m) { return m.dept === id }) }
    readonly property var elsewhere: cur ? all.filter(function (m) { return m.dept !== cur.id && (m.host + " " + (m.user || "")).toLowerCase().indexOf(q.trim().toLowerCase()) >= 0 }) : []
    readonly property var shown: more ? elsewhere : elsewhere.slice(0, cap)
    readonly property var groups: !cur ? [] : depts.filter(function (d) { return d.id !== cur.id })
        .map(function (d) { return { name: d.name, ms: page.shown.filter(function (m) { return m.dept === d.id }) } })
        .filter(function (g) { return g.ms.length > 0 })

    function make() {
        var name = nm.trim()
        if (!name) return
        falcon.call("hierarchy.department_create", { name: name }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not made"); return }
            Msg.ok(name + " made · put machines in it on the right")
            page.nm = ""; page.sel = r.department_id; Fleet.refresh()
        })
    }
    function rename(d) {
        var name = ren.trim()
        if (!name || name === d.name) return
        falcon.call("hierarchy.department_rename", { department_id: d.id, name: name }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not renamed"); return }
            Msg.ok(r.was + " is now " + r.name); page.exp = null; Fleet.refresh()
        })
    }
    function moveIn(m) {
        var d = cur
        var doIt = function () {
            falcon.call("hierarchy.pc_move", { pc_id: m.pc_id, department_id: d.id }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not moved"); return }
                Msg.ok(m.host + " is in " + d.name + " now"); Fleet.refresh()
            })
        }
        confirm.ask({ title: "Move " + m.host + " to " + d.name + "?", ok: "Move it",
                      text: "It leaves " + m.deptName + ". A department is only a label: nothing on the machine changes, and every Admin still reaches it." }, doIt)
    }

    Confirm { id: confirm }

    Txt {
        width: parent.width
        color: Theme.text2
        wrapMode: Text.WordWrap; elide: Text.ElideNone
        text: Theme.many(page.depts.length, "department") + " and " + Theme.many(page.all.length, "machine") + ". Every IT Admin reaches every department."
    }

    Row {
        id: two
        width: parent.width
        spacing: 14
        readonly property real h: Math.max(left.implicitHeight, right.implicitHeight)

        // --- the departments ---------------------------------------------------------------------------
        Panel {
            id: left
            width: (parent.width - 14) * 0.5
            height: two.h
            title: "Departments · " + Theme.fmt(page.depts.length)
            sub: "a label for grouping machines and the people at them; click one to see its machines, expand it to rename it"
            Column {
                width: parent.width
                spacing: 8
                Txt { visible: page.depts.length === 0; text: "No departments yet. Make one below."; color: Theme.text3 }
                Repeater {
                    model: page.depts
                    delegate: Rectangle {
                        id: card
                        required property var modelData
                        readonly property bool picked: page.cur !== null && page.cur.id === modelData.id
                        readonly property bool open: page.exp === modelData.id
                        readonly property var ms: page.inD(modelData.id)
                        objectName: "deptCard-" + modelData.id
                        width: parent.width
                        height: inner.height + 20
                        radius: Theme.radius
                        color: picked ? Theme.accentSoft : Theme.surface
                        border.width: 1
                        border.color: picked ? Theme.accent : Theme.border
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.sel = card.modelData.id }
                        Column {
                            id: inner
                            x: 12; y: 10
                            width: parent.width - 24
                            spacing: 10
                            Row {
                                width: parent.width
                                spacing: 10
                                Column {
                                    width: parent.width - facts.width - expand.width - 20
                                    anchors.verticalCenter: parent.verticalCenter
                                    Txt { width: parent.width; text: card.modelData.name; font.weight: Font.DemiBold }
                                    Txt { width: parent.width; color: Theme.text3; font.pixelSize: Theme.fSmall
                                          text: card.ms.length ? card.ms.slice(0, 4).map(function (m) { return m.host }).join(", ") + (card.ms.length > 4 ? " and " + (card.ms.length - 4) + " more" : "") : "no machines yet" }
                                }
                                Column {
                                    id: facts
                                    anchors.verticalCenter: parent.verticalCenter
                                    Txt { text: Theme.many(card.ms.length, "machine"); font.pixelSize: Theme.fSmall; elide: Text.ElideNone }
                                    Txt { readonly property int n: card.ms.filter(function (m) { return !!m.user }).length
                                          text: n + (n === 1 ? " person" : " people"); color: Theme.text3; font.pixelSize: Theme.fSmall; elide: Text.ElideNone }
                                }
                                Btn {
                                    id: expand
                                    objectName: "deptExpand"
                                    small: true; kind: "text"
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: card.open ? "Collapse" : "Expand"
                                    iconName: card.open ? "chevu" : "chevd"; iconRight: true
                                    onClicked: { page.sel = card.modelData.id; page.ren = card.modelData.name; page.exp = card.open ? null : card.modelData.id }
                                }
                            }
                            Column {
                                visible: card.open
                                width: parent.width
                                spacing: 8
                                Field { objectName: "deptRename"; width: parent.width; text: page.ren; placeholderText: "Name"; onTextEdited: page.ren = text; onAccepted: page.rename(card.modelData) }
                                Row {
                                    width: parent.width
                                    spacing: 10
                                    Txt { width: parent.width - rn.width - 10; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 12
                                          wrapMode: Text.WordWrap; elide: Text.ElideNone; text: "The new name shows everywhere the department does; its machines stay in it." }
                                    Btn { id: rn; small: true; text: "Rename"; enabled: page.ren.trim() !== "" && page.ren.trim() !== card.modelData.name; onClicked: page.rename(card.modelData) }
                                }
                            }
                        }
                    }
                }
            }
        }

        // --- the picked department's machines, and the rest to move in ----------------------------------
        Panel {
            id: right
            width: (parent.width - 14) * 0.5
            height: two.h
            title: page.cur ? page.cur.name : "No department picked"
            sub: page.cur ? Theme.many(page.inD(page.cur.id).length, "machine") + "; a machine is in one department at a time" : ""
            Column {
                width: parent.width
                spacing: 8
                Txt { visible: !page.cur; text: "Pick a department on the left, or make one below."; color: Theme.text3 }
                Txt { visible: !!page.cur; text: page.cur ? "IN " + page.cur.name.toUpperCase() : ""; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Txt { visible: !!page.cur && page.inD(page.cur.id).length === 0; text: "No machines yet. Put some in from the list below."; color: Theme.text3 }
                Flow {
                    visible: !!page.cur
                    width: parent.width
                    spacing: 5
                    Repeater { model: page.cur ? page.inD(page.cur.id) : []; delegate: tile }
                }
                Txt { visible: !!page.cur; topPadding: 6; text: "ELSEWHERE · click one to move it in"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Field { visible: !!page.cur; width: Math.min(300, parent.width); iconName: "search"; placeholderText: "Find a machine or a person"; text: page.q; onTextEdited: page.q = text }
                Repeater {
                    model: page.groups
                    delegate: Column {
                        required property var modelData
                        width: parent.width
                        spacing: 5
                        Txt { text: modelData.name; color: Theme.text2; font.pixelSize: Theme.fSmall }
                        Flow { width: parent.width; spacing: 5; Repeater { model: modelData.ms; delegate: tile } }
                    }
                }
                Txt { visible: !!page.cur && page.elsewhere.length === 0; color: Theme.text3
                      text: page.q ? "Nothing matches." : page.cur ? "Every machine is in " + page.cur.name + "." : "" }
                Link { visible: page.elsewhere.length > page.cap; text: page.more ? "Show fewer" : "and " + Theme.fmt(page.elsewhere.length - page.cap) + " more"; onClicked: page.more = !page.more }
            }
        }
    }

    // --- making one ---------------------------------------------------------------------------------------
    Panel {
        width: parent.width
        title: "Make a department"
        sub: "name it, then put machines in it on the right"
        Row {
            width: parent.width
            spacing: 10
            Field { objectName: "deptName"; width: Math.min(420, parent.width - mk.width - 10); placeholderText: "For example Procurement"; text: page.nm; onTextEdited: page.nm = text; onAccepted: page.make() }
            Btn { id: mk; objectName: "deptMake"; kind: "primary"; text: "Make it"; enabled: page.nm.trim() !== ""; onClicked: page.make() }
        }
    }

    // a machine as the Overview's tile, with its whole name, coloured by how it is; who is at it on hover
    Component {
        id: tile
        Item {
            required property var modelData
            readonly property bool inside: page.cur !== null && modelData.dept === page.cur.id
            // the machine's whole name (the concept, 1 Nov 2026): with every department in one console, "01" alone is several machines
            readonly property string name: modelData.host.replace(/^WS-/, "")
            width: Math.max(46, nameW.implicitWidth + 18); height: 34
            Txt { id: nameW; visible: false; text: parent.name; mono: true; font.pixelSize: 12 }
            HealthMark {
                anchors.fill: parent
                size: 34
                bordered: false
                k: Fleet.mark(modelData.status)
                label: parent.name
                scale: hit.containsMouse && !parent.inside ? 1.06 : 1
                Behavior on scale { NumberAnimation { duration: Theme.durFast } }
            }
            MouseArea {
                id: hit
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: parent.inside ? Qt.ArrowCursor : Qt.PointingHandCursor
                onClicked: if (!parent.inside) page.moveIn(parent.modelData)
            }
            Tip { text: modelData.host + (modelData.user ? ", " + modelData.user : ", nobody signed in") + (parent.inside ? "" : " · click to move it in") }
        }
    }
}
