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

    readonly property var loose: all.filter(function (m) { return !depts.some(function (d) { return d.id === m.dept }) })
    situation: Theme.many(depts.length, "department") + " and " + Theme.many(all.length, "machine") + "; "
               + (loose.length ? Theme.fmt(loose.length) + " in no department yet" : "every machine is in one") + ". Every IT Admin reaches every department."
    situationAt: Time.now
    function deptColor(i) { return [Theme.ser1, Theme.ser2, Theme.ser3, Theme.ser4, Theme.ser5, Theme.ser6][i % 6] }

    Row {
        id: two
        width: parent.width
        spacing: 14
        readonly property real h: Math.max(left.implicitHeight, right.implicitHeight)

        // --- the departments ---------------------------------------------------------------------------
        Box {
            id: left
            width: (parent.width - 14) * 0.5
            height: two.h
            title: "Departments · " + Theme.fmt(page.depts.length)
            sub: "a label for grouping machines and the people at them; click one to see its machines on the right, expand it to rename it"
            Quiet { visible: page.depts.length === 0; text: "No departments yet. Make one below." }
            Column {
                width: parent.width
                spacing: 6
                Repeater {
                    model: page.depts
                    delegate: Card {
                        id: card
                        required property var modelData
                        required property int index
                        readonly property var ms: page.inD(modelData.id)
                        readonly property int ppl: ms.filter(function (m) { return !!m.user }).length
                        objectName: "deptCard-" + modelData.id
                        width: parent.width
                        midW: 200
                        actW: 150
                        dotColor: page.deptColor(index)
                        title: modelData.name
                        line: ms.length ? Theme.listNames(ms.map(function (m) { return m.host }), 4) : "no machines yet"
                        picked: page.cur !== null && page.cur.id === modelData.id
                        expandable: true
                        expanded: page.exp === modelData.id
                        onOpen: page.sel = modelData.id
                        onToggle: { page.sel = modelData.id; page.ren = modelData.name; page.exp = expanded ? null : modelData.id }
                        mid: Row {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 14
                            Txt { text: Theme.many(card.ms.length, "machine"); font.pixelSize: 12; color: Theme.text3; elide: Text.ElideNone }
                            Txt { text: card.ppl + (card.ppl === 1 ? " person" : " people"); font.pixelSize: 12; color: Theme.text3; elide: Text.ElideNone }
                        }
                        // opened: its name, to change (pd-open)
                        Column {
                            y: 4
                            width: parent.width
                            spacing: 10
                            Row {
                                spacing: 8
                                Txt { width: 64; anchors.verticalCenter: parent.verticalCenter; text: "Name"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                                Field { objectName: "deptRename"; small: true; width: Math.min(260, card.width - 58 - 14 - 72); text: page.ren; placeholderText: "Name"; onTextEdited: page.ren = text; onAccepted: page.rename(card.modelData) }
                            }
                            Item {
                                width: parent.width
                                height: rn.height + 2
                                Txt { width: parent.width - rn.width - 10; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 12
                                      text: "The new name shows everywhere the department does; its machines stay in it." }
                                Btn { id: rn; anchors.right: parent.right; small: true; text: "Rename"; enabled: page.ren.trim() !== "" && page.ren.trim() !== card.modelData.name; onClicked: page.rename(card.modelData) }
                            }
                        }
                    }
                }
            }
        }

        // --- the picked department's machines, and the rest to move in ----------------------------------
        Box {
            id: right
            width: (parent.width - 14) * 0.5
            height: two.h
            title: page.cur ? page.cur.name : "No department picked"
            Pulse { parent: right; key: page.cur ? page.cur.id : null }          // a click on the left pulses it at once (drawn from the list: no spinner)
            sub: page.cur ? Theme.many(page.inD(page.cur.id).length, "machine") + "; a machine is in one department at a time" : ""
            Quiet { visible: !page.cur; text: "Pick a department on the left, or make one below." }
            Item { visible: !!page.cur; width: parent.width; height: ih.height + 6; Txt { id: ih; y: 6; text: page.cur ? "In " + page.cur.name : ""; font.pixelSize: 12; font.weight: Font.DemiBold; color: Theme.text2 } }
            Quiet { visible: !!page.cur && page.inD(page.cur.id).length === 0; text: "No machines yet. Put some in from the list below." }
            Flow {
                visible: !!page.cur && page.inD(page.cur.id).length > 0
                width: parent.width
                spacing: 10
                Repeater { model: page.cur ? page.inD(page.cur.id) : []; delegate: Tile { required property var modelData; m: modelData; still: true } }
            }
            Item {
                visible: !!page.cur
                width: parent.width
                height: eh.height + 16
                Txt { id: eh; y: 16; text: "Elsewhere"; font.pixelSize: 12; font.weight: Font.DemiBold; color: Theme.text2; elide: Text.ElideNone }
                Txt { x: eh.implicitWidth + 8; y: 16; text: page.cur ? "click one to move it into " + page.cur.name : ""; font.pixelSize: 12; color: Theme.text3; elide: Text.ElideNone }
            }
            Field { visible: !!page.cur; small: true; width: Math.min(300, parent.width); iconName: "search"; placeholderText: "Find a machine or a person"; text: page.q; onTextEdited: page.q = text }
            Repeater {
                model: page.groups
                delegate: Column {
                    required property var modelData
                    width: parent.width
                    spacing: 6
                    Txt { topPadding: 10 + (font.pixelSize * 0.1); text: modelData.name; color: Theme.text3; font.pixelSize: 12 }
                    Flow { width: parent.width; spacing: 10
                           Repeater { model: modelData.ms; delegate: Tile { required property var modelData; m: modelData; onClicked: page.moveIn(modelData) } } }
                }
            }
            Quiet { visible: !!page.cur && page.elsewhere.length === 0; text: page.q ? "Nothing matches." : page.cur ? "Every machine is in " + page.cur.name + "." : "" }
            Txt { visible: page.elsewhere.length > page.cap; text: page.more ? "Show fewer" : "and " + Theme.fmt(page.elsewhere.length - page.cap) + " more"; color: Theme.text3; font.pixelSize: 13
                  MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.more = !page.more } }
            Row {
                visible: !!page.cur
                spacing: 18
                topPadding: 4
                Repeater {
                    model: [["fine", Theme.surface3, "transparent"], ["needs a look", Theme.mix(Theme.crit, Theme.surface3, 0.16), Theme.alpha(Theme.crit, 0.35)], ["offline", "transparent", Theme.text4]]
                    delegate: Row {
                        required property var modelData
                        spacing: 6
                        Rectangle { width: 14; height: 11; radius: 3; color: modelData[1]; border.width: 1; border.color: modelData[2]; anchors.verticalCenter: parent.verticalCenter }
                        Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    }
                }
            }
        }
    }

    // --- making one ---------------------------------------------------------------------------------------
    Box {
        width: parent.width
        accentFoot: true
        title: "Make a department"
        sub: "name it, then put machines in it on the right"
        Row {
            width: parent.width
            spacing: 8
            Field { objectName: "deptName"; width: Math.min(420, parent.width - mk.width - 8); placeholderText: "For example Procurement"; text: page.nm; onTextEdited: page.nm = text; onAccepted: page.make() }
            Btn { id: mk; objectName: "deptMake"; kind: "primary"; text: "Make it"; enabled: page.nm.trim() !== ""; onClicked: page.make() }
        }
    }
}
