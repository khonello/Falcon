import QtQuick
import QtQuick.Controls.Basic
import "."

// HOW CHECKING WORKS (the concept's HowChecking): a link at a task's targets, and under it a popover of six lines, 340 wide.
Item {
    id: root
    property string who: ""
    implicitWidth: link.implicitWidth
    implicitHeight: link.implicitHeight
    readonly property var lines: [
        ["aim", "When the task was given, it named what done looks like: a file to create or change, a folder, a program to use. You confirmed each one."],
        ["eye", "The system watches the machine for signs of progress, through its own file events and what its programs are doing. Nothing is installed for this task."],
        ["filesearch", "It reports what it found. It never marks a task done, and never closes one."],
        ["user", (who || "The person doing the task") + " sees the same signs of progress on their machine."],
        ["fieldtime", "A task under way with nothing seen for two days is marked quiet, so you can ask early rather than at the deadline."],
        ["checkcircle", "You close it: Complete, or Incomplete with a reason."]]
    Btn { id: link; objectName: "howChecking"; kind: "link"; iconName: "question"; text: "How checking works"; onClicked: pop.open() }
    Popup {
        id: pop
        x: root.width - width
        y: root.height + 6
        width: 340 + 24
        padding: 12
        background: Rectangle { color: Theme.elevated; radius: Theme.radiusLg; border.width: 1; border.color: Theme.border }
        contentItem: Column {
            spacing: 10
            Txt { text: "How checking works"; font.weight: Font.DemiBold; elide: Text.ElideNone }
            Repeater {
                model: root.lines
                Row {
                    required property var modelData
                    spacing: 10
                    Icon { y: 3; name: modelData[0]; size: 13; color: Theme.text3 }
                    Txt { width: 340 - 23; text: modelData[1]; color: Theme.text2; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                }
            }
        }
    }
}
