import QtQuick
import "."

// REGISTER A PC, PROVISION AN ADMIN, OR A NEW KEY: one drawer in two steps. The first asks the name and the
// department; the second shows the key, once. A new key skips the first step (the confirm came before).
//   ask({mode: "pc" | "admin" | "rekey" | "promote", subject?, pc_id?, account_id?})
// "promote" makes a worker an Admin of their department (hierarchy.admin_promote): their machine gets a new key, shown here.
Drawer {
    id: kd
    width: 480
    property var spec: null
    property int step: 0
    property string name: ""
    property var dept: null
    property var made: null
    property bool busy: false
    readonly property bool rk: spec !== null && spec.mode === "rekey"
    readonly property bool pc: spec !== null && spec.mode === "pc"
    readonly property bool pr: spec !== null && spec.mode === "promote"
    title: !spec ? "" : pr ? spec.subject + " becomes an Admin" : rk ? "New key for " + spec.subject : pc ? "Register a PC" : "Provision an Admin"
    note: step === 0 && spec && !rk ? (!name.trim() ? (pc ? "Name the machine." : "Name the machine they will work on.") : dept === null ? "Pick the department." : "") : ""
    signal done()

    function ask(s) { spec = s; name = ""; dept = s.department_id !== undefined ? s.department_id : null; made = null; busy = false; step = s.mode === "rekey" || s.mode === "promote" ? 1 : 0; open()
                      if (s.mode === "rekey") rekey(); if (s.mode === "promote") promote() }
    function promote() {
        busy = true
        falcon.call("hierarchy.admin_promote", { account_id: spec.account_id }, function (ok, r) {
            kd.busy = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not promoted"); kd.close(); return }
            kd.made = r; Msg.ok(kd.spec.subject + " is an Admin now · recorded"); kd.done()
        })
    }
    function rekey() {
        busy = true
        falcon.call("hierarchy.pc_rekey", { pc_id: spec.pc_id }, function (ok, r) {
            kd.busy = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "No new key"); kd.close(); return }
            kd.made = r; kd.done()
        })
    }
    function submit() {
        busy = true
        var cb = function (ok, r) {
            kd.busy = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
            kd.made = r; kd.step = 1; Msg.ok(kd.name.trim() + " registered · recorded in the audit log"); kd.done()
        }
        if (pc) falcon.call("hierarchy.pc_register", { hostname: name.trim(), department_id: dept, pc_type: "client_pc" }, cb)
        else falcon.call("hierarchy.account_create", { role: "admin", hostname: name.trim(), department_id: dept }, cb)
    }

    footer: [
        Btn { visible: kd.step === 0; text: "Cancel"; onClicked: kd.close() },
        Btn { visible: kd.step === 0; kind: "primary"; text: kd.pc ? "Register" : "Provision"; enabled: !kd.busy && kd.name.trim() !== "" && kd.dept !== null; onClicked: kd.submit() },
        Btn { visible: kd.step === 1; kind: "primary"; enabled: kd.made !== null; text: "I have saved it"; onClicked: kd.close() }
    ]

    Column {
        visible: kd.step === 0
        width: parent.width
        spacing: 18
        Column { width: parent.width; spacing: 6
                 Txt { text: kd.pc ? "MACHINE NAME" : "THEIR WORKSTATION"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                 Field { width: parent.width; text: kd.name; placeholderText: kd.pc ? "OPS-08" : "ADM-OPS-03"; onTextEdited: kd.name = text } }
        Column { width: parent.width; spacing: 6
                 Txt { text: "DEPARTMENT"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                 Select { width: parent.width; search: true; placeholder: "Which department?"; value: kd.dept
                          options: Fleet.depts.map(function (d) { return { value: d.id, label: d.name } }); onPicked: function (v) { kd.dept = v } } }
        Rectangle {
            width: parent.width; height: hint.height + 20; radius: 6; color: Theme.surface2
            Txt { id: hint; x: 12; y: 10; width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                  text: kd.pc ? "The machine joins the department and shows up in its fleet. It gets a key, shown once."
                              : "They get a console and a key, shown once. The department's reports start reaching them once you route them." }
        }
    }
    Column {
        visible: kd.step === 1
        width: parent.width
        spacing: 12
        Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2
              text: kd.made === null ? "Making the key…"
                  : kd.pr ? kd.spec.subject + " is an Admin of their department. Their machine's Worker install stops working: install the Operator Client on it with this key."
                  : (kd.rk ? "The old key for " + kd.spec.subject + " stops working at once." : kd.name.trim() + " is registered.")
                    + " Copy this into " + (kd.rk || kd.pc ? "the machine's Worker Client settings." : "their Operator Client settings.") }
        Repeater {
            model: kd.made ? [["Client id", kd.made.client_id], ["Key", kd.made.client_key]] : []
            Column { required property var modelData; width: parent.width; spacing: 4
                     Txt { text: modelData[0].toUpperCase(); color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                     Rectangle { width: parent.width; height: kt.height + 24; radius: 6; color: Theme.surface2; border.color: Theme.borderStrong
                                 TextEdit { id: kt; x: 14; y: 12; width: parent.width - 60; text: modelData[1]; readOnly: true; selectByMouse: true; wrapMode: TextEdit.WrapAnywhere
                                            font.family: Theme.mono; font.pixelSize: 13; color: Theme.text; selectionColor: Theme.accentSoft; selectedTextColor: Theme.text }
                                 Btn { anchors.right: parent.right; anchors.rightMargin: 6; anchors.verticalCenter: parent.verticalCenter; small: true; kind: "ghost"; iconName: "copy"; tip: "Copy"
                                       onClicked: { kt.selectAll(); kt.copy(); kt.deselect(); Msg.ok(modelData[0] + " copied") } } } }
        }
        Rectangle {
            width: parent.width; height: once.height + 20; radius: 6
            color: Theme.alpha(Theme.med, 0.08); border.color: Theme.alpha(Theme.med, 0.35)
            Txt { id: once; x: 12; y: 10; width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: 12; textFormat: Text.RichText
                  text: "<b>It is shown once.</b> It cannot be shown again. If it is lost, make a new one." }
        }
    }
}
