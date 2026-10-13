import QtQuick
import QtQuick.Controls.Basic
import "."

// NEW CUSTOM ACTION (or Edit): a script the worker client runs on a machine. It is checked as you type
// with the same check the Engine and then each machine run on it (compiles; only the standard library
// and Windows-native imports). It runs without a sandbox, so that is said beside it.
Page {
    id: page
    objectName: "newAction"
    bare: true

    readonly property int editId: Nav.sub && String(Nav.sub).indexOf("edit-") === 0 ? Number(String(Nav.sub).slice(5)) : 0
    property string name: ""
    property string desc: ""
    property string lang: "python"
    property string src: "import os\n\n# write what the action does\nprint(os.environ[\"COMPUTERNAME\"])\n"
    property int limit: 60
    property var lastSaved: 0

    Component.onCompleted: if (editId) falcon.call("control.action_list", {}, function (ok, r) {
        var a = ok ? ((r.actions || {}).custom || []).filter(function (x) { return x.id === page.editId })[0] : null
        if (!a) return
        page.name = a.name; page.desc = a.description || ""; page.lang = a.custom_script_language || "python"
        page.src = a.custom_script || ""; page.limit = a.timeout_seconds || 60
    })
    readonly property var chk: falcon.validateScript(lang, src)
    readonly property var used: {
        var out = [], re = lang === "python" ? /^\s*(?:import\s+([\w.]+(?:\s*,\s*[\w.]+)*)|from\s+([\w.]+)\s+import)/gm : /Import-Module\s+([\w.\-]+)/gi, m
        while ((m = re.exec(src)) !== null) {
            (m[1] ? m[1].split(",") : [m[2]]).forEach(function (x) { if (x) { var n = x.trim().split(".")[0]; if (out.indexOf(n) < 0) out.push(n) } })
        }
        return out
    }
    readonly property bool ready: !!chk && chk.ok && name.trim() !== ""
    function switchLang(l) { lang = l; src = l === "python" ? "import os\n\n# write what the action does\nprint(os.environ[\"COMPUTERNAME\"])\n" : "$name = $env:COMPUTERNAME\nWrite-Output $name\n" }
    function save() {
        var p = page.editId ? { action_id: page.editId, name: name.trim(), description: desc.trim(), script: src, timeout_s: limit }
                            : { kind: "custom", name: name.trim(), description: desc.trim(), language: lang, script: src, timeout_s: limit }
        falcon.call(page.editId ? "control.action_update" : "control.action_create", p, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not saved"); return }
            Msg.ok(page.editId ? "Saved · checked again on each machine when it arrives" : "Saved to the library")
            Nav.go("actions", page.editId || (r.action ? r.action.id : null))
        })
    }

    component FieldRow: Row {
        property string label: ""
        default property alias inner: fr.data
        Txt { width: 130; text: parent.label; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
        Row { id: fr; spacing: 10; anchors.verticalCenter: parent.verticalCenter }
    }

    Item {
        width: parent.width
        height: Math.max(form.height, checks.height)
        Row {
            width: Math.min(1000, parent.width)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 14
            Panel {
                id: form
                width: (parent.width - 14) * 8 / 12
                title: page.editId ? "Edit " + page.name : "New custom action"
                sub: "a script the worker client runs on a machine" + (page.editId ? " · rules that use it get the new version from their next run" : "")
                Column {
                    width: parent.width
                    spacing: 16
                    FieldRow { label: "Name"; Field { width: 360; text: page.name; placeholderText: "e.g. Clear the print queue"; onTextEdited: page.name = text } }
                    FieldRow { label: "What it does"; Field { width: form.width - 180; text: page.desc; placeholderText: "One line, shown in the library and when someone runs it"; onTextEdited: page.desc = text } }
                    FieldRow { label: "Language"; Segmented { small: false; enabled: !page.editId; options: [{ value: "python", label: "Python" }, { value: "powershell", label: "PowerShell" }]; value: page.lang; onPicked: function (v) { page.switchLang(v) } } }
                    Column {
                        width: parent.width
                        spacing: 6
                        Txt { text: "SCRIPT"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                        Rectangle {
                            width: parent.width
                            height: 300
                            radius: 5
                            color: Theme.surface2
                            border.width: 1
                            border.color: editor.activeFocus ? Theme.accent : Theme.borderStrong
                            Flickable {
                                anchors.fill: parent
                                contentHeight: editor.implicitHeight
                                clip: true
                                TextArea.flickable: TextArea {
                                    id: editor
                                    text: page.src
                                    font.family: Theme.mono
                                    font.pixelSize: 12
                                    color: Theme.text
                                    wrapMode: TextEdit.NoWrap
                                    selectByMouse: true
                                    selectionColor: Theme.alpha(Theme.accent, 0.3)
                                    tabStopDistance: 28
                                    leftPadding: 12; rightPadding: 12; topPadding: 10; bottomPadding: 10
                                    background: null
                                    onTextChanged: if (text !== page.src) page.src = text
                                }
                            }
                        }
                    }
                    FieldRow { label: "Time limit"
                               Num { width: 100; value: page.limit; from: 1; to: 3600; onChanged: function (v) { page.limit = v } }
                               Txt { text: "seconds. Over it, the run is ended and counted as timed out."; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter } }
                    Rectangle { width: parent.width; height: 1; color: Theme.border }
                    Row {
                        anchors.right: parent.right
                        spacing: 8
                        Btn { text: "Cancel"; onClicked: Nav.go("actions", page.editId || null) }
                        Btn { text: "Test on one machine"; enabled: false; tip: "The Engine runs only saved actions: save it, then run it on one machine from Actions" }
                        Btn { kind: "primary"; enabled: page.ready; text: page.editId ? "Save changes" : "Save action"; onClicked: page.save() }
                    }
                }
            }
            Panel {
                id: checks
                width: (parent.width - 14) * 4 / 12
                Column {
                    width: parent.width
                    spacing: 12
                    Txt { text: "CHECKED AS YOU TYPE"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                    readonly property var probs: page.chk ? (page.chk.problems || []) : []
                    readonly property var compileProbs: probs.filter(function (p) { return !/import|module/i.test(p) })
                    readonly property var importProbs: probs.filter(function (p) { return /import|module/i.test(p) })
                    Row { spacing: 8; width: parent.width
                          Icon { name: parent.parent.compileProbs.length ? "closecircle" : "checkcircle"; size: 15; color: parent.parent.compileProbs.length ? Theme.crit : Theme.ok }
                          Txt { width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: parent.parent.compileProbs.length ? "Does not compile: " + parent.parent.compileProbs[0] : "Compiles" } }
                    Row { spacing: 8; width: parent.width
                          Icon { name: parent.parent.importProbs.length ? "closecircle" : "checkcircle"; size: 15; color: parent.parent.importProbs.length ? Theme.crit : Theme.ok }
                          Column { width: parent.width - 24
                                   Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: parent.parent.parent.importProbs.length ? "Not allowed: " + parent.parent.parent.importProbs.join("; ") : "Only standard and Windows-native imports" }
                                   Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12; text: page.used.length ? "Uses " + page.used.join(", ") : "No imports" } } }
                    Rectangle {
                        width: parent.width; height: wn.height + 20; radius: 6
                        color: Theme.alpha(Theme.med, 0.09); border.width: 1; border.color: Theme.alpha(Theme.med, 0.35)
                        Txt { id: wn; x: 10; y: 10; width: parent.width - 20; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                              text: "Runs without a sandbox, with the worker client's rights. It is checked again on each machine when it arrives, and every run and its output are recorded." }
                    }
                }
            }
        }
    }
}
