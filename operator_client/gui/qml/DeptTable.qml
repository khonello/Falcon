import QtQuick
import "."

// The departments, one row each: who runs it, how many machines and how many online, open issues,
// how many run the current version, and how fast its reports are addressed. Ten rows a page.
Column {
    id: root
    property var rows: Fleet.depts
    readonly property var colW: [0, 0, 90, 90, 100, 170, 180]     // the first two share what is left
    readonly property real flexW: (width - 630) / 2
    property int page: 1
    readonly property int pages: Math.max(1, Math.ceil(rows.length / 10))

    function w(i) { return i < 2 ? flexW : colW[i] }

    Rectangle {
        width: parent.width
        height: 36
        color: Theme.surface2
        Row {
            anchors.fill: parent
            Repeater {
                model: ["Department", "Admins", "Machines", "Online", "Open issues", "On " + (Fleet.version || "current"), "Median time to address"]
                Txt {
                    required property var modelData
                    required property int index
                    width: root.w(index)
                    leftPadding: index === 0 ? 14 : 8
                    rightPadding: index >= 2 && index !== 5 ? 12 : 0
                    horizontalAlignment: index >= 2 && index !== 5 ? Text.AlignRight : Text.AlignLeft
                    text: modelData
                    color: Theme.text3; font.pixelSize: 12; font.weight: Font.Medium
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
    }
    Repeater {
        model: root.rows.slice((root.page - 1) * 10, root.page * 10)
        delegate: Rectangle {
            required property var modelData
            readonly property var ms: modelData.machines
            readonly property int online: ms.filter(function (m) { return m.online }).length
            readonly property int ok: ms.filter(function (m) { return !m.behind }).length
            readonly property int open: Fleet.issues.filter(function (i) { return i.dept === modelData.id }).length
            width: root.width
            height: 40
            color: "transparent"
            Row {
                anchors.fill: parent
                Row {
                    width: root.w(0); leftPadding: 14; spacing: 8
                    anchors.verticalCenter: parent.verticalCenter
                    Rectangle { width: 8; height: 8; radius: 2; color: [Theme.ser1, Theme.ser2, Theme.ser4, Theme.ser3, Theme.ser5, Theme.ser6][modelData.id % 6]; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: modelData.name; font.weight: Font.Medium; width: root.w(0) - 40 }
                }
                Txt {
                    width: root.w(1); leftPadding: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.admins.length ? modelData.admins.map(function (a) { return a.name }).join(", ") : "None assigned"
                    color: modelData.admins.length ? Theme.text : Theme.crit
                }
                Txt { width: root.w(2); rightPadding: 12; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter; text: String(ms.length) }
                Txt { width: root.w(3); rightPadding: 12; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter
                      text: online + " / " + ms.length; color: online < ms.length ? Theme.crit : Theme.text }
                Txt { width: root.w(4); rightPadding: 12; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter; text: String(open) }
                Row {
                    width: root.w(5); leftPadding: 8; spacing: 8
                    anchors.verticalCenter: parent.verticalCenter
                    Bar { width: 90; v: ok; max: Math.max(1, ms.length); c: ok === ms.length ? Theme.ok : Theme.med; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: ms.length ? Math.round(ok / ms.length * 100) + "%" : "—"; mono: true; elide: Text.ElideNone }
                }
                Txt { width: root.w(6); rightPadding: 12; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter; text: "—"; mono: true }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
        }
    }
    Item {
        visible: root.pages > 1
        width: parent.width; height: 40
        Pager { anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter; current: root.page; pages: root.pages; onGo: function (p) { root.page = p } }
    }
}
