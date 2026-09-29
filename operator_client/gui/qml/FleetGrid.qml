import QtQuick
import "."

// A DEPARTMENT'S MACHINES AT A GLANCE, four or two hundred and forty. The table is still the default
// answer; this is for the moment a table stops being scannable, and it says exactly one thing per
// machine -- the state -- because that is all that survives at this size.
Item {
    id: root
    property var machines: []
    property int cell: 96
    signal chose(var machine)

    readonly property var groups: {
        var by = {}, order = []
        for (var i = 0; i < machines.length; i++) {
            var m = machines[i]
            if (!by[m.department]) { by[m.department] = []; order.push(m.department) }
            by[m.department].push(m)
        }
        return order.map(function (name) { return { name: name, machines: by[name] } })
    }

    // only the two hues that mean somebody must act get a tint. "Entered" is a word, not a colour:
    // the accent is for interaction and never for status (docs/UI.md).
    function fill(state) {
        return state === "danger" ? Theme.dangerSoft
               : state === "warn" ? Theme.warnSoft
               : state === "free" ? Theme.surface : Theme.fill
    }
    function edge(state) {
        return state === "danger" ? "#ffccc7" : state === "warn" ? "#ffe58f" : Theme.split
    }

    Flickable {
        anchors.fill: parent
        contentHeight: stack.implicitHeight
        clip: true

        Column {
            id: stack
            width: parent.width
            spacing: Theme.s4

            Repeater {
                model: root.groups
                delegate: Column {
                    required property var modelData
                    width: stack.width
                    spacing: Theme.s2

                    Row {
                        spacing: Theme.s2
                        Txt { text: modelData.name; strong: true; font.pixelSize: Theme.fSmall }
                        Txt {
                            text: Theme.many(modelData.machines.length, "machine")
                            tone: "quiet"
                            font.pixelSize: Theme.fSmall
                        }
                    }

                    Flow {
                        width: parent.width
                        spacing: Theme.s2

                        Repeater {
                            model: modelData.machines
                            delegate: Rectangle {
                                required property var modelData
                                width: root.cell
                                height: 64
                                radius: Theme.radius
                                color: root.fill(modelData.state)
                                border.width: 1
                                border.color: hover.hovered ? Theme.primary : root.edge(modelData.state)
                                Behavior on border.color { ColorAnimation { duration: Theme.durFast } }

                                Column {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.margins: Theme.s2
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 2

                                    Txt {
                                        width: parent.width
                                        text: modelData.host
                                        mono: true
                                        strong: true
                                        font.pixelSize: Theme.fSmall
                                    }
                                    Txt {
                                        width: parent.width
                                        text: modelData.stateWord
                                        tone: modelData.state === "danger" ? "danger"
                                              : modelData.state === "warn" ? "warn" : "mid"
                                        font.pixelSize: 11
                                    }
                                }

                                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: root.chose(modelData) }
                            }
                        }
                    }
                }
            }
        }
    }

    Empty {
        anchors.centerIn: parent
        width: 300
        visible: root.machines.length === 0
        text: "No machines yet"
        hint: "A machine appears here once it is registered."
    }
}
