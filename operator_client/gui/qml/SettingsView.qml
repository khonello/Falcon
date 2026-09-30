import QtQuick
import "."

// WHAT THIS CONSOLE IS CONNECTED TO, and the one thing about you that other people see. There is very
// little here on purpose: nearly everything is decided by the Engine and merely rendered, so a setting
// that cannot change anything does not get a control.
Item {
    id: root

    property string selfName: ""
    property bool saving: false

    function setSelfName(label) {
        saving = true
        falcon.call("hierarchy.set_self_name", { label: label }, function (ok, r) {
            root.saving = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not saved"); return }
            Msg.ok("Saved")
        })
    }

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s4

        PageHeader {
            width: parent.width
            title: "Settings"
            subtitle: "This machine's console, and how it reaches the Engine."
        }

        // not connected is not a small note: nothing on any page is live, so it takes the page
        Result {
            width: parent.width
            height: 200
            visible: !falcon.isConnected
            kind: "danger"
            title: "Not connected"
            hint: (falcon.failMessage !== "" ? falcon.failMessage
                                             : "The Engine did not answer on " + falcon.engineAddress)
                  + ". Nothing you can see here is live."
            Btn { kind: "primary"; text: "Reconnect"; onClicked: falcon.retryNow() }
        }

        Rectangle {
            width: parent.width
            height: conn.implicitHeight + 2 * Theme.s4
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Column {
                id: conn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.s4
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.s2

                Txt { text: "The connection"; strong: true }
                Descriptions {
                    objectName: "connectionFacts"
                    width: parent.width
                    items: [
                        { label: "Engine", value: falcon.engineAddress || "not set", mono: true },
                        { label: "State", value: falcon.isConnected ? "connected" : falcon.connectState,
                          tag: true, tone: falcon.isConnected ? "" : "danger" },
                        { label: "Signed in as", value: falcon.roleLabel },
                        { label: "This machine", value: falcon.defaultClientId || "—", mono: true }
                    ]
                }
                Btn {
                    objectName: "retryConnection"
                    text: "Reconnect"
                    visible: !falcon.isConnected      // a Column skips what is not visible; a Row
                    onClicked: falcon.retryNow()      // wrapping it would have kept the gap
                }
            }
        }

        Rectangle {
            width: parent.width
            height: me.implicitHeight + 2 * Theme.s4
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Column {
                id: me
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.s4
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.s2

                Txt { text: "What people below you see"; strong: true }
                FormRow {
                    width: parent.width
                    label: "Your name"
                    hint: "Only those below you in the hierarchy see this. What somebody above you calls "
                          + "you is theirs, and you never see it -- names do not travel between layers."
                    Field {
                        id: mine
                        objectName: "selfNameField"
                        width: Math.min(parent.width, 320)
                        placeholderText: "How they should see you"
                        onTextChanged: root.selfName = text
                        onAccepted: root.setSelfName(text.trim())
                    }
                }
                Btn {
                    objectName: "saveSelfName"
                    kind: "primary"
                    text: "Save"
                    loading: root.saving
                    enabled: root.selfName.trim() !== ""
                    onClicked: root.setSelfName(root.selfName.trim())
                }
            }
        }

        Txt {
            width: parent.width
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
            tone: "quiet"
            font.pixelSize: Theme.fSmall
            text: "Everything else -- who you may see, what you may do, which reports reach you -- is "
                  + "decided by the Engine and cannot be changed from here."
        }
    }
}
