import QtQuick
import QtQuick.Controls.Basic
import "."

// A DATE AND A TIME, as "Fri 16 Oct, 17:00". A click opens the month with the time beside it; Clear
// empties it. `value` is an ISO string or null; `changed(iso)` fires on every pick.
Item {
    id: root
    property var value: null
    property string placeholder: "Pick a date"
    property bool small: false
    signal changed(var iso)

    implicitWidth: 200
    implicitHeight: small ? Theme.controlSm : Theme.control
    readonly property var d: Time.d(value)

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSm
        color: Theme.surface
        border.width: 1
        border.color: pop.opened || area.containsMouse ? Theme.accent : Theme.borderStrong
        Txt {
            x: 10
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 36
            text: root.d ? Time.date(root.d) : root.placeholder
            color: root.d ? Theme.text : Theme.text4
            font.pixelSize: root.small ? Theme.fSmall : Theme.fBody
        }
        Icon { name: "calendar"; size: 13; color: Theme.text3; anchors.right: parent.right; anchors.rightMargin: 9; anchors.verticalCenter: parent.verticalCenter }
        MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: pop.opened ? pop.close() : pop.open() }
    }

    property date month: d ? d : new Date(Time.now)
    function pick(day, h, m) {
        var x = new Date(day.getFullYear(), day.getMonth(), day.getDate(), h, m, 0, 0)
        root.value = x.toISOString()
        root.changed(root.value)
    }

    Popup {
        id: pop
        y: root.height + 4
        padding: 10
        width: 7 * 34 + 20 + 110
        height: 280
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {
            radius: Theme.radius; color: Theme.surface; border.width: 1; border.color: Theme.borderStrong
            MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons }
        }
        Row {
            spacing: 10
            Column {
                spacing: 6
                Row {
                    width: 7 * 34
                    Btn { kind: "text"; small: true; iconName: "chevl"; onClicked: root.month = new Date(root.month.getFullYear(), root.month.getMonth() - 1, 1) }
                    Txt { width: 7 * 34 - 60; horizontalAlignment: Text.AlignHCenter; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter
                          text: Time.months[root.month.getMonth()] + " " + root.month.getFullYear() }
                    Btn { kind: "text"; small: true; iconName: "chevr"; onClicked: root.month = new Date(root.month.getFullYear(), root.month.getMonth() + 1, 1) }
                }
                MonthGrid {
                    month: root.month
                    from: root.d
                    to: root.d
                    onPicked: function (day) { root.pick(day, root.d ? root.d.getHours() : 17, root.d ? root.d.getMinutes() : 0) }
                }
            }
            Column {
                spacing: 6
                width: 100
                Txt { text: "Time"; color: Theme.text3; font.pixelSize: 12 }
                Select {
                    width: 100
                    small: true
                    options: { var o = []; for (var i = 0; i < 48; i++) { var v = Time.pad(Math.floor(i / 2)) + ":" + (i % 2 ? "30" : "00"); o.push({ value: v, label: v }) } return o }
                    value: root.d ? Time.pad(root.d.getHours()) + ":" + (root.d.getMinutes() >= 30 ? "30" : "00") : "17:00"
                    onPicked: function (v) { var day = root.d || new Date(Time.now); root.pick(day, +v.slice(0, 2), +v.slice(3)) }
                }
                Item { width: 1; height: 120 }
                Btn { small: true; text: "Clear"; onClicked: { root.value = null; root.changed(null); pop.close() } }
                Btn { small: true; kind: "primary"; text: "OK"; onClicked: pop.close() }
            }
        }
    }
}
