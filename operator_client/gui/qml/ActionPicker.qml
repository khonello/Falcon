import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Which actions an event fires, chosen BY NAME from the Actions page's library -- never typed as ids.
// The chosen ones are chips (x removes one); the drop-down under them adds another, and lists only
// the actions not already chosen.
ColumnLayout {
    id: root

    property var actions: []        // the library: [{id, name, builtin_type, kind}]
    property var selected: []       // action ids, in firing order
    spacing: 6

    function nameOf(id) {
        for (var i = 0; i < actions.length; i++)
            if (actions[i].id === id) return actions[i].name || actions[i].builtin_type || ("action " + id)
        return "action " + id
    }
    readonly property var remaining: actions.filter(function (a) { return root.selected.indexOf(a.id) < 0 })

    Flow {
        Layout.fillWidth: true
        spacing: 6
        visible: root.selected.length > 0
        Repeater {
            model: root.selected
            delegate: Rectangle {
                required property var modelData
                required property int index
                height: 26
                width: chipRow.implicitWidth + 18
                radius: 13
                color: Theme.toneSoft("accent")
                Row {
                    id: chipRow
                    anchors.centerIn: parent
                    spacing: 6
                    Label { text: root.nameOf(modelData); color: Theme.text; font.pixelSize: Theme.fontBody
                            anchors.verticalCenter: parent.verticalCenter }
                    Label {
                        text: "×"; color: Theme.textDim; font.pixelSize: Theme.fontMedium
                        anchors.verticalCenter: parent.verticalCenter
                        TapHandler { onTapped: { var s = root.selected.slice(); s.splice(index, 1); root.selected = s } }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                }
            }
        }
    }
    Label {
        visible: root.selected.length === 0
        text: "No action chosen: the event will fire and do nothing."
        color: Theme.textFaint
        font.pixelSize: Theme.fontBody
    }
    Picker {
        id: add
        objectName: "actionPickerAdd"
        Layout.fillWidth: true
        enabled: root.remaining.length > 0
        model: [root.remaining.length > 0 ? "Add an action…" : "Every action is chosen"].concat(
                   root.remaining.map(function (a) { return a.name || a.builtin_type }))
        onActivated: function (i) {
            if (i <= 0) return
            root.selected = root.selected.concat([root.remaining[i - 1].id])
            add.currentIndex = 0
        }
    }
}
