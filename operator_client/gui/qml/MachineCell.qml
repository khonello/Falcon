import QtQuick
import "."

// A machine inside a table row: its state as a dot, its name, and the reason in words. The reason
// takes the tone only when somebody has to do something about it.
Row {
    id: root
    property string host: ""
    property string line: ""
    property string state: "ok"              // ok | free | entered | warn | danger
    readonly property bool needs: state === "warn" || state === "danger"
    spacing: Theme.s2

    Dot {
        tone: root.state === "danger" ? "danger" : root.state === "warn" ? "warn"
              : root.state === "entered" ? "ink" : root.state === "free" ? "quiet" : "mid"
        hollow: root.state === "free"
        anchors.verticalCenter: parent.verticalCenter
    }
    Txt {
        text: root.host
        mono: true
        strong: true
        font.pixelSize: Theme.fSmall
        anchors.verticalCenter: parent.verticalCenter
    }
    Txt {
        text: root.line
        tone: root.needs ? (root.state === "danger" ? "danger" : "warn") : "mid"
        font.pixelSize: Theme.fSmall
        anchors.verticalCenter: parent.verticalCenter
    }
}
