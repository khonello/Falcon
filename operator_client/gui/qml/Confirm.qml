import QtQuick
import "."

// A confirmation: the question as the title, what actually happens to a person under it, then Cancel
// and the act. One per page is enough: `ask({title, text, ok, cancel, danger}, onOk)`.
Modal {
    id: root
    objectName: "confirm"
    property string cost: ""
    property string verb: "Yes"
    property string cancelText: "Cancel"
    property bool destructive: false
    property var okFn: null
    signal accepted()

    width: 440

    function ask(o, fn) {
        title = o.title || ""
        cost = o.text || ""
        verb = o.ok || "Yes"
        cancelText = o.cancel || "Cancel"
        destructive = !!o.danger
        okFn = fn || null
        open()
    }

    Row {
        width: parent.width
        spacing: 12
        Icon { name: "info"; size: 20; color: root.destructive ? Theme.crit : Theme.med }
        Txt {
            width: parent.width - 32
            text: root.cost
            color: Theme.text2
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
        }
    }

    footer: [
        Btn { text: root.cancelText; onClicked: root.close() },
        Btn {
            objectName: "confirmYes"
            kind: "primary"
            danger: root.destructive
            text: root.verb
            onClicked: { var f = root.okFn; root.close(); root.accepted(); if (f) f() }
        }
    ]
}
