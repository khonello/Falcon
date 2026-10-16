import QtQuick
import "."

// MESSAGES HAS TWO SIDES: conversations (a person asks, someone answers) and announcements (one person tells many). The same switch sits at the top of both.
Item {
    id: root
    objectName: "messageTabs"
    width: parent ? parent.width : 400
    height: 34
    Segmented {
        options: [{ value: "conversations", label: "Conversations" }, { value: "announcements", label: "Announcements" }]
        value: Nav.sub === "announcements" ? "announcements" : "conversations"
        onPicked: function (v) { Nav.go("messages", v === "announcements" ? "announcements" : undefined) }
    }
}
