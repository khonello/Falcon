import QtQuick
import QtQuick.Controls.Basic
import "."

// A button names the act in a few words; what it costs is said beside it.
//   kind: primary | default | text | link      danger: destructive      ghost: primary outline
//   circle: a round icon-only button (the composer's Send)
Button {
    id: root
    property string kind: "default"
    property bool danger: false
    property bool ghost: false
    property bool small: false
    property bool circle: false
    property string iconName: ""
    property bool loading: false
    property string tip: ""
    property bool iconRight: false

    readonly property color accent: danger ? Theme.crit : Theme.accent
    readonly property bool filled: kind === "primary" && !ghost
    readonly property bool bare: kind === "text" || kind === "link"
    readonly property color ink: filled ? Theme.inverse
                                : kind === "link" || ghost ? accent
                                : danger ? Theme.crit : Theme.text

    implicitHeight: small ? Theme.controlSm : Theme.control
    implicitWidth: circle ? implicitHeight
                   : row.implicitWidth + (bare ? (small ? 8 : 12) : 2 * (small ? 8 : 14))
    hoverEnabled: true
    focusPolicy: Qt.TabFocus
    opacity: enabled ? 1 : 0.45

    background: Rectangle {
        radius: root.circle ? height / 2 : Theme.radiusSm
        color: root.filled ? (root.pressed ? Qt.darker(root.accent, 1.15)
                              : root.hovered ? Qt.lighter(root.accent, 1.1) : root.accent)
               : root.bare ? (root.hovered && root.kind === "text" ? Theme.surface3 : "transparent")
               : root.ghost ? (root.hovered ? Theme.accentSoft : "transparent")
               : (root.pressed ? Theme.surface3 : Theme.surface)
        border.width: root.filled || root.bare ? 0 : 1
        border.color: root.ghost ? root.accent
                      : root.hovered && root.enabled ? root.accent
                      : root.danger ? Theme.alpha(Theme.crit, 0.6) : Theme.borderStrong
        Behavior on color { ColorAnimation { duration: Theme.durFast } }
    }

    contentItem: Item {
        implicitWidth: row.implicitWidth
        implicitHeight: row.implicitHeight
        Row {
            id: row
            anchors.centerIn: parent
            spacing: 6
            layoutDirection: root.iconRight ? Qt.RightToLeft : Qt.LeftToRight
            Icon {
                visible: root.iconName !== "" || root.loading
                name: root.loading ? "loading" : root.iconName
                size: root.small ? 13 : 14
                color: root.ink
                anchors.verticalCenter: parent.verticalCenter
                RotationAnimator on rotation {
                    running: root.loading; from: 0; to: 360; duration: 900; loops: Animation.Infinite
                }
            }
            Txt {
                visible: root.text !== "" && !root.circle
                text: root.text
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: root.small ? Theme.fSmall : Theme.fBody
                font.weight: root.filled ? Font.Medium : Font.Normal
                color: root.hovered && !root.filled && !root.danger && root.kind !== "link" && !root.ghost
                       && root.enabled ? root.accent : root.ink
                elide: Text.ElideNone
            }
        }
    }
    ToolTip.visible: tip !== "" && hovered
    ToolTip.text: tip
    ToolTip.delay: 400
}
