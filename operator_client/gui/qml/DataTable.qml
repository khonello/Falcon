import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// A table over a JS array of objects (what falcon.call returns), with chosen columns.
// rows: [{...}], columns: ["id", "status", ...], optional widths: {id: 60}
Item {
    id: table
    property var rows: []
    property var columns: []
    property var widths: ({})
    property int defaultWidth: 140
    property string emptyText: "(none)"
    signal rowClicked(var row)
    property int selectedIndex: -1

    function fmt(v) {
        if (v === null || v === undefined) return "-"
        if (typeof v === "boolean") return v ? "yes" : "no"
        if (typeof v === "object") return JSON.stringify(v)
        var s = String(v)
        if (s.length > 19 && s.charAt(4) === "-" && s.charAt(10) === "T") return s.substring(0, 16).replace("T", " ")
        return s
    }
    function colWidth(c) { return widths[c] !== undefined ? widths[c] : defaultWidth }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        Row {
            id: headerRow
            Layout.fillWidth: true
            Repeater {
                model: table.columns
                delegate: Label {
                    required property var modelData
                    width: table.colWidth(modelData)
                    text: modelData
                    color: "#9aa"
                    font.bold: true
                    elide: Text.ElideRight
                    padding: 4
                }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: "#444" }
        Label { visible: table.rows.length === 0; text: table.emptyText; color: "#777"; padding: 6 }
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: table.rows
            delegate: Rectangle {
                required property var modelData
                required property int index
                width: list.width
                height: 26
                color: index === table.selectedIndex ? "#3a4a6a" : (index % 2 ? "#232529" : "transparent")
                Row {
                    Repeater {
                        model: table.columns
                        delegate: Label {
                            required property var modelData
                            width: table.colWidth(modelData)
                            text: table.fmt(parent.parent.modelData[modelData])
                            color: "#ddd"
                            elide: Text.ElideRight
                            padding: 4
                        }
                    }
                }
                MouseArea { anchors.fill: parent; onClicked: { table.selectedIndex = index; table.rowClicked(modelData) } }
            }
            ScrollBar.vertical: ScrollBar { }
        }
    }
}
