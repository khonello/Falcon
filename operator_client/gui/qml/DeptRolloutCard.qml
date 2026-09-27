import QtQuick
import "."

// ONE DEPARTMENT'S ROLLOUT, ALWAYS ONE LINE (design/PATTERNS.md 3a; boards RO05, OV02).
//
// Identity stamp, name, a thin progress line, "13 of 14", and ONE machine mark holding the count of machines behind --
// never one mark per machine -- with two short lines of words. Fixed width, so the line never grows whether one or
// forty are behind. A department with nothing behind shows a quiet screen and "all current". Machines are only named
// when the department is opened (double click).
//
//   dept    { department_id, department_name, pcs, current, pending, escalated }   (updates.rollout_health)
//   behind  the department's rows of pcs_behind: { hostname, failures, escalated }
Rectangle {
    id: root

    property var dept: ({})
    property var behind: []
    property color stamp: Theme.accent
    property bool compact: false
    property var modelData: null            // when used as a pager delegate
    property int index: -1
    signal opened()

    readonly property int total: dept ? (dept.pcs || 0) : 0
    readonly property int onCurrent: Math.max(0, total - behind.length)
    readonly property int pastLimit: behind.filter(function (b) { return b.escalated }).length
    readonly property int retrying: behind.length - pastLimit
    readonly property int worst: behind.reduce(function (m, b) { return Math.max(m, b.failures || 0) }, 0)
    readonly property string tone: pastLimit > 0 ? "danger" : behind.length > 0 ? "warn" : ""
    readonly property string head: behind.length === 0 ? "all current" : behind.length + " behind"
    // short on purpose, so the mark sits close to the chevron: past the limit is the story when there is one
    readonly property string sub: behind.length === 0 ? ""
        : pastLimit > 0 ? pastLimit + " past the limit" + (retrying > 0 ? " · " + retrying + " retrying" : "")
        : retrying + " retrying" + (worst > 0 ? " · worst " + worst + "×" : "")

    implicitHeight: 50
    radius: 14
    color: area.containsMouse ? Qt.lighter(Theme.pane, 1.12) : Theme.pane

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Rectangle { width: 9; height: 9; radius: 3; color: root.stamp; anchors.verticalCenter: parent.verticalCenter }
        Txt {
            width: root.compact ? 92 : 130; elide: Text.ElideRight
            text: root.dept ? (root.dept.department_name || "") : ""
            color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
        Rectangle {
            width: root.compact ? 110 : 200; height: 4; radius: 2; color: Qt.rgba(1, 1, 1, 0.10)
            anchors.verticalCenter: parent.verticalCenter
            Rectangle { width: parent.width * (root.total > 0 ? root.onCurrent / root.total : 0); height: 4; radius: 2; color: Theme.dim }
        }
        Txt { width: 58; text: root.onCurrent + " of " + root.total; color: Theme.dim; font.pixelSize: Theme.fBody
              anchors.verticalCenter: parent.verticalCenter }
    }

    Row {
        objectName: "rolloutMark"
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10
        MachineMark {
            size: 30
            label: root.behind.length > 0 ? String(root.behind.length) : ""
            status: root.tone === "danger" ? "danger" : root.tone === "warn" ? "warn" : "ok"
            anchors.verticalCenter: parent.verticalCenter
        }
        Column {
            width: root.compact ? 128 : 134
            anchors.verticalCenter: parent.verticalCenter
            Txt { text: root.head; color: root.tone === "" ? Theme.faint : Theme.tone(root.tone)
                  font.pixelSize: Theme.fMeta; font.weight: root.tone === "" ? Font.Normal : Font.DemiBold }
            Txt { visible: root.sub !== ""; text: root.sub; color: Theme.faint; font.pixelSize: Theme.fMeta - 1 }
        }
        Icon { name: "chev"; size: 13; color: Theme.faint; anchors.verticalCenter: parent.verticalCenter }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onDoubleClicked: root.opened()
    }
}
