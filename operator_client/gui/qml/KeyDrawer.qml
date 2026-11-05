import QtQuick
import "."

// A NEW KEY for a machine, shown once (the concept's KeyModal). A machine joins with its licence code, so a key is only ever replaced here.
//   ask({mode: "rekey", subject, pc_id})
Drawer {
    id: kd
    width: 480
    property var spec: null
    property var made: null
    title: spec ? "New key for " + spec.subject : ""
    signal done()

    function ask(s) {
        spec = s; made = null; open()
        falcon.call("hierarchy.pc_rekey", { pc_id: s.pc_id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "No new key"); kd.close(); return }
            kd.made = r; kd.done()
        })
    }

    footer: Btn { kind: "primary"; enabled: kd.made !== null; text: "I have saved it"; onClicked: kd.close() }

    Column {
        width: parent.width
        spacing: 12
        Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2
              text: kd.made === null ? "Making the key…" : "The old key for " + kd.spec.subject + " stops working at once. Copy this into the machine's Worker Client settings." }
        // the key alone: the machine keeps its id, and only the key changes
        Rectangle { visible: !!kd.made; width: parent.width; height: kt.height + 24; radius: 6; color: Theme.surface2; border.color: Theme.borderStrong
                    TextEdit { id: kt; x: 14; y: 12; width: parent.width - 60; text: kd.made ? kd.made.client_key : ""; readOnly: true; selectByMouse: true; wrapMode: TextEdit.WrapAnywhere
                               font.family: Theme.mono; font.pixelSize: 13; color: Theme.text; selectionColor: Theme.accentSoft; selectedTextColor: Theme.text }
                    Btn { anchors.right: parent.right; anchors.rightMargin: 6; anchors.verticalCenter: parent.verticalCenter; small: true; kind: "ghost"; iconName: "copy"; tip: "Copy"
                          onClicked: { kt.selectAll(); kt.copy(); kt.deselect(); Msg.ok("Key copied") } } }
        Decide { c: Theme.med; text: "It is shown once. It cannot be shown again. If it is lost, make a new one." }
    }
}
