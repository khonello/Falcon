import QtQuick
import QtQuick.Dialogs
import QtQuick.Controls.Basic
import "."

// FIRST RUN: this console is not set up, so the Engine's address and an admin licence code are asked for here, in the middle, and
// nothing else can be done until it has joined. The certificate is only asked for when the install did not bring one: it stays pinned.
Modal {
    id: root
    objectName: "setupModal"
    visible: falcon.needsSetup
    closePolicy: Popup.NoAutoClose
    closable: false
    title: "Set up Falcon"
    subtitle: "Give this console your Engine's address and a licence code."

    property string address: falcon.setupAddress
    property string code: ""
    property string cert: ""
    readonly property string problem: !address.trim() ? "" : !code.trim() ? "" : falcon.setupNeedsCert && !cert ? "" : "ready"
    function go() { if (problem && !falcon.setupBusy) falcon.setUp(address, code, cert) }

    Column {
        width: root.width - 2 * root.pad
        spacing: 14
        bottomPadding: 8
        Column { width: parent.width; spacing: 6
            Txt { text: "Engine IP address"; font.pixelSize: 13; font.weight: Font.DemiBold }
            Field { objectName: "setupAddress"; width: parent.width; text: root.address; placeholderText: "For example 192.168.1.20"; enabled: !falcon.setupBusy
                    onTextEdited: root.address = text; onAccepted: root.go() } }
        Column { width: parent.width; spacing: 6
            Txt { text: "Licence code"; font.pixelSize: 13; font.weight: Font.DemiBold }
            Field { objectName: "setupCode"; width: parent.width; text: root.code; placeholderText: "From the licence your organisation bought"; enabled: !falcon.setupBusy
                    onTextEdited: root.code = text; onAccepted: root.go() } }
        Column { visible: falcon.setupNeedsCert; width: parent.width; spacing: 6
            Txt { text: "Engine certificate"; font.pixelSize: 13; font.weight: Font.DemiBold }
            Row { width: parent.width; spacing: 8
                Field { width: parent.width - pick.width - 8; text: root.cert; readOnly: true; placeholderText: "engine.crt, from your Engine" }
                Btn { id: pick; text: "Choose…"; enabled: !falcon.setupBusy; onClicked: files.open() } } }
        Decide { visible: falcon.setupError !== ""; c: Theme.crit; text: falcon.setupError }
    }
    FileDialog { id: files; nameFilters: ["Certificates (*.crt *.pem)"]; onAccepted: root.cert = String(selectedFile) }

    footer: Btn { objectName: "setupGo"; kind: "primary"; loading: falcon.setupBusy; enabled: root.problem !== "" && !falcon.setupBusy
                  text: falcon.setupBusy ? "Connecting" : "Connect"; onClicked: root.go() }
}
