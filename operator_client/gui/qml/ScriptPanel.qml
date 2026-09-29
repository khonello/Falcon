import QtQuick
import QtQuick.Controls.Basic
import "."

// A CUSTOM ACTION'S SCRIPT, AND WHAT IS WRONG WITH IT. The same panel whether it is being written or
// being read, because they are the same thing seen twice -- and the check under it is the one the
// Engine runs and the worker runs again on arrival, so a refusal here reads as a review.
Item {
    id: root
    property string language: "python"
    property bool readOnly: false
    property alias text: body.text
    property var problems: []
    property bool checked: false          // has it been read yet
    signal check()

    implicitHeight: box.height + (note.visible ? note.height + Theme.s2 : 0)

    Rectangle {
        id: box
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: Math.min(260, Math.max(96, body.contentHeight + 2 * Theme.s2 + rule.height))
        radius: Theme.radius
        color: root.readOnly ? Theme.fill : Theme.surface
        border.width: 1
        border.color: root.problems.length > 0 ? Theme.danger
                      : body.activeFocus ? Theme.primary : Theme.split
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }

        // the one bit of chrome: which language, so nobody guesses from the syntax
        Item {
            id: rule
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 26
            Txt {
                anchors.left: parent.left
                anchors.leftMargin: Theme.s2
                anchors.verticalCenter: parent.verticalCenter
                text: root.language === "powershell" ? "PowerShell" : "Python"
                tone: "quiet"
                font.pixelSize: 11
            }
            Btn {
                objectName: "checkScript"
                kind: "link"
                small: true
                text: "Check"
                visible: !root.readOnly
                anchors.right: parent.right
                anchors.rightMargin: Theme.s1
                anchors.verticalCenter: parent.verticalCenter
                onClicked: root.check()
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.split }
        }

        Flickable {
            anchors.top: rule.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: Theme.s2
            contentWidth: body.contentWidth
            contentHeight: body.contentHeight
            clip: true

            TextEdit {
                id: body
                objectName: "scriptText"
                width: Math.max(parent.width, contentWidth)
                readOnly: root.readOnly
                selectByMouse: true
                wrapMode: TextEdit.NoWrap
                font.family: Theme.mono
                font.pixelSize: Theme.fSmall
                color: Theme.ink
                onTextChanged: root.checked = false
            }
        }
    }

    Column {
        id: note
        anchors.top: box.bottom
        anchors.topMargin: Theme.s2
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 2
        visible: root.problems.length > 0 || (root.checked && !root.readOnly)

        Repeater {
            model: root.problems
            delegate: Txt {
                required property var modelData
                width: note.width
                text: String(modelData)
                tone: "danger"
                font.pixelSize: Theme.fSmall
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
            }
        }
        Txt {
            visible: root.checked && root.problems.length === 0
            text: "Reads clean: the standard library and what Windows already has."
            tone: "mid"
            font.pixelSize: Theme.fSmall
        }
    }
}
