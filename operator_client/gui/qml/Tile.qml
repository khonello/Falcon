import QtQuick
import "."

// A MACHINE AS A TILE (the concept's ovh-m in ao-ovh): its name in 66 x 42, coloured by how it is: a red wash and red name
// when it needs a look, dashed and faint when it is offline. Who is at it is on hover.
Rectangle {
    id: root
    property var m: ({})
    property bool still: false                  // a click does nothing (the department it is already in)
    property string tip: ""
    property string mark: ""                    // Restricted says what a machine holds instead of how it is: home, hot, ok
    property bool picked: false
    property bool marksOnly: false              // on Restricted red means a copy, so a machine's health does not show
    signal clicked()
    readonly property bool isOff: !m.online && mark === ""
    readonly property bool isLag: !!m.online && !marksOnly && mark === "" && (m.status === "high" || m.status === "critical")
    readonly property color tone: mark === "home" ? Theme.accent : mark === "hot" ? Theme.crit : Theme.ok
    width: 66; height: 42; radius: 7
    color: mark !== "" ? Theme.mix(tone, Theme.surface3, mark === "ok" ? 0.26 : 0.28) : isOff ? "transparent" : isLag ? Theme.mix(Theme.crit, Theme.surface3, 0.16) : Theme.surface3
    border.width: isOff ? 0 : picked ? 1.5 : 1
    border.color: picked ? Theme.crit : isLag ? Theme.alpha(Theme.crit, 0.35) : ta.containsMouse && !still ? Theme.borderStrong : "transparent"
    Canvas {
        visible: root.isOff
        anchors.fill: parent
        onPaint: { var g = getContext("2d"); g.reset(); g.strokeStyle = Theme.text4; g.lineWidth = 1; g.setLineDash([3, 3])
                   var r = 7, x = 0.5, y = 0.5, w = width - 1, h = height - 1
                   g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); g.stroke() }
    }
    Txt { anchors.centerIn: parent; width: parent.width - 6; horizontalAlignment: Text.AlignHCenter; text: String(root.m.host || "").replace(/^WS-/, ""); font.pixelSize: 12; font.weight: root.mark !== "" ? Font.DemiBold : Font.Medium
          color: root.mark !== "" ? root.tone : root.isOff ? Theme.text4 : root.isLag ? Theme.crit : Theme.text2 }
    MouseArea { id: ta; anchors.fill: parent; hoverEnabled: true; cursorShape: root.still ? Qt.ArrowCursor : Qt.PointingHandCursor; onClicked: if (!root.still) root.clicked() }
    Tip { text: root.tip !== "" ? root.tip : (root.m.host || "") + (root.m.user ? ", " + root.m.user : ", nobody signed in") }
}
