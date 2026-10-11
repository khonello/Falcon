import QtQuick
import QtQuick.Controls.Basic
import "."

// SEARCH, WHICH IS A JUMP (Ctrl K): pages, machines, and at the Super User's level departments. At most
// five per group; the rest are counted, and a sharper query finds them. Arrows move, Enter opens.
Popup {
    id: root
    objectName: "palette"
    parent: Overlay.overlay
    x: (parent.width - width) / 2
    y: parent.height * 0.12
    width: Math.min(640, parent.width - 32)
    height: input.height + Math.min(360, list.contentHeight + 12) + 2
    padding: 0
    modal: true
    dim: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    Overlay.modal: Rectangle { color: Theme.scrimLight }

    property var machines: []
    property var depts: []
    property int at: 0

    onOpened: {
        input.text = ""; at = 0; input.forceActiveFocus()
        falcon.call("hierarchy.tree", {}, function (ok, r) {
            if (!ok) return
            var ms = [], ds = r.departments || []
            for (var i = 0; i < ds.length; i++)
                for (var k = 0; k < (ds[i].workers || []).length; k++) {
                    var w = ds[i].workers[k]
                    ms.push({ host: w.hostname, sub: (w.name || "no user") + " · " + ds[i].name + (w.online === false ? " · offline" : "") })
                }
            root.machines = ms
            root.depts = ds.map(function (d) { return { id: d.department_id, name: d.name, admins: (d.admins || []).map(function (a) { return a.name }) } })
        })
    }

    readonly property var items: {
        var q = input.text.toLowerCase(), out = [], extra = {}, seen = {}
        var all = []
        for (var g = 0; g < Nav.menu.length; g++)
            for (var i = 0; i < Nav.menu[g][1].length; i++) {
                var m = Nav.menu[g][1][i]
                all.push({ g: "Go to", l: m[1], icon: m[2], page: m[0], sub: null })
            }
        for (var k = 0; k < machines.length; k++)
            all.push({ g: "Machines", l: machines[k].host, s: machines[k].sub, icon: "desktop", mono: true, page: "machines", sub: machines[k].host })
        if (Nav.boss)
            for (var d = 0; d < depts.length; d++)
                all.push({ g: "Departments", l: depts[d].name, s: depts[d].admins.length ? Theme.listNames(depts[d].admins) : "no Admin",
                           icon: "apartment", page: "departments", sub: depts[d].id })
        for (var j = 0; j < all.length; j++) {
            var x = all[j]
            if ((x.l + " " + (x.s || "") + " " + x.g).toLowerCase().indexOf(q) < 0) continue
            seen[x.g] = (seen[x.g] || 0) + 1
            if (seen[x.g] <= 5 || x.g === "Go to") out.push(x); else extra[x.g] = (extra[x.g] || 0) + 1
        }
        for (var gg in extra)
            out.push({ g: gg, l: "+" + extra[gg] + " more " + gg.toLowerCase(), s: "type more to narrow, or open the full list",
                       icon: "ellipsis", page: gg === "Machines" ? "machines" : "departments", sub: null })
        return out
    }
    function pick(x) { if (!x) return; Nav.go(x.page, x.sub); close() }

    background: Rectangle {
        radius: Theme.radiusLg
        color: Theme.surface
        border.width: 1
        border.color: Theme.borderStrong
    }

    TextField {
        id: input
        width: parent.width
        height: 50
        leftPadding: 16
        font.family: Theme.sans
        font.pixelSize: Theme.fLead
        color: Theme.text
        placeholderText: "Jump to a page, machine or department"
        placeholderTextColor: Theme.text4
        background: Rectangle { color: "transparent"; Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border } }
        onTextChanged: root.at = 0
        Keys.onDownPressed: root.at = Math.min(root.items.length - 1, root.at + 1)
        Keys.onUpPressed: root.at = Math.max(0, root.at - 1)
        Keys.onReturnPressed: root.pick(root.items[root.at])
        Keys.onEnterPressed: root.pick(root.items[root.at])
    }
    ListView {
        id: list
        anchors.top: input.bottom
        anchors.topMargin: 6
        x: 6
        width: parent.width - 12
        height: Math.min(360, contentHeight)
        clip: true
        model: root.items
        delegate: Column {
            required property var modelData
            required property int index
            width: list.width
            Txt {
                visible: index === 0 || root.items[index - 1].g !== modelData.g
                text: modelData.g.toUpperCase()
                color: Theme.text4
                font.pixelSize: 11
                font.weight: Font.DemiBold
                font.letterSpacing: 0.6
                leftPadding: 10
                topPadding: 8
                bottomPadding: 2
                height: visible ? implicitHeight : 0
            }
            Rectangle {
                width: parent.width
                height: 32
                radius: 5
                color: index === root.at ? Theme.accentSoft : "transparent"
                Row {
                    x: 10
                    spacing: 10
                    anchors.verticalCenter: parent.verticalCenter
                    Icon { name: modelData.icon; size: 14; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: modelData.l; mono: !!modelData.mono; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: modelData.s || ""; color: Theme.text3; font.pixelSize: Theme.fSmall; anchors.verticalCenter: parent.verticalCenter; width: 320 }
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: root.at = index
                    onClicked: root.pick(modelData)
                }
            }
        }
        Txt { visible: root.items.length === 0; text: "No matches."; color: Theme.text3; x: 12; y: 8 }
    }
}
