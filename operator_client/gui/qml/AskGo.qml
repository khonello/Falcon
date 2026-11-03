import QtQuick
import "."

// BEFORE A BUTTON OPENS ANOTHER PAGE (the user, 1 Nov 2026): no sudden jump. It says where it goes and what will be picked
// there; Open goes and the page arrives with that thing picked and pulsing. "Don't ask again" stops it; the line at the foot
// of the menu turns it back on.
Modal {
    id: root
    objectName: "askGo"
    property var req: null
    property bool stop: false
    signal stopAsking()
    width: 460
    title: req ? "Open " + Nav.title(req.page) + "?" : ""

    function ask(r) { req = r; stop = false; open() }

    Column {
        width: parent.width
        spacing: 14
        Txt {
            width: parent.width
            text: root.req && root.req.what ? root.req.what : (root.req ? "This leaves the page you are on." : "")
            color: Theme.text2
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
        }
        Check { objectName: "askGoStop"; text: "Don't ask again"; checked: root.stop; onToggled: function (c) { root.stop = c } }
    }
    footer: [
        Btn { text: "Cancel"; onClicked: root.close() },
        Btn {
            objectName: "askGoOpen"
            kind: "primary"
            text: "Open"
            onClicked: {
                var r = root.req
                if (root.stop) root.stopAsking()
                root.close()
                Nav.arriveAt(r)
            }
        }
    ]
}
