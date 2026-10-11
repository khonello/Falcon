import QtQuick
import "."

// ACROSS THE TOP OF EVERY PAGE OF AN ADMIN'S CONSOLE while a task given to them is unseen:
// New task from the Super User · what · due · Open · I've seen it. It goes only when they mark it
// seen, and the time is kept. A Super User inside the console sees it, but only the Admin can press it.
Rectangle {
    id: root
    property var tasks: []
    signal marked()
    readonly property var t: tasks.length ? tasks[0] : null

    visible: !Nav.boss && t !== null
    height: visible ? 40 : 0
    color: Theme.accentSoft
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.alpha(Theme.accent, 0.35) }

    Row {
        x: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Icon {
            name: "notification"
            size: 15
            color: Theme.accent
            anchors.verticalCenter: parent.verticalCenter
            SequentialAnimation on scale {
                running: root.visible
                loops: 3
                NumberAnimation { to: 1.25; duration: 800 }
                NumberAnimation { to: 1; duration: 800 }
            }
        }
        Txt {
            text: root.tasks.length > 1 ? root.tasks.length + " new tasks from the Super User" : "New task from the Super User"
            font.weight: Font.DemiBold
            elide: Text.ElideNone
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: root.t ? root.t.title : ""
            width: Math.min(implicitWidth, root.width - 720)
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            mono: true
            elide: Text.ElideNone
            color: root.t && Time.past(root.t.deadline_at) ? Theme.crit : Theme.text
            text: root.t ? "due " + Time.atDay(root.t.deadline_at).replace("Today", "today") : ""
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            visible: root.tasks.length > 1
            text: "+" + (root.tasks.length - 1) + " more"
            color: Theme.text3
            elide: Text.ElideNone
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8
        Btn { small: true; text: "Open"; onClicked: Nav.go("tasks", root.t ? "dt:" + root.t.id : null) }
        Btn {
            objectName: "seenTask"
            visible: !Nav.inside
            small: true
            kind: "primary"
            text: "I've seen it"
            onClicked: falcon.call("task.dept_mark", { task_id: root.t.id, state: "seen" }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not marked"); return }
                Msg.ok("Marked seen at " + Time.hhmm(Date.now()) + " · the Super User sees when")
                root.marked()
            })
        }
    }
}
