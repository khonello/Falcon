import QtQuick
import QtQuick.Controls
import "."

// THE FEW THAT INTERRUPT (board DG01). Only an act with a cost interrupts, and every one is this dialog:
//
//   a title that asks the question ("End R. Mensah's session and enter?")
//   the cost as one sentence, then as rows -- what happens to whom -- BEFORE the button
//   a button that names the act ("Offboard Kojo", never "OK"), tonal red when it destroys; Cancel always beside it
//   a one-time secret (a new key) shown once, said to be shown once, with Copy; its only button is "I've saved it"
//   an optional name to type (a hostname) or a pick from a few people
//
// The page asks: shell.ask({ title, lead, rows, body, act, actTone, cancel, field, picks, secret }, function (answer) {...})
Popup {
    id: root

    property var spec: ({})
    property var onAct: null
    property string typed: ""
    property var picked: null

    modal: true
    dim: true
    anchors.centerIn: Overlay.overlay
    width: 460
    padding: 24
    closePolicy: spec.secret ? Popup.NoAutoClose : Popup.CloseOnEscape | Popup.CloseOnPressOutside
    Overlay.modal: Rectangle { color: Qt.rgba(0.04, 0.03, 0.08, 0.55) }

    function ask(s, cb) {
        spec = s
        onAct = cb
        typed = ""
        picked = null
        open()
    }
    function act() {
        var cb = onAct
        var answer = spec.picks ? picked : spec.field ? typed.trim() : true
        close()
        if (cb) cb(answer)
    }

    background: Rectangle {
        radius: 18
        color: Theme.pane
        border.width: root.spec.secret ? 1 : 0
        border.color: Qt.rgba(Theme.warn.r, Theme.warn.g, Theme.warn.b, 0.6)
    }

    contentItem: Column {
        spacing: 12
        Txt { objectName: "dialogTitle"; width: parent.width; wrapMode: Text.WordWrap; text: root.spec.title || ""
              color: Theme.ink; font.pixelSize: Theme.fSection + 2; font.weight: Font.Bold }
        Txt { visible: !!root.spec.lead; width: parent.width; wrapMode: Text.WordWrap; text: root.spec.lead || ""
              color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
        Txt { visible: !!root.spec.body; width: parent.width; wrapMode: Text.WordWrap; text: root.spec.body || ""
              color: Theme.dim; font.pixelSize: Theme.fBody }
        Repeater {
            model: root.spec.rows || []
            delegate: Item {
                required property var modelData
                width: parent.width; height: 36
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                Txt { anchors.verticalCenter: parent.verticalCenter; text: modelData[0]; color: Theme.dim; font.pixelSize: Theme.fBody }
                Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]
                      color: modelData[2] ? Theme.tone(modelData[2]) : Theme.dim; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
            }
        }
        // a name to type
        Column {
            visible: !!root.spec.field
            width: parent.width
            spacing: 6
            Txt { text: root.spec.field ? root.spec.field.label : ""; color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
            Field { id: typedField; objectName: "dialogField"; width: parent.width
                    placeholderText: root.spec.field ? root.spec.field.placeholder || "" : ""
                    text: root.typed; onTextEdited: root.typed = text }
        }
        // a pick from a few people
        Repeater {
            model: root.spec.picks || []
            delegate: InfoCard {
                required property var modelData
                width: parent.width
                initials: Theme.initials(modelData.name || "")
                title: modelData.name || ""; line: modelData.line || ""
                selected: root.picked === modelData
                onClicked: root.picked = modelData
            }
        }
        // a one-time secret
        Column {
            visible: !!root.spec.secret
            width: parent.width
            spacing: 8
            Repeater {
                model: root.spec.secret || []
                delegate: Column {
                    required property var modelData
                    width: parent.width
                    spacing: 4
                    Txt { text: modelData[0]; color: Theme.faint; font.pixelSize: Theme.fMeta }
                    Rectangle {
                        width: parent.width; height: 46; radius: 10; color: Theme.ground
                        Txt { id: secretText; anchors.centerIn: parent; monospace: true; font.pixelSize: Theme.fRow; color: Theme.ink
                              text: String(modelData[1]).replace(/(.{4})(?=.)/g, "$1 ") }
                        TextEdit { id: clip; visible: false; text: modelData[1] }
                    }
                    Item {
                        width: parent.width; height: 26
                        GBtn { small: true; text: "Copy"; anchors.verticalCenter: parent.verticalCenter
                               onClicked: { clip.selectAll(); clip.copy(); shell.notify("Copied", false) } }
                    }
                }
            }
            Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                  text: "It is shown once — Falcon can't show it again. If it is lost, issue a new key from the machine." }
        }
        Item { width: 1; height: 4 }
        Item {
            width: parent.width; height: 34
            Txt { visible: !!root.spec.link; anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                  text: root.spec.link ? root.spec.link.text : ""; color: Theme.accent; font.pixelSize: Theme.fBody
                  MouseArea { anchors.fill: parent; anchors.margins: -4; cursorShape: Qt.PointingHandCursor
                              onClicked: { var f = root.spec.link.onClicked; root.close(); if (f) f() } } }
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                GBtn { visible: !root.spec.secret; text: root.spec.cancel || "Cancel"; onClicked: root.close() }
                TBtn { objectName: "dialogAct"; text: root.spec.act || "OK"; tone: root.spec.actTone || "accent"
                       iconName: root.spec.actIcon || ""
                       enabled: (!root.spec.field || root.typed.trim() !== "") && (!root.spec.picks || root.picked !== null)
                       onClicked: root.act() }
            }
        }
    }
}
