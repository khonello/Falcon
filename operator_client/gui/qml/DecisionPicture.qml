import QtQuick
import "."

// EACH DECISION'S EVIDENCE AS A PICTURE, small on its card and large beside the choices. The kind owns
// the picture: the gate (one bar for every machine, the ones holding it named), an empty seat (the
// department with nobody between it and you), a department task (each Admin told and how far they got),
// reports (how many, and how old the oldest is).
Item {
    id: root
    property var d: null
    property bool big: false
    implicitHeight: big ? col.height : 52

    readonly property var behind: Fleet.machines.filter(function (m) { return m.behind })
    readonly property int on: Fleet.machines.length - behind.length
    readonly property var dstate: ({ told: ["Not seen yet", Theme.text4], seen: ["Seen", Theme.ser1], ongoing: ["Ongoing", Theme.med], done: ["Done", Theme.ok] })

    Column {
        id: col
        width: parent.width
        spacing: 8
        anchors.verticalCenter: root.big ? undefined : parent.verticalCenter

        // the gate
        Column {
            visible: !!root.d && root.d.kind === "gate"
            width: parent.width
            spacing: root.big ? 10 : 4
            Row { visible: root.big; spacing: 8
                  Txt { text: Theme.fmt(root.on); font.pixelSize: 22; font.weight: Font.DemiBold; elide: Text.ElideNone }
                  Txt { text: "of " + Theme.fmt(Fleet.machines.length) + " machines on " + Fleet.version; color: Theme.text3; elide: Text.ElideNone; anchors.baseline: parent.children[0].baseline }
                  Txt { text: root.behind.length + " holding the gate"; color: Theme.med; elide: Text.ElideNone; anchors.baseline: parent.children[0].baseline } }
            Row {
                width: parent.width; height: root.big ? 14 : 10
                Rectangle { width: parent.width * root.on / Math.max(1, Fleet.machines.length); height: parent.height; color: Theme.alpha(Theme.ser2, 0.55) }
                Rectangle { width: parent.width - parent.children[0].width; height: parent.height; color: Theme.alpha(Theme.med, 0.7) }
            }
            Txt { visible: !root.big; text: root.behind.length + " holding it"; mono: true; color: Theme.text3; font.pixelSize: 10 }
            Flow {
                visible: root.big
                width: parent.width
                spacing: 6
                Repeater { model: root.behind.slice(0, 10)
                           Rectangle { required property var modelData; width: ht.implicitWidth + 16; height: 28; radius: 4; color: "transparent"; border.width: 1.5; border.color: Theme.med
                                       Txt { id: ht; anchors.centerIn: parent; text: modelData.host + "  " + modelData.ver; mono: true; color: Theme.med; font.pixelSize: 11; elide: Text.ElideNone } } }
                More { n: root.behind.length - 10; what: "holding it" }
            }
        }

        // an empty seat
        Item {
            id: seat
            visible: !!root.d && root.d.kind === "seat"
            width: parent.width
            height: root.big ? 150 : 30
            readonly property var dd: root.d && root.d.kind === "seat" ? Fleet.dept(root.d.dept) : null
            Row {
                visible: !root.big
                spacing: 8
                anchors.verticalCenter: parent.verticalCenter
                Rectangle { width: 26; height: 26; radius: 13; color: "transparent"; border.width: 1.5; border.color: Theme.crit
                            Txt { anchors.centerIn: parent; text: "?"; color: Theme.crit; font.weight: Font.DemiBold; elide: Text.ElideNone } }
                Icon { name: "arrowr"; size: 16; color: Theme.text4; anchors.verticalCenter: parent.verticalCenter }
                Rectangle { width: 26; height: 26; radius: 13; color: "transparent"; border.width: 1.5; border.color: Theme.borderStrong
                            Txt { anchors.centerIn: parent; text: "You"; color: Theme.text3; font.pixelSize: 9; font.weight: Font.DemiBold; elide: Text.ElideNone } }
            }
            Item {
                visible: root.big
                anchors.fill: parent
                Rectangle { x: 20; y: 6; width: 40; height: 40; radius: 20; color: Theme.accentSoft; border.width: 1.5; border.color: Theme.accent
                            Txt { anchors.centerIn: parent; text: "You"; color: Theme.accent; font.weight: Font.Bold; elide: Text.ElideNone } }
                Rectangle { x: 150; y: 50; width: 130; height: 34; radius: 6; color: Theme.surface2; border.width: 1; border.color: Theme.borderStrong
                            Txt { anchors.centerIn: parent; width: parent.width - 12; horizontalAlignment: Text.AlignHCenter; text: seat.dd ? seat.dd.name : ""; font.weight: Font.DemiBold } }
                Rectangle { x: 197; y: 100; width: 36; height: 36; radius: 18; color: Theme.alpha(Theme.crit, 0.08); border.width: 1.5; border.color: Theme.crit
                            Txt { anchors.centerIn: parent; text: "?"; color: Theme.crit; font.pixelSize: 15; font.weight: Font.DemiBold; elide: Text.ElideNone } }
                Txt { x: 180; y: 138; text: "No Admin"; color: Theme.crit; font.pixelSize: 11; font.weight: Font.DemiBold }
                Txt { x: 300; y: 108; width: parent.width - 300; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                      text: seat.dd ? Theme.many(seat.dd.machines.length, "machine") + "' reports skip the empty seat and come straight to you" : "" }
                Canvas {
                    anchors.fill: parent
                    onPaint: { var c = getContext("2d"); c.reset(); c.strokeStyle = Theme.crit; c.lineWidth = 2
                               c.beginPath(); c.moveTo(150, 72); c.bezierCurveTo(100, 90, 40, 80, 40, 50); c.stroke()
                               c.fillStyle = Theme.crit; c.beginPath(); c.moveTo(34, 54); c.lineTo(40, 46); c.lineTo(46, 54); c.closePath(); c.fill()
                               c.setLineDash([4, 3]); c.beginPath(); c.moveTo(215, 84); c.lineTo(215, 100); c.stroke() }
                }
            }
        }

        // a department's task: each Admin told, and how far they got
        Column {
            visible: !!root.d && root.d.kind === "task"
            width: parent.width
            spacing: 6
            Row {
                visible: !root.big
                spacing: 4
                Repeater { model: root.d && root.d.task ? (root.d.task.admins || []).slice(0, 4) : []
                           Rectangle { required property var modelData; width: 24; height: 24; radius: 12; color: Theme.surface3; border.width: 2; border.color: root.dstate[modelData.state][1]
                                       Txt { anchors.centerIn: parent; text: Theme.initials(modelData.name); font.pixelSize: 9; font.weight: Font.DemiBold; elide: Text.ElideNone } } }
                Txt { text: root.d && root.d.task ? Time.left(root.d.task.deadline_at) : ""; mono: true; color: Theme.text3; font.pixelSize: 10; leftPadding: 6; anchors.verticalCenter: parent.verticalCenter }
            }
            Repeater {
                model: root.big && root.d && root.d.task ? (root.d.task.admins || []) : []
                Item { required property var modelData; width: col.width; height: 36
                       Rectangle { width: 26; height: 26; radius: 13; color: Theme.surface3; border.width: 2; border.color: root.dstate[modelData.state][1]; anchors.verticalCenter: parent.verticalCenter
                                   Txt { anchors.centerIn: parent; text: Theme.initials(modelData.name); font.pixelSize: 10; font.weight: Font.DemiBold; elide: Text.ElideNone } }
                       Txt { x: 36; anchors.verticalCenter: parent.verticalCenter; text: modelData.name; width: parent.width - 200 }
                       Txt { anchors.right: tm.left; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: root.dstate[modelData.state][0]; color: root.dstate[modelData.state][1] }
                       Txt { id: tm; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: modelData.state_at ? Time.hhmm(modelData.state_at) : "—"; mono: true; color: Theme.text3 } }
            }
            Txt { visible: root.big && !!root.d && !!root.d.task; color: Theme.text3; font.pixelSize: 12
                  text: root.d && root.d.task ? "Given " + Time.atDay(root.d.task.created_at) + " · due " + Time.atDay(root.d.task.deadline_at) + " · " + Time.left(root.d.task.deadline_at) : "" }
        }

        // reports
        Item {
            visible: !!root.d && root.d.kind === "reports" && !root.big
            width: 60; height: 26
            Repeater { model: 4
                       Rectangle { required property int index; x: index * 6; y: index * 3; width: 34; height: 14; radius: 2; color: Theme.surface; border.width: 1; border.color: Theme.borderStrong } }
        }
    }
}
