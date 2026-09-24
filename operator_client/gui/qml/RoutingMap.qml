import QtQuick
import QtQuick.Shapes
import "."

// Report routing, drawn as what it is: additive. Every category reaches you whatever else is set,
// and routing adds departments to that -- it never takes your copy away.
Item {
    id: root

    property var categories: []            // [{ label, to: [departmentIndex, ...] }]
    property var destinations: []          // [{ index, name }] -- only the departments actually routed to
    readonly property real leftX: 4
    readonly property real rightX: width - 116
    readonly property real rowGap: 34
    // the diagram sizes itself from how many categories there are, so the last label never lands
    // on whatever sits under the panel
    implicitHeight: 16 + Math.max(1, categories.length) * rowGap + 26

    function catY(i) { return 16 + i * rowGap }
    function destY(i) { return 26 + i * 50 }
    readonly property real youY: Math.max(destY(destinations.length - 1) + 44, height - 30)

    function curve(x0, y0, x1, y1) {
        var out = []
        var c1x = x0 + 72, c2x = x1 - 70
        for (var s = 0; s <= 14; s++) {
            var t = s / 14, u = 1 - t
            out.push(Qt.point(u * u * u * x0 + 3 * u * u * t * c1x + 3 * u * t * t * c2x + t * t * t * x1,
                              u * u * u * y0 + 3 * u * u * t * y0 + 3 * u * t * t * y1 + t * t * t * y1))
        }
        return out
    }

    Repeater {
        model: root.categories
        delegate: Item {
            id: cat
            required property var modelData
            required property int index
            anchors.fill: parent

            Txt {
                text: cat.modelData.label
                color: Theme.dim
                font.pixelSize: Theme.fBody
                x: root.leftX
                y: root.catY(cat.index) - height / 2
            }

            Shape {
                anchors.fill: parent
                antialiasing: true
                layer.enabled: true
                layer.samples: 4

                // the copy that always reaches you
                ShapePath {
                    strokeColor: Theme.line2
                    strokeWidth: 1.5
                    fillColor: "transparent"
                    PathPolyline { path: root.curve(root.leftX + 112, root.catY(cat.index), root.rightX, root.youY) }
                }
            }

            Repeater {
                model: cat.modelData.to
                delegate: Shape {
                    id: branch
                    required property var modelData
                    anchors.fill: parent
                    antialiasing: true
                    layer.enabled: true
                    layer.samples: 4

                    ShapePath {
                        strokeColor: Theme.series(branch.modelData)
                        strokeWidth: 2.5
                        fillColor: "transparent"
                        PathPolyline {
                            path: root.curve(root.leftX + 112, root.catY(cat.index),
                                             root.rightX, root.destY(root.destinationRow(branch.modelData)))
                        }
                    }
                }
            }
        }
    }

    function destinationRow(departmentIndex) {
        for (var i = 0; i < destinations.length; i++)
            if (destinations[i].index === departmentIndex) return i
        return 0
    }

    Repeater {
        model: root.destinations
        delegate: Item {
            id: dest
            required property var modelData
            required property int index
            anchors.fill: parent

            Rectangle {
                width: 12
                height: 12
                radius: 6
                color: Theme.series(dest.modelData.index)
                x: root.rightX - 6
                y: root.destY(dest.index) - 6
            }
            Txt {
                text: dest.modelData.name
                font.pixelSize: Theme.fBody
                x: root.rightX + 12
                y: root.destY(dest.index) - height / 2
            }
        }
    }

    Rectangle {
        width: 14
        height: 14
        radius: 7
        color: Theme.ink
        x: root.rightX - 7
        y: root.youY - 7
    }
    Txt {
        text: "You, always"
        font.pixelSize: Theme.fBody
        x: root.rightX + 12
        y: root.youY - height / 2
    }
}
