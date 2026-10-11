import QtQuick
import "."

// A figure in its own panel: what it counts, the figure (and its unit), a trend line on the right,
// and one line of what changed. `none` is the zero state: "—" and why there is no history.
Rectangle {
    id: root
    property string label: ""
    property string value: ""
    property string unit: ""
    property string delta: ""
    property color dc: Theme.text3
    property var spark: []
    property color sc: Theme.ser6
    property real sparkMax: 0
    property bool none: false
    property string noneValue: "—"
    property string noneText: "No history yet"
    signal clicked()
    property bool link: false

    color: Theme.surface
    radius: Theme.radius
    border.width: 1
    border.color: link && area.containsMouse ? Theme.borderStrong : Theme.border
    implicitHeight: 88

    Column {
        x: 14; y: 12
        width: parent.width - 28
        spacing: 4
        Txt { text: root.label; color: Theme.text3; width: parent.width }
        Item {
            width: parent.width
            height: 30
            Row {
                anchors.bottom: parent.bottom
                spacing: 3
                Txt {
                    id: fig
                    text: root.none ? root.noneValue : root.value
                    font.pixelSize: Theme.fFigure
                    font.weight: Font.DemiBold
                    elide: Text.ElideNone
                }
                Txt {
                    visible: root.unit !== "" && (!root.none || root.unit.indexOf("/") === 0)
                    text: root.unit
                    color: Theme.text3
                    anchors.baseline: fig.baseline
                    elide: Text.ElideNone
                }
            }
            Spark {
                visible: !root.none && root.spark && root.spark.length > 1
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 4
                values: root.spark
                c: root.sc
                max: root.sparkMax
            }
        }
        Txt {
            text: root.none ? root.noneText : root.delta
            color: root.none ? Theme.text3 : root.dc
            font.pixelSize: Theme.fSmall
            width: parent.width
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        enabled: root.link
        hoverEnabled: true
        cursorShape: root.link ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
