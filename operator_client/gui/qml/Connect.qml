import QtQuick
import "."

// NOT CONNECTED. Nothing on any page is live, so it takes the page: where it tried, what went wrong,
// and the one thing to do about it.
Rectangle {
    color: Theme.bg
    Panel {
        anchors.centerIn: parent
        width: 520
        title: "Not connected"
        sub: falcon.connectState === "connecting" ? "connecting…" : ""
        Column {
            width: parent.width
            spacing: 12
            Txt {
                width: parent.width
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
                color: Theme.text2
                text: (falcon.failMessage !== "" ? falcon.failMessage
                       : "The Engine did not answer on " + (falcon.engineAddress || "the address in this console's settings"))
                      + ". Nothing you can see is live until it does."
            }
            Row {
                spacing: 8
                Btn { objectName: "retryConnection"; kind: "primary"; text: "Reconnect"; onClicked: falcon.retryNow() }
                Txt {
                    visible: falcon.retryIn > 0
                    text: "Trying again in " + falcon.retryIn + "s"
                    color: Theme.text3
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
