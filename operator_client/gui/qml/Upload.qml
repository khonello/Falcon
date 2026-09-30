import QtQuick
import "."

// A FILE FROM THIS MACHINE, named and read. Nothing is sent anywhere by this control: it hands the
// text to whatever asked for it, and that decides. A script arrives this way rather than being typed.
Rectangle {
    id: root
    property string fileName: ""
    property string hint: "Drop a file here, or choose one"
    signal loaded(string name, string text)
    signal failed(string why)

    implicitHeight: 84
    radius: Theme.radius
    color: drop.containsDrag ? Theme.primarySoft : Theme.fill
    border.width: 1
    border.color: drop.containsDrag ? Theme.primary : Theme.border
    Behavior on color { ColorAnimation { duration: Theme.durFast } }

    function take(url) {
        var path = String(url).replace("file:///", "")
        var text = falcon.readFile(path)
        if (String(text).indexOf("__error__:") === 0) {
            root.failed(String(text).substring(10))
            return
        }
        root.fileName = path.split("/").pop()
        root.loaded(root.fileName, text)
    }

    DropArea {
        id: drop
        anchors.fill: parent
        onDropped: function (ev) { if (ev.hasUrls) root.take(ev.urls[0]) }
    }

    Column {
        anchors.centerIn: parent
        spacing: Theme.s1

        Icon {
            anchors.horizontalCenter: parent.horizontalCenter
            name: root.fileName === "" ? "cloud" : "file"
            size: 20
            color: Theme.quiet
        }
        Txt {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.fileName === "" ? root.hint : root.fileName
            tone: root.fileName === "" ? "mid" : "ink"
            mono: root.fileName !== ""
            font.pixelSize: Theme.fSmall
        }
    }
}
