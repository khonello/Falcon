import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "."

// CONNECTING (board ST01), the first run in plain words. The install package gave this machine three things -- the
// Engine's address, a client id and its key (both printed once, when this machine was registered) -- plus the Engine's
// certificate file. This screen asks for exactly those. Beside it, the one outcome of the last attempt, said once
// with what to do: connecting, a key that does not match, an Engine that cannot be reached, a certificate that
// does not. (A machine whose name changed still connects; that is said by the lid once inside.)
Item {
    id: root

    readonly property string address: String(addressField.text).trim()
    readonly property string hostPart: address.indexOf(":") >= 0 ? address.split(":")[0].trim() : address
    readonly property int portPart: address.indexOf(":") >= 0 ? parseInt(address.split(":")[1]) || 7400 : 7400
    property string certPath: falcon.defaultCaCert
    property bool plaintext: falcon.defaultPlaintext

    function go() {
        falcon.connectTo(hostPart, portPart, whoField.text.trim(), keyField.text.trim(), plaintext, certPath)
    }

    // the gradient frame shows; the card and the outcome sit on it
    RowLayout {
        anchors.centerIn: parent
        spacing: 48

        Rectangle {
            objectName: "connectCard"
            Layout.preferredWidth: 440
            Layout.preferredHeight: form.implicitHeight + 48
            radius: 18
            color: Theme.pane
            Column {
                id: form
                x: 24; y: 24
                width: parent.width - 48
                spacing: 8
                Txt { text: "Connect to the Engine"; color: Theme.ink; font.pixelSize: Theme.fSection + 2; font.weight: Font.Bold }
                Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.dim; font.pixelSize: Theme.fBody
                      text: "The Engine is the machine that runs Falcon for your organisation. Your administrator gave you these." }
                Item { width: 1; height: 6 }
                Txt { text: "Engine address"; color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                Field { id: addressField; objectName: "connectAddress"; width: parent.width
                        text: falcon.defaultHost ? falcon.defaultHost + " : " + falcon.defaultPort : ""
                        placeholderText: "falcon.internal : 7400" }
                Txt { text: "Your client id"; color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold; topPadding: 4 }
                Field { id: whoField; objectName: "connectWho"; width: parent.width; text: falcon.defaultClientId; placeholderText: "paste it here" }
                Txt { text: "given with your key when this machine was registered"; color: Theme.faint; font.pixelSize: Theme.fMeta }
                Txt { text: "Your key"; color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold; topPadding: 4 }
                Field { id: keyField; objectName: "connectKey"; width: parent.width; text: falcon.defaultClientKey
                        echoMode: TextInput.Password; placeholderText: "paste it here" }
                Txt { text: "paste it; it is kept on this machine only"; color: Theme.faint; font.pixelSize: Theme.fMeta }
                Item {
                    width: parent.width; height: 34
                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8
                        Icon { name: "shield"; size: 14; color: root.certPath ? Theme.ok : Theme.faint; anchors.verticalCenter: parent.verticalCenter }
                        Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody
                              color: root.plaintext ? Theme.faint : root.certPath ? Theme.ink : Theme.warn
                              text: root.plaintext ? "no certificate — development only"
                                    : root.certPath ? root.certPath.replace(/\\/g, "/").split("/").pop() + " · the Engine's certificate"
                                    : "the Engine's certificate is not chosen yet" }
                    }
                    GBtn { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Choose…"
                           visible: !root.plaintext; onClicked: certDialog.open() }
                    FileDialog { id: certDialog; nameFilters: ["Certificates (*.crt *.pem)"]
                                 onAccepted: root.certPath = decodeURIComponent(String(selectedFile).replace(/^file:\/{2,3}/, "")) }
                }
                Item {
                    width: parent.width; height: 40
                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 7
                        Rectangle { width: 15; height: 15; radius: 4; anchors.verticalCenter: parent.verticalCenter
                                    color: root.plaintext ? Theme.warnSoft : "transparent"; border.width: 1.2
                                    border.color: root.plaintext ? Theme.warn : Theme.line2
                                    Icon { anchors.centerIn: parent; visible: root.plaintext; name: "check"; size: 10; color: Theme.warn } }
                        Txt { text: "No encryption (development only)"; color: Theme.faint; font.pixelSize: Theme.fMeta
                              anchors.verticalCenter: parent.verticalCenter }
                        TapHandler { onTapped: root.plaintext = !root.plaintext }
                    }
                    TBtn { objectName: "connectButton"; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                           text: falcon.connectState === "connecting" ? "Connecting…" : "Connect"; iconName: "chev"
                           enabled: falcon.connectState !== "connecting" && root.hostPart !== "" && whoField.text.trim() !== ""
                           onClicked: root.go() }
                }
            }
        }

        // the one outcome of the last attempt
        Rectangle {
            objectName: "connectOutcome"
            visible: falcon.connectState === "connecting" || falcon.connectState === "failed"
            Layout.preferredWidth: 400
            Layout.preferredHeight: outcome.implicitHeight + 36
            radius: 14
            color: Theme.pane
            readonly property string kind: falcon.connectState === "connecting" ? "connecting" : falcon.failKind
            Column {
                id: outcome
                x: 18; y: 18
                width: parent.width - 36
                spacing: 8
                Row {
                    spacing: 10
                    Icon { anchors.verticalCenter: parent.verticalCenter; size: 16
                           name: parent.parent.parent.kind === "connecting" ? "clock" : parent.parent.parent.kind === "unreachable" ? "globe"
                                 : parent.parent.parent.kind === "certificate" ? "shield" : "x"
                           color: parent.parent.parent.kind === "connecting" ? Theme.dim : Theme.danger }
                    Txt { objectName: "connectOutcomeTitle"; color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.Bold
                          text: { var k = parent.parent.parent.kind
                                  return k === "connecting" ? "Connecting to " + root.hostPart + "…"
                                       : k === "key" ? "The key doesn't match this client id."
                                       : k === "unreachable" ? "The Engine can't be reached."
                                       : k === "certificate" ? "The Engine's certificate doesn't match."
                                       : "It didn't connect." } }
                }
                Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.dim; font.pixelSize: Theme.fBody
                      text: { var k = parent.parent.kind
                              return k === "connecting" ? "Checking the certificate, then who you are. This takes a moment."
                                   : k === "key" ? "Check you pasted the whole key. If it was re-issued, ask for the new one."
                                   : k === "unreachable" ? root.hostPart + " didn't answer on port " + root.portPart + ". It may be off, or the address is wrong."
                                   : k === "certificate" ? "The file chosen is not this Engine's. Ask your administrator for engine.crt."
                                   : falcon.failMessage } }
                GBtn { visible: parent.parent.kind !== "connecting"; small: true; text: "Try again"; onClicked: root.go() }
            }
        }
    }
}
