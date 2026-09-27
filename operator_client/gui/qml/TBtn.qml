import QtQuick
import QtQuick.Controls
import "."

// A tonal button: a soft fill of one core colour. The only "filled" button in the product.
AbstractButton {
    id: root
    property string tone: "accent"
    property string iconName: ""
    property bool small: false

    implicitWidth: row.implicitWidth + (small ? 22 : 28)
    implicitHeight: small ? 28 : 34
    opacity: enabled ? 1 : 0.45
    hoverEnabled: true

    background: Rectangle {
        radius: Theme.radiusSm
        color: Theme.toneSoft(root.tone)
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: Theme.tone(root.tone)
            opacity: root.pressed ? 0.16 : root.hovered ? 0.08 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.durFast } }
        }
    }
    // the control stretches contentItem to fill it; the row is centred inside a plain Item so the label never
    // drifts left when the button is wider than its words
    contentItem: Item {
        Row {
            id: row
            anchors.centerIn: parent
            spacing: 7
            Icon {
                name: root.iconName
                visible: root.iconName !== ""
                color: Theme.tone(root.tone)
                size: 15
                anchors.verticalCenter: parent.verticalCenter
            }
            Txt {
                text: root.text
                color: Theme.tone(root.tone)
                font.pixelSize: root.small ? Theme.fMeta : Theme.fBody
                font.weight: Font.DemiBold
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
