import QtQuick
import "."

// WHO MAY OPEN A PRIVATE FILE: the people of the organisation (chat.people: the other Admins, and the person of each machine), found by a
// search and ticked. Whoever makes it private may always open it, so they are not listed. `picked` is the account ids ticked; the
// owner of the list sets it from `changed`.
Column {
    id: root
    property var people: []                 // chat.people's people: [{account_id, name, role, hostname, department}]
    property var picked: []
    property string q: ""
    signal changed(var ids)
    width: parent ? parent.width : 400
    spacing: 8

    // one row per person, however many machines they are on
    readonly property var everyone: {
        var seen = {}, out = []
        people.forEach(function (p) {
            if (!p.account_id || seen[p.account_id]) return
            seen[p.account_id] = true
            out.push({ id: p.account_id, name: p.name || "Account " + p.account_id, admin: p.role === "admin",
                       sub: [p.hostname, p.department].filter(function (x) { return !!x }).join(" · ") })
        })
        return out
    }
    readonly property var shown: {
        var s = q.trim().toLowerCase()
        return everyone.filter(function (p) { return !s || (p.name + " " + p.sub).toLowerCase().indexOf(s) >= 0 })
    }
    function has(id) { return picked.indexOf(id) >= 0 }
    function flip(id, on) { root.changed(on ? picked.concat([id]) : picked.filter(function (x) { return x !== id })) }

    Field { objectName: "readersSearch"; width: parent.width; small: true; iconName: "search"; placeholderText: "Search people by name or machine"; text: root.q; onTextEdited: root.q = text }
    Rectangle {
        width: parent.width
        height: Math.min(list.height, 248) + 2
        radius: Theme.radius
        color: "transparent"
        border.width: 1
        border.color: Theme.border
        Flickable {
            x: 1; y: 1
            width: parent.width - 2
            height: parent.height - 2
            contentHeight: list.height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            Column {
                id: list
                width: parent.width
                Repeater {
                    model: root.shown
                    delegate: Rectangle {
                        id: pr
                        required property var modelData
                        required property int index
                        objectName: "reader_" + modelData.id
                        width: list.width
                        height: 40
                        color: pa.containsMouse ? Theme.surface3 : "transparent"
                        Check { x: 12; anchors.verticalCenter: parent.verticalCenter; controlled: true; checked: root.has(pr.modelData.id); onToggled: function (v) { root.flip(pr.modelData.id, v) } }
                        Column {
                            x: 40; anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 40 - 80
                            Txt { width: parent.width; text: pr.modelData.name; font.pixelSize: 13; font.weight: Font.Medium }
                            Txt { visible: text !== ""; width: parent.width; text: pr.modelData.sub; mono: true; color: Theme.text3; font.pixelSize: 12 }
                        }
                        Txt { visible: pr.modelData.admin; anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: "Admin"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                        Rectangle { visible: pr.index < root.shown.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                        MouseArea { id: pa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.flip(pr.modelData.id, !root.has(pr.modelData.id)) }
                    }
                }
                Txt { visible: root.shown.length === 0; padding: 12; text: root.everyone.length ? "Nobody by that name." : "Nobody else has an account yet."; color: Theme.text3; font.pixelSize: 13 }
            }
        }
    }
    Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
          text: (root.picked.length ? Theme.many(root.picked.length, "person", "people") + " named, and you." : "Only you, so far.") + " Whoever made it private may always open it." }
}
