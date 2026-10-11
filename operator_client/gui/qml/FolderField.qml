import QtQuick
import QtQuick.Controls.Basic
import "."

// A folder on one machine: type it, or pick from the folders the file index has seen there.
Item {
    id: root
    property int pcId: 0
    property string text: ""
    property string placeholder: "Folder"
    signal edited(string text)
    property var folders: []
    implicitWidth: 220
    implicitHeight: Theme.control

    onPcIdChanged: load()
    Component.onCompleted: load()
    function load() {
        if (!pcId) { folders = []; return }
        falcon.call("index.folders", { pc_id: pcId }, function (ok, r) { root.folders = ok ? (r.folders || []) : [] })
    }
    readonly property var hits: folders.filter(function (f) { return f.path.toLowerCase().indexOf(root.text.toLowerCase()) >= 0 }).slice(0, 8)

    Field {
        id: f
        anchors.fill: parent
        text: root.text
        placeholderText: root.placeholder
        font.family: Theme.mono
        onTextEdited: { root.edited(text); pop.open() }
        onActiveFocusChanged: if (activeFocus && root.hits.length) pop.open()
    }
    Popup {
        id: pop
        y: root.height + 4
        width: Math.max(root.width, 280)
        padding: 4
        height: Math.min(lv.contentHeight + 8, 240)
        visible: opened && root.hits.length > 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        background: Rectangle { radius: Theme.radius; color: Theme.surface; border.width: 1; border.color: Theme.borderStrong
                                MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons } }
        ListView {
            id: lv
            anchors.fill: parent
            clip: true
            model: root.hits
            delegate: Rectangle {
                required property var modelData
                width: lv.width; height: 30; radius: Theme.radiusSm
                color: ma.containsMouse ? Theme.surface3 : "transparent"
                Txt { x: 8; width: parent.width - 70; anchors.verticalCenter: parent.verticalCenter; text: modelData.path; mono: true; font.pixelSize: 12 }
                Txt { anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; text: Theme.fmt(modelData.files || 0) + " files"; color: Theme.text3; font.pixelSize: 11 }
                MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: { root.edited(modelData.path); pop.close() } }
            }
        }
    }
}
