import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    ColumnLayout {
        anchors.centerIn: parent
        width: 420
        spacing: 10
        Label { text: "Connect to the Engine"; font.pixelSize: 20; color: "white" }
        GridLayout {
            columns: 2
            columnSpacing: 10
            rowSpacing: 8
            Label { text: "Engine host"; color: "#ccc" }
            TextField { id: host; Layout.fillWidth: true; text: falcon.defaultHost }
            Label { text: "Port"; color: "#ccc" }
            TextField { id: port; Layout.fillWidth: true; text: String(falcon.defaultPort); validator: IntValidator { bottom: 1; top: 65535 } }
            Label { text: "Client id"; color: "#ccc" }
            TextField { id: clientId; Layout.fillWidth: true; text: falcon.defaultClientId; placeholderText: "issued at provisioning" }
            Label { text: ""; }
            CheckBox { id: plaintext; text: "plaintext (development only)"; checked: falcon.defaultPlaintext }
        }
        Button {
            Layout.alignment: Qt.AlignRight
            text: "Connect"
            enabled: clientId.text.length > 0
            onClicked: falcon.connectTo(host.text, parseInt(port.text), clientId.text, plaintext.checked)
        }
        Label { id: err; color: "#ff8a80"; wrapMode: Text.Wrap; Layout.fillWidth: true
                Connections { target: falcon; function onConnectionFailed(m) { err.text = m } function onConnected() { err.text = "" } } }
    }
}
