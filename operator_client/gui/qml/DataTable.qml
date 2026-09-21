import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// A table over a JS array of objects (what falcon.call returns), with chosen columns.
// rows: [{...}], columns: ["id", "status", ...], optional widths: {id: 60}, optional titles:
// {description_raw: "description"}, optional tints: {status: function(v, row) -> color}.
// Rows are dense and quiet: hover instead of zebra striping, an accent edge on the selected row.
Item {
    id: table
    property var rows: []
    property var columns: []
    property var widths: ({})
    property var titles: ({})
    property var tints: ({})
    property int defaultWidth: 140
    property string emptyText: "Nothing here"
    property string emptyHint: ""
    signal rowClicked(var row)
    property int selectedIndex: -1
    onRowsChanged: selectedIndex = -1

    function fmt(v) {
        if (v === null || v === undefined) return "—"
        if (typeof v === "boolean") return v ? "yes" : "no"
        if (typeof v === "object") return JSON.stringify(v)
        var s = String(v)
        if (s.length > 19 && s.charAt(4) === "-" && s.charAt(10) === "T") return s.substring(0, 16).replace("T", " ")
        return s
    }
    function colWidth(c) { return widths[c] !== undefined ? widths[c] : defaultWidth }
    function colTitle(c) { return titles[c] !== undefined ? titles[c] : c.replace(/_/g, " ") }
    function cellColor(c, v, row) { return tints[c] !== undefined ? tints[c](v, row) : Theme.text }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        Row {
            Layout.fillWidth: true
            leftPadding: Theme.space1
            Repeater {
                model: table.columns
                delegate: Eyebrow {
                    required property var modelData
                    width: table.colWidth(modelData)
                    label: table.colTitle(modelData)
                    elide: Text.ElideRight
                    padding: Theme.space1
                    leftPadding: Theme.space2
                }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
        ColumnLayout {
            visible: table.rows.length === 0
            Layout.fillWidth: true
            Layout.topMargin: Theme.space4
            spacing: 2
            Label { text: table.emptyText; color: Theme.textDim; font.pixelSize: Theme.fontMedium; font.bold: true; Layout.alignment: Qt.AlignHCenter }
            Label { visible: table.emptyHint !== ""; text: table.emptyHint; color: Theme.textFaint; font.pixelSize: Theme.fontSmall; Layout.alignment: Qt.AlignHCenter }
        }
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: table.rows
            delegate: Rectangle {
                id: rowItem
                required property var modelData
                required property int index
                readonly property bool selected: index === table.selectedIndex
                width: list.width
                height: 28
                color: selected ? Theme.wash(Theme.accent, 0.12) : (hover.hovered ? Qt.rgba(1, 1, 1, 0.04) : "transparent")
                Rectangle { visible: rowItem.selected; anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 2; color: Theme.accent }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.wash(Theme.border, 0.6) }
                Row {
                    anchors.fill: parent
                    leftPadding: Theme.space1
                    Repeater {
                        model: table.columns
                        delegate: Label {
                            required property var modelData
                            width: table.colWidth(modelData)
                            height: rowItem.height
                            text: table.fmt(rowItem.modelData[modelData])
                            color: table.cellColor(modelData, rowItem.modelData[modelData], rowItem.modelData)
                            font.pixelSize: Theme.fontBody
                            font.family: (modelData === "id" || modelData.indexOf("_id") > 0 || modelData.indexOf("_at") > 0 || modelData.indexOf("hash") >= 0) ? Theme.mono : Qt.application.font.family
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                            leftPadding: Theme.space2
                            rightPadding: Theme.space1
                        }
                    }
                }
                HoverHandler { id: hover }
                TapHandler { onTapped: { table.selectedIndex = rowItem.index; table.rowClicked(rowItem.modelData) } }
            }
            ScrollBar.vertical: ScrollBar { }
        }
    }
}
