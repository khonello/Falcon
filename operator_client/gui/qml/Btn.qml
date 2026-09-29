import QtQuick
import QtQuick.Controls.Basic
import "."

// A button names the act in AT MOST TWO WORDS (docs/UI.md rule 12); what it costs is said beside it.
//   kind: primary | default | text | link
//   danger: true   -- destructive, and then primary means a filled red
Button {
    id: root
    property string kind: "default"
    property bool danger: false
    property bool small: false
    property string iconName: ""
    property bool loading: false

    readonly property color accent: danger ? Theme.dangerStrong : Theme.primary
    readonly property bool filled: kind === "primary"
    readonly property bool bare: kind === "text" || kind === "link"

    implicitHeight: small ? Theme.controlSm : Theme.control
    implicitWidth: row.implicitWidth + (bare ? 2 * Theme.s2 : 2 * (small ? Theme.s3 : Theme.s4))
    enabled: !loading
    hoverEnabled: true

    background: Rectangle {
        radius: Theme.radius
        color: root.filled ? (root.pressed ? Qt.darker(root.accent, 1.15)
                              : root.hovered ? Qt.lighter(root.accent, 1.12) : root.accent)
               : root.bare ? (root.hovered ? Theme.hover : "transparent")
               : (root.pressed ? Theme.fillStrong : root.hovered ? Theme.fill : Theme.surface)
        border.width: root.filled || root.bare ? 0 : 1
        border.color: root.hovered ? root.accent : Theme.border
        opacity: root.enabled ? 1 : 0.45
        Behavior on color { ColorAnimation { duration: Theme.durFast } }
    }

    contentItem: Item {
        implicitWidth: row.implicitWidth
        implicitHeight: row.implicitHeight
        Row {
            id: row
            anchors.centerIn: parent
            spacing: Theme.s2 - 2
            Icon {
                visible: root.iconName !== "" || root.loading
                name: root.loading ? "history" : root.iconName
                size: root.small ? 13 : 15
                color: root.filled ? Theme.onDark
                       : root.kind === "link" ? root.accent
                       : root.danger ? Theme.danger : Theme.ink
                anchors.verticalCenter: parent.verticalCenter
                RotationAnimator on rotation {
                    running: root.loading; from: 0; to: 360; duration: 1100; loops: Animation.Infinite
                }
            }
            Txt {
                text: root.text
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: root.small ? Theme.fSmall : Theme.fBody
                font.weight: root.filled ? Font.DemiBold : Font.Normal
                color: root.filled ? Theme.onDark
                       : root.kind === "link" ? root.accent
                       : root.danger ? Theme.danger : Theme.ink
            }
        }
    }
}
