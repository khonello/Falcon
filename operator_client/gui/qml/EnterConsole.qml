import QtQuick
import "."

// ENTERING AN ADMIN'S CONSOLE. To work as them the Super User takes their console, so the Admin's own
// session has to stop first: blocked (they keep their place and wait) or ended (signed out). The
// console then becomes that Admin's, under "Super User in charge", until Leave.
//
//   ask(admin, to)   admin: {account_id, name, pc_id, hostname, session, online}; to: [page, sub] to land on
Modal {
    id: root
    objectName: "enterConsole"
    title: admin ? "Enter " + admin.name + "'s console?" : ""
    width: 520

    property var admin: null
    property var to: null
    property string how: "block"            // what was chosen for the console now held
    property string pick: "block"
    property string who: ""                 // the Admin whose console this is
    property bool busy: false

    function ask(a, landing) { admin = a; to = landing || null; pick = "block"; open() }

    function enter() {
        if (!admin) return
        busy = true
        // The Engine ends the occupant either way today; blocking (they keep their place) is asked for
        // and recorded, and logged as an Engine gap.
        falcon.call("hierarchy.traverse", { pc_id: admin.pc_id, force: true, mode: pick }, function (ok, r) {
            root.busy = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "Could not enter"); return }
            root.how = root.pick
            root.who = root.admin.name
            root.close()
            Nav.go(root.to ? root.to[0] : "overview", root.to ? root.to[1] : null)
            Msg.ok((root.how === "end" ? "Ended " : "Blocked ") + root.who + "'s session. You are in their console.")
        })
    }
    function leaveConsole() {
        var s = falcon.session
        if (!s) return
        var who = root.who
        falcon.call("hierarchy.end_session", { session_id: s.session_id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Still inside"); return }
            Nav.go("departments")
            Msg.ok("Left " + (who || "the Admin") + "'s console. Their session is back.")
        })
    }

    Txt {
        width: parent.width
        wrapMode: Text.WordWrap
        elide: Text.ElideNone
        color: Theme.text2
        text: root.admin ? root.admin.name + " is "
                           + (root.admin.session && root.admin.session.occupied_via === "traversal"
                              ? "inside a machine right now"
                              : root.admin.online ? "signed in on " + (root.admin.hostname || "their workstation") : "not signed in")
                           + ". To work as them you take their console, so their own session has to stop first." : ""
    }
    Column {
        width: parent.width
        spacing: 8
        Choice {
            width: parent.width
            on: root.pick === "block"
            icon: "pausecircle"
            title: "Block their session"
            desc: (root.admin ? root.admin.name : "They") + " keeps their place and waits until you leave."
            onClicked: root.pick = "block"
        }
        Choice {
            width: parent.width
            on: root.pick === "end"
            icon: "logout"
            title: "End their session"
            desc: (root.admin ? root.admin.name : "They") + " is signed out. Anything open on their side closes."
            onClicked: root.pick = "end"
        }
    }
    Txt {
        width: parent.width
        wrapMode: Text.WordWrap
        elide: Text.ElideNone
        color: Theme.text3
        font.pixelSize: Theme.fSmall
        text: "While you are in, nobody can move you out, and their workstation shows that the Super User is in charge. The record notes when you entered and left."
    }

    footer: [
        Btn { text: "Cancel"; onClicked: root.close() },
        Btn {
            objectName: "enterConsoleGo"
            kind: "primary"
            danger: root.pick === "end"
            loading: root.busy
            text: root.pick === "end" ? "End and enter" : "Block and enter"
            onClicked: root.enter()
        }
    ]
}
