import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import "."

// WRITE AN ACTION (and Edit the script), the concept's ActionNew: what it is; the script, checked as it is typed with the same check the
// Engine and each machine run on it; then a real test on one machine, the time limit, and saving. It runs without a sandbox, so that is said beside it.
Editor {
    id: page
    objectName: "newAction"
    readonly property int editId: Nav.sub && String(Nav.sub).indexOf("edit-") === 0 ? Number(String(Nav.sub).slice(5)) : 0
    drawerTitle: editId ? "Edit " + name : "Write an action"
    drawerNote: "nothing is saved until you confirm"
    names: ["What it is", "The script", "Try it and save"]
    nameNow: name
    confirmText: editId ? "Save changes" : "Add the action"

    property string name: ""
    property string desc: ""
    property string eff: ""                     // what it reports: text | list | status
    property string lang: "python"
    property string src: ""
    property string file: ""
    property int limit: 60
    property var taken: []
    property var by: null
    property string host: ""
    property var test: null                     // { st: run | done, src, host, exec, lines, sec, ok }
    readonly property var tpl: ({ python: "import os\n\n# write what the action does\nprint(os.environ[\"COMPUTERNAME\"])\n", powershell: "$name = $env:COMPUTERNAME\n\n# write what the action does\nWrite-Output $name\n" })

    Component.onCompleted: falcon.call("control.action_list", {}, function (ok, r) {
        var a = ok ? (r.actions || {}) : {}, all = (a.control || []).concat(a.monitoring || [], a.custom || [])
        page.taken = all.filter(function (x) { return x.id !== page.editId }).map(function (x) { return String(x.name).toLowerCase() })
        var c = page.editId ? (a.custom || []).filter(function (x) { return x.id === page.editId })[0] : null
        if (!c) return
        page.name = c.name; page.desc = c.description || ""; page.lang = c.custom_script_language || "python"; page.src = c.custom_script || ""
        page.limit = c.timeout_seconds || 60; page.eff = c.output_kind || "text"; page.by = c.created_by_name || null
    })
    readonly property var pcs: (myPc ? [myPc] : []).concat(Fleet.machines)
    readonly property var myPc: {
        for (var i = 0; i < Fleet.depts.length; i++) for (var j = 0; j < (Fleet.depts[i].admins || []).length; j++) {
            var a = Fleet.depts[i].admins[j]
            if (a.account_id === falcon.accountId && a.pc_id) return { pc_id: a.pc_id, host: a.hostname || "", online: true, user: a.name }
        }
        return null
    }
    readonly property string hostNow: host || (myPc ? myPc.host : (Fleet.machines[0] || { host: "" }).host)
    readonly property var chk: src.trim() ? falcon.validateScript(lang, src) : null
    readonly property var probs: chk ? (chk.problems || []) : []
    readonly property var compileProbs: probs.filter(function (p) { return !/import|module/i.test(p) })
    readonly property var importProbs: probs.filter(function (p) { return /import|module/i.test(p) })
    readonly property var used: {
        var out = [], re = lang === "python" ? /^\s*(?:import\s+([\w.]+(?:\s*,\s*[\w.]+)*)|from\s+([\w.]+)\s+import)/gm : /Import-Module\s+([\w.\-]+)/gi, m
        while ((m = re.exec(src)) !== null) (m[1] ? m[1].split(",") : [m[2]]).forEach(function (x) { if (x) { var n = x.trim().split(".")[0]; if (out.indexOf(n) < 0) out.push(n) } })
        return out
    }
    function isBad(u) { return importProbs.some(function (p) { return p.indexOf(u) >= 0 }) }
    readonly property bool dup: taken.indexOf(name.trim().toLowerCase()) >= 0
    readonly property string fname: file || ((name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "script") + (lang === "python" ? ".py" : ".ps1"))
    readonly property int lines: src.split("\n").length
    prob: step === 0 && !name.trim() ? "Give it a name." : step === 0 && dup ? "Another action already has that name." : step === 0 && !eff ? "Say what it reports back."
          : step === 1 && !src.trim() ? "Write the script, or upload one." : step === 1 && compileProbs.length ? "The script does not compile yet."
          : step === 1 && importProbs.length ? importProbs[0] : ""
    readonly property string effWord: eff === "list" ? "reports a list" : eff === "status" ? "reports only whether it worked" : eff === "text" ? "reports text" : ""
    readonly property string limitWord: limit < 60 ? limit + "s" : Math.floor(limit / 60) + "m" + (limit % 60 ? " " + (limit % 60) + "s" : "")
    readonly property string langWord: lang === "python" ? "Python" : "PowerShell"

    function readIn(url) {
        var p = String(url).replace(/^file:\/\/\//, "").replace(/^file:\/\//, ""), ext = p.split(".").pop().toLowerCase()
        if (ext !== "py" && ext !== "ps1") { Msg.warn("Only a .py or .ps1 file"); return }
        src = falcon.readFile(decodeURIComponent(p)); lang = ext === "py" ? "python" : "powershell"; file = p.split("/").pop(); test = null
    }
    function runTest() {
        var m = pcs.filter(function (x) { return x.host === page.hostNow })[0]
        if (!m) return
        var s0 = src
        test = { st: "run", src: s0, host: m.host, exec: 0, t0: Time.now }
        falcon.call("control.action_try", { language: lang, script: src, pc_id: m.pc_id, timeout_s: limit, output_kind: eff || "text", name: name.trim() || undefined }, function (ok, r) {
            if (!ok) { page.test = null; Msg.failed(r && r.message ? r.message : "Not run"); return }
            page.test = Object.assign({}, page.test, { exec: r.execution_id }); poll.start()
        })
    }
    Timer {
        id: poll; interval: 1000; repeat: true
        onTriggered: {
            if (!page.test || page.test.st !== "run") { stop(); return }
            var id = page.test.exec
            falcon.call("control.execution", { execution_id: id }, function (ok, r) {
                if (!ok || !r.execution || r.execution.status === "pending" || !page.test || page.test.exec !== id) return
                var o = Auto.outcome(r.execution)
                page.test = Object.assign({}, page.test, { st: "done", lines: r.output || [], ok: o === "Success", word: o === "Success" ? "worked" : o === "Timed out" ? "ran out of time" : "failed",
                                                           exit: r.execution.exit_code || 0, sec: Math.max(1, Math.round((Time.now - page.test.t0) / 1000)) })
                poll.stop()
            })
        }
    }
    onConfirmed: {
        var p = editId ? { action_id: editId, name: name.trim(), description: desc.trim(), script: src, timeout_s: limit, output_kind: eff }
                       : { kind: "custom", name: name.trim(), description: desc.trim(), language: lang, script: src, timeout_s: limit, output_kind: eff }
        falcon.call(editId ? "control.action_update" : "control.action_create", p, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not saved"); return }
            Msg.ok(editId ? name.trim() + " saved" : name.trim() + " added to Custom")
            Nav.go("actions", page.editId || (r.action ? r.action.id : null))
        })
    }
    FileDialog { id: pick; nameFilters: ["Scripts (*.py *.ps1)"]; onAccepted: page.readIn(selectedFile) }

    head: Txt {
        width: parent.width; color: Theme.text3; font.pixelSize: 13
        text: [page.desc.trim(), "Custom · " + page.langWord, page.effWord].filter(function (x) { return x }).join(" · ")
    }

    // --- what it is ---------------------------------------------------------------------------------------------------------------
    NfSec { visible: page.step === 0; first: true; title: "What do you call it?"; note: "How it shows in Your actions, in a rule's actions, and in every run."
        Field { width: parent.width; text: page.name; placeholderText: "For example Clear the print queue"; maximumLength: 60; onTextEdited: page.name = text } }
    NfSec { visible: page.step === 0; title: "What does it do?"; optional: "optional"; note: "One plain line, shown under the name. Leave it empty if the name says it all."
        Field { width: parent.width; text: page.desc; placeholderText: "For example Stops the spooler, empties the queue, starts it again."; maximumLength: 120; onTextEdited: page.desc = text } }
    NfSec { visible: page.step === 0; title: "What does it report back?"; note: "This is how its output is shown when you open a run."
        NfPick { title: "Text"; desc: "What it prints is shown as it is, like a console. The first line is the summary."; on: page.eff === "text"; onPicked: page.eff = "text" }
        NfPick { title: "A list"; desc: "Each line it prints is a row, and a tab splits the columns: files, programs, users. The summary counts the rows."; on: page.eff === "list"; onPicked: page.eff = "list" }
        NfPick { title: "Only whether it worked"; desc: "It prints nothing worth keeping. Exit 0 counts as worked, anything else as failed."; on: page.eff === "status"; onPicked: page.eff = "status" } }

    // --- the script ---------------------------------------------------------------------------------------------------------------
    NfSec {
        visible: page.step === 1; first: true
        Rectangle {
            width: parent.width
            height: edh.height + (page.src ? Math.max(460, code.contentH) : 460)
            radius: 8
            color: Theme.surface2
            clip: true
            border.width: 1
            border.color: over.containsDrag ? Theme.accent : Theme.borderStrong
            DropArea { id: over; anchors.fill: parent; onDropped: function (d) { if (d.hasUrls) page.readIn(d.urls[0]) } }
            Rectangle {
                id: edh
                x: 1; y: 1
                width: parent.width - 2; height: 41; radius: 7
                color: Theme.surface
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
                Row {
                    x: 10; anchors.verticalCenter: parent.verticalCenter
                    spacing: 12
                    Segmented { options: [{ value: "python", label: "Python" }, { value: "powershell", label: "PowerShell" }]; value: page.lang; onPicked: function (v) { page.lang = v; page.test = null } }
                    Txt { anchors.verticalCenter: parent.verticalCenter; text: page.fname; mono: true; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    Txt { visible: page.src !== ""; anchors.verticalCenter: parent.verticalCenter; text: Theme.many(page.lines, "line"); color: Theme.text4; font.pixelSize: 12; elide: Text.ElideNone }
                }
                Btn { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; small: true; iconName: "upload"; text: page.file ? "Upload another" : "Upload a file"; onClicked: pick.open() }
            }
            // what was written, with its line numbers
            Item {
                id: code
                visible: page.src !== ""
                y: edh.height + 1
                width: parent.width
                readonly property real lineH: ta.lineCount > 0 ? ta.contentHeight / ta.lineCount : 20
                readonly property real contentH: ta.contentHeight + 24
                height: parent.height - y
                Rectangle { width: gut.width + 24; height: parent.height; color: "transparent"; Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.border } }
                Column {
                    id: gut
                    x: 14; y: 12
                    width: Math.max(14, String(page.lines).length * 8)
                    Repeater { model: page.lines
                        Txt { required property int index; width: gut.width; height: code.lineH; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter; text: index + 1; mono: true; color: Theme.text4; elide: Text.ElideNone } }
                }
                TextArea {
                    id: ta
                    x: gut.width + 24; y: 0
                    width: parent.width - x; height: parent.height
                    text: page.src
                    font.family: Theme.mono; font.pixelSize: 13
                    color: Theme.text
                    wrapMode: TextEdit.NoWrap
                    selectByMouse: true
                    selectionColor: Theme.alpha(Theme.accent, 0.3)
                    tabStopDistance: 28
                    leftPadding: 14; rightPadding: 14; topPadding: 12; bottomPadding: 12
                    background: null
                    onTextChanged: if (text !== page.src) page.src = text
                }
            }
            // nothing yet: drop one, upload one, or start blank
            Column {
                visible: page.src === ""
                anchors.centerIn: parent; anchors.verticalCenterOffset: edh.height / 2
                spacing: 8
                Icon { anchors.horizontalCenter: parent.horizontalCenter; name: "filetext"; size: 26; color: Theme.text4 }
                Txt { anchors.horizontalCenter: parent.horizontalCenter; text: "Drop a .py or .ps1 file here"; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideNone }
                Txt { anchors.horizontalCenter: parent.horizontalCenter; text: "or upload one, or start writing from a blank script"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 8
                    Btn { small: true; text: "Upload a file"; onClicked: pick.open() }
                    Btn { small: true; text: "Blank Python"; onClicked: { page.lang = "python"; page.src = page.tpl.python } }
                    Btn { small: true; text: "Blank PowerShell"; onClicked: { page.lang = "powershell"; page.src = page.tpl.powershell } }
                }
            }
        }
    }
    NfSec {
        visible: page.step === 1 && page.src.trim() !== ""; title: "Checked as you type"
        component Cr: Item {
            id: cr
            property var state2: null                 // true: fine; false: wrong; null: to know
            property string title: ""
            property string line: ""
            default property alias more: cc.data
            width: parent ? parent.width : 0
            height: cc.height + 19
            Rectangle { y: 9; width: 22; height: 22; radius: 11
                        color: cr.state2 === true ? Theme.mix(Theme.ok, Theme.surface3, 0.20) : cr.state2 === false ? Theme.mix(Theme.crit, Theme.surface3, 0.22) : Theme.surface3
                        Icon { anchors.centerIn: parent; name: cr.state2 === true ? "check" : cr.state2 === false ? "close" : "infocircle"; size: 11; color: cr.state2 === true ? Theme.ok : cr.state2 === false ? Theme.crit : Theme.text3 } }
            Column { id: cc; x: 34; y: 9; width: parent.width - 34; spacing: 3
                Txt { width: parent.width; text: cr.title; font.pixelSize: 13; font.weight: Font.DemiBold; color: cr.state2 === false ? Theme.crit : Theme.text }
                Txt { visible: cr.line !== ""; width: parent.width; text: cr.line; color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone } }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
        }
        Cr { state2: page.compileProbs.length === 0; title: page.compileProbs.length ? "It does not compile yet" : "It compiles"; line: page.compileProbs.length ? "a bracket or block is not closed" : "" }
        Cr {
            state2: page.importProbs.length === 0; title: page.importProbs.length ? "It imports something not allowed" : "Its imports are allowed"
            line: (page.lang === "python" ? "Only Python's standard library and what Windows has (winreg, msvcrt)." : "Only the modules a stock Windows install has.") + " Nothing can be installed."
            Flow {
                width: parent.width; spacing: 6
                Repeater { model: page.used
                    Rectangle { required property var modelData; readonly property bool bad: page.isBad(modelData); width: iw.implicitWidth + 16; height: iw.implicitHeight + 4; radius: 5
                                color: bad ? Theme.mix(Theme.crit, Theme.surface3, 0.18) : Theme.mix(Theme.ok, Theme.surface3, 0.14)
                                Txt { id: iw; anchors.centerIn: parent; text: parent.modelData; mono: true; font.pixelSize: 12; color: parent.bad ? Theme.crit : Theme.ok; elide: Text.ElideNone } } }
                Txt { visible: page.used.length === 0; text: "it imports nothing"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
            }
        }
        Cr { title: "Checked again on each machine"; line: "the worker client runs the same checks when the script arrives, so a script changed on the way is refused" }
        Cr { title: "No sandbox"; line: "it runs with the worker client's rights; every run is recorded with your name as its author" }
        Cr { title: "What it prints is kept"; line: "with the run, for 90 days; the first line becomes its summary. Exit 0 counts as worked, anything else as failed" }
    }

    // --- try it and save ----------------------------------------------------------------------------------------------------------
    NfSec {
        visible: page.step === 2; first: true; title: "Try it on one machine"; note: "A real run: it runs there and is recorded. Your own PC is the safe place to start."
        Flow {
            width: parent.width; spacing: 8
            Repeater { model: page.pcs
                delegate: Rectangle {
                    required property var modelData
                    readonly property bool on: page.hostNow === modelData.host
                    width: Math.max(64, tn.implicitWidth + 16); height: 42; radius: 7
                    color: !modelData.online ? "transparent" : on ? Theme.mix(Theme.accent, Theme.surface3, 0.28) : Theme.surface3
                    border.width: modelData.online ? 1 : 0; border.color: ta2.containsMouse ? Theme.borderStrong : "transparent"
                    DashBox { visible: !modelData.online }
                    Txt { id: tn; anchors.centerIn: parent; text: modelData.host.replace(/^WS-/, ""); mono: true; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideNone
                          color: !modelData.online ? Theme.text4 : parent.on ? Theme.accent : Theme.text3 }
                    MouseArea { id: ta2; anchors.fill: parent; hoverEnabled: true; enabled: modelData.online; cursorShape: Qt.PointingHandCursor; onClicked: page.host = modelData.host }
                } }
        }
        Row {
            topPadding: 2
            spacing: 10
            Btn { iconName: "caretr"; loading: !!page.test && page.test.st === "run"; text: "Run a test on " + page.hostNow; onClicked: page.runTest() }
            Txt { visible: !!page.test && page.test.st === "done" && page.test.src !== page.src; anchors.verticalCenter: parent.verticalCenter; text: "the script changed since this test"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
        }
        Rectangle {
            visible: page.test !== null
            width: parent.width
            height: con.height + 24
            radius: 8
            color: Theme.surface2
            Column {
                id: con
                x: 14; y: 12
                width: parent.width - 28
                spacing: 2
                Txt { width: parent.width; mono: true; color: Theme.text4; text: page.test ? "$ " + (page.lang === "python" ? "python" : "powershell -File") + " " + page.fname + "   on " + page.test.host : "" }
                Txt { visible: !!page.test && page.test.st === "run"; mono: true; color: Theme.text3; text: "running…" }
                Txt { visible: !!page.test && page.test.st === "done" && page.eff !== "status"; width: parent.width; mono: true; wrapMode: Text.Wrap; elide: Text.ElideNone
                      color: page.test && page.test.lines && page.test.lines.length ? Theme.text : Theme.text3
                      text: page.test && page.test.lines && page.test.lines.length ? page.test.lines.join("\n") : "(it printed nothing)" }
                Txt { visible: !!page.test && page.test.st === "done"; topPadding: 6; mono: true; textFormat: Text.StyledText; color: Theme.text3
                      text: page.test ? "<font color='" + (page.test.ok ? Theme.ok : Theme.crit) + "'>" + page.test.word + "</font> · exit " + page.test.exit + " · " + page.test.sec + "s of " + page.limit + "s" : "" }
            }
        }
    }
    NfSec {
        visible: page.step === 2; title: "How long may it run?"; note: "Past this it is stopped and the run counts as out of time, not failed. You can also stop a run by hand."
        Item {
            width: parent.width; height: 40
            AntSlider { width: parent.width - 72; from: 5; to: 600; stepSize: 5; value: page.limit; marks: ["5s", "10m"]; onMoved: function (v) { page.limit = v } }
            Txt { anchors.right: parent.right; y: 2; text: page.limitWord; font.pixelSize: 15; font.weight: Font.DemiBold; elide: Text.ElideNone }
        }
    }
    NfSec {
        visible: page.step === 2
        FactRows {
            rows: [["Called", page.name.trim()]].concat(page.desc.trim() ? [["Does", page.desc.trim()]] : [],
                  [["Reports", page.eff === "list" ? "a list" : page.eff === "status" ? "only whether it worked" : "text"],
                   ["Script", page.langWord + ", " + page.lines + " lines" + (page.file ? ", from " + page.file : "")], ["Time limit", page.limit + "s"],
                   ["Tried", page.test && page.test.st === "done" ? "on " + page.test.host + ", it " + page.test.word : "not yet"], ["Written by", page.by || "you"]])
        }
    }
    Decide { visible: page.step === 2; text: "It joins Your actions under Custom when you confirm. Rules can use it, and you can run it by hand." }
}
