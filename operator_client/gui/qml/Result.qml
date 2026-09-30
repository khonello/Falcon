import QtQuick
import "."

// THE WHOLE PAGE CANNOT ANSWER: not connected, not allowed, nothing found. Different from Empty --
// Empty means there is nothing yet and that is fine; this means something is wrong and names the way
// forward, because a dead end with no next step is the worst thing a console can show.
Item {
    id: root
    property string kind: "danger"        // danger | warn | note
    property string title: ""
    property string hint: ""
    default property alias acts: row.data

    implicitHeight: body.implicitHeight

    Column {
        id: body
        anchors.centerIn: parent
        width: Math.min(root.width, 420)
        spacing: Theme.s3

        Icon {
            anchors.horizontalCenter: parent.horizontalCenter
            name: root.kind === "note" ? "info" : "warn"
            size: 34
            color: root.kind === "note" ? Theme.quiet : Theme.tone(root.kind)
        }
        Txt {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.title
            strong: true
            font.pixelSize: Theme.fLead
        }
        Txt {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.hint
            tone: "mid"
            font.pixelSize: Theme.fSmall
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
        }
        Row {
            id: row
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.s2
        }
    }
}
