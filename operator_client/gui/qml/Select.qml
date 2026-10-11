import QtQuick
import QtQuick.Controls.Basic
import "."

// NOTHING TYPED THAT CAN BE PICKED. `options` are {value, label, disabled?} (or plain strings), so the
// console shows the word and sends the id. `multiple` picks several (`values`), shown as tags;
// `search` filters the list as you type. A group heading is {group: "Control"}.
Item {
    id: root
    property var options: []
    property var value: null
    property var values: []
    property bool multiple: false
    property bool search: false
    property bool small: false
    property bool invalid: false
    property bool enabled: true
    property string placeholder: "Select"
    property int popupWidth: 0
    signal picked(var value)

    readonly property var items: options.map(function (o) { return typeof o === "object" ? o : { value: o, label: String(o) } })
    implicitWidth: 240
    implicitHeight: small ? Theme.controlSm : Theme.control
    opacity: enabled ? 1 : 0.5

    function labelFor(v) {
        for (var i = 0; i < items.length; i++) if (items[i].value === v) return items[i].label
        return ""
    }
    function has(v) { return values.indexOf(v) >= 0 }

    Rectangle {
        id: box
        anchors.fill: parent
        radius: Theme.radiusSm
        color: Theme.surface
        border.width: 1
        border.color: root.invalid ? Theme.crit : pop.opened || area.containsMouse ? Theme.accent : Theme.borderStrong
        clip: true

        Txt {
            visible: !root.multiple || root.values.length === 0
            anchors.left: parent.left
            anchors.leftMargin: 10
            anchors.right: chev.left
            anchors.rightMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            font.pixelSize: root.small ? Theme.fSmall : Theme.fBody
            text: root.multiple ? root.placeholder : (root.value === null || root.value === undefined ? root.placeholder : root.labelFor(root.value))
            color: root.multiple || root.value === null || root.value === undefined ? Theme.text4 : Theme.text
        }
        Row {
            visible: root.multiple && root.values.length > 0
            x: 4
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            width: parent.width - 30
            clip: true
            Repeater {
                model: root.values.slice(0, 3)
                Tag { required property var modelData; text: root.labelFor(modelData) }
            }
            Tag { visible: root.values.length > 3; text: "+" + (root.values.length - 3) }
        }
        Icon {
            id: chev
            name: "chevd"
            size: 12
            color: Theme.text3
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
        }
        MouseArea {
            id: area
            anchors.fill: parent
            enabled: root.enabled
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: { if (pop.opened) pop.close(); else { filter.text = ""; pop.open(); if (root.search) filter.forceActiveFocus() } }
        }
    }

    Popup {
        id: pop
        y: root.height + 4
        width: Math.max(root.width, root.popupWidth)
        padding: 4
        height: Math.min(list.contentHeight + (root.search ? 36 : 0) + 8, 280)
        background: Rectangle {
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.borderStrong
            // a popup that floats over the page takes every press in it that no option took
            MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }
        }
        SearchBox {
            id: filter
            visible: root.search
            width: parent.width
            height: visible ? 28 : 0
            placeholderText: "Type to find"
        }
        ListView {
            id: list
            anchors.top: filter.bottom
            anchors.topMargin: root.search ? 6 : 0
            anchors.bottom: parent.bottom
            width: parent.width
            clip: true
            model: root.items.filter(function (o) { return !root.search || o.group || String(o.label).toLowerCase().indexOf(filter.text.toLowerCase()) >= 0 })
            delegate: Rectangle {
                required property var modelData
                readonly property bool on: root.multiple ? root.has(modelData.value) : modelData.value === root.value
                width: list.width
                height: modelData.group ? 26 : 30
                radius: Theme.radiusSm
                color: modelData.group ? "transparent" : on ? Theme.accentSoft : oh.containsMouse && !modelData.disabled ? Theme.surface3 : "transparent"
                Txt {
                    anchors.left: parent.left
                    anchors.leftMargin: modelData.group ? 8 : 10
                    anchors.right: tick.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.group ? modelData.group : modelData.label
                    color: modelData.group ? Theme.text3 : modelData.disabled ? Theme.text4 : Theme.text
                    font.pixelSize: modelData.group ? 11 : Theme.fBody
                    font.weight: on ? Font.Medium : Font.Normal
                }
                Icon { id: tick; visible: root.multiple && on; name: "check"; size: 13; color: Theme.accent; anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter }
                MouseArea {
                    id: oh
                    anchors.fill: parent
                    enabled: !modelData.group && !modelData.disabled
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.multiple) {
                            var v = root.values.slice(), i = v.indexOf(modelData.value)
                            if (i >= 0) v.splice(i, 1); else v.push(modelData.value)
                            root.values = v
                            root.picked(v)
                        } else {
                            root.value = modelData.value
                            root.picked(modelData.value)
                            pop.close()
                        }
                    }
                }
            }
        }
    }
}
