import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// The install package gave this client three things: an Engine address, a client id + key, and
// the Engine's pinned certificate. This screen asks for exactly those and nothing else.
Item {
    Section {
        anchors.centerIn: parent
        width: 460
        title: "Connect to the Engine"
        hint: "Your client id and key were issued once at provisioning; the certificate pins this Engine."
        spacing: Theme.space2

        GridLayout {
            columns: 2
            columnSpacing: Theme.space3
            rowSpacing: Theme.space2
            Layout.fillWidth: true
            Layout.topMargin: Theme.space2

            Eyebrow { label: "Engine" }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space2
                Field { id: host; Layout.fillWidth: true; text: falcon.defaultHost; placeholderText: "host" }
                Field { id: port; Layout.preferredWidth: 72; text: String(falcon.defaultPort); validator: IntValidator { bottom: 1; top: 65535 } }
            }
            Eyebrow { label: "Client id" }
            Field { id: clientId; Layout.fillWidth: true; text: falcon.defaultClientId; placeholderText: "issued at provisioning"; font.family: Theme.mono }
            Eyebrow { label: "Client key" }
            Field { id: clientKey; Layout.fillWidth: true; text: falcon.defaultClientKey; placeholderText: "issued with the client id"; echoMode: TextInput.Password; font.family: Theme.mono }
            Eyebrow { label: "Certificate" }
            Field { id: caCert; Layout.fillWidth: true; text: falcon.defaultCaCert; placeholderText: "path to the pinned engine.crt"; enabled: !plaintext.checked }
            Item { }
            CheckBox { id: plaintext; text: "plaintext (development only)"; checked: falcon.defaultPlaintext; font.pixelSize: Theme.fontSmall }
        }
        RowLayout {
            Layout.fillWidth: true
            Label { id: err; color: Theme.danger; font.pixelSize: Theme.fontSmall; wrapMode: Text.Wrap; Layout.fillWidth: true
                    Connections { target: falcon; function onConnectionFailed(m) { err.text = m } function onConnected() { err.text = "" } } }
            Btn {
                text: "Connect"
                tint: Theme.accent
                enabled: clientId.text.length > 0
                onClicked: falcon.connectTo(host.text, parseInt(port.text), clientId.text, clientKey.text, plaintext.checked, caCert.text)
            }
        }
    }
}
