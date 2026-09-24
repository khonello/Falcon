import QtQuick
import "."

// One row per department: confirmed / behind / failing, all to a common scale so the rows can be
// compared by eye. Only the data ends of a bar are rounded; the joins inside it are square, with a
// 2 px gap of the surface showing through -- a bar is one object, not three pills.
Item {
    id: root

    property var rows: []                  // [{ label, parts: [{ tone, value }] }]
    property int labelWidth: 96
    property int valueWidth: 46
    property int barHeight: 18
    property int rowGap: 26

    function total(parts) {
        var t = 0
        for (var i = 0; i < parts.length; i++) t += parts[i].value
        return t
    }
    function firstDrawn(parts) {
        for (var i = 0; i < parts.length; i++) if (parts[i].value > 0) return i
        return -1
    }
    // a skeleton row carries a nominal value so the track has a length; it is structure, not data,
    // so it never shows a total
    function isSkeleton(parts) {
        for (var i = 0; i < parts.length; i++) if (parts[i].tone !== "quiet") return false
        return parts.length > 0
    }
    function lastDrawn(parts) {
        for (var i = parts.length - 1; i >= 0; i--) if (parts[i].value > 0) return i
        return -1
    }
    readonly property real maxTotal: {
        var m = 1
        for (var i = 0; i < rows.length; i++) m = Math.max(m, total(rows[i].parts))
        return m
    }
    readonly property real plot: Math.max(40, width - labelWidth - valueWidth)

    implicitHeight: rows.length * rowGap

    Column {
        width: parent.width
        spacing: root.rowGap - root.barHeight

        Repeater {
            model: root.rows
            delegate: Item {
                id: line
                required property var modelData
                width: root.width
                height: root.barHeight

                Txt {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: root.labelWidth - 8
                    text: line.modelData.label
                    color: Theme.dim
                    font.pixelSize: Theme.fBody
                    elide: Text.ElideRight
                }

                Row {
                    id: bar
                    anchors.left: parent.left
                    anchors.leftMargin: root.labelWidth
                    height: parent.height
                    spacing: 2

                    Repeater {
                        model: line.modelData.parts
                        delegate: Item {
                            required property var modelData
                            required property int index
                            readonly property color tint: Theme.tone(modelData.tone)

                            visible: modelData.value > 0
                            width: visible ? Math.max(4, (modelData.value / root.maxTotal) * root.plot) : 0
                            height: bar.height

                            Rectangle { anchors.fill: parent; radius: 4; color: parent.tint }
                            Rectangle {
                                width: Math.min(4, parent.width); height: parent.height
                                visible: index !== root.firstDrawn(line.modelData.parts)
                                color: parent.tint
                            }
                            Rectangle {
                                anchors.right: parent.right
                                width: Math.min(4, parent.width); height: parent.height
                                visible: index !== root.lastDrawn(line.modelData.parts)
                                color: parent.tint
                            }
                        }
                    }
                }

                Txt {
                    anchors.left: bar.right
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.isSkeleton(line.modelData.parts) ? ""
                                                                : String(root.total(line.modelData.parts))
                    color: Theme.faint
                    monospace: true
                    font.pixelSize: Theme.fMeta
                }
            }
        }
    }
}
