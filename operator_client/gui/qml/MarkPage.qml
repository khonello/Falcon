import QtQuick
import QtQuick.Dialogs
import "."

// RESTRICT SOMETHING, the concept's RestrictNew: only on this PC. The file or folder is found with a search of what the index has seen here, or picked in Explorer; then where it
// may be; then checked and restricted. What marking would cost is asked of the Engine first (marks.assess), so a folder like node_modules is met with a reason, not a surprise.
Editor {
    id: page
    objectName: "markFiles"
    drawerTitle: "Restrict something"
    drawerNote: "nothing is restricted until you confirm"
    names: ["What to restrict", "Where it may be", "Check and restrict"]
    showTop: false
    confirmText: "Restrict it"
    confirmDisabled: tooLarge || (large && !confirmLarge) || busy

    property var files: []                // marks.tree's files: [{path, name, marked, covered_by}]
    property var folders: []              // marks.tree's folders: [{path, files}]
    property var mine: []                 // the paths already restricted
    property string host: ""
    property string q: ""
    property string path: ""
    property string pkind: "file"
    property string keep: "path"
    property bool busy: false
    property var assessed: []
    property bool confirmLarge: false

    Component.onCompleted: {
        falcon.call("marks.tree", {}, function (ok, r) {
            page.files = ok && r ? r.files || [] : []
            page.folders = ok && r ? r.folders || [] : []
            page.host = ok && r ? r.hostname || "" : ""
        })
        falcon.call("marks.list", { scope: "all" }, function (ok, r) { page.mine = ok ? (r.marks || []).map(function (k) { return page.norm(k.path) }) : [] })
    }
    function norm(p) { return String(p).replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase() }
    function leaf(p) { return String(p).replace(/[\\/]+$/, "").split(/[\\/]/).pop() }
    readonly property string nm: leaf(path)
    readonly property var hits: {
        var s = q.trim().toLowerCase()
        if (!s) return []
        var fo = folders.map(function (f) { return { path: f.path, kind: "folder" } }), fi = files.map(function (f) { return { path: f.path, kind: "file" } })
        return fo.concat(fi).filter(function (x) { return x.path.toLowerCase().indexOf(s) >= 0 }).slice(0, 8)
    }
    function had(p) { return mine.indexOf(norm(p)) >= 0 }
    function take(p, k) { path = p; pkind = k; confirmLarge = false; assessed = []
                          falcon.call("marks.assess", { paths: [p] }, function (ok, r) { if (ok && r && page.path === p) page.assessed = r.assessed || [] }) }
    readonly property bool tooLarge: assessed.some(function (a) { return a.verdict === "too_large" })
    readonly property bool large: assessed.some(function (a) { return a.verdict === "large" })
    readonly property real seconds: assessed.reduce(function (t, a) { return t + (a.seconds || 0) }, 0)
    function span(sec) { return sec < 60 ? "under a minute" : sec < 5400 ? "about " + Math.round(sec / 60) + " minutes" : "about " + (sec / 3600).toFixed(1) + " hours" }
    prob: step === 0 && !path ? "Search for the file or folder, or pick it in Explorer." : step === 2 && tooLarge ? "Too large to restrict as it is." : step === 2 && large && !confirmLarge ? "This is large: tick the box to go ahead." : ""

    onConfirmed: {
        busy = true
        falcon.call("marks.create", { paths: [path], keep: keep, confirm_large: confirmLarge }, function (ok, r) {
            page.busy = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not restricted"); return }
            var n = r.copies_found || 0
            Msg.ok(page.nm + " is restricted to this PC" + (n ? " · " + Theme.many(n, "copy", "copies") + " found elsewhere already" : ""))
            Nav.go("restricted")
        })
    }
    function pickUrl(u) { return decodeURIComponent(String(u).replace(/^file:\/\/\//, "").replace(/^file:\/\//, "")).replace(/\//g, "\\") }
    FileDialog { id: fileD; onAccepted: page.take(page.pickUrl(selectedFile), "file") }

    component Hit: Rectangle {
        id: hr
        property string p: ""
        property string k: "file"
        readonly property bool on: page.path === p
        readonly property bool wasHad: page.had(p)
        width: parent ? parent.width : 0
        height: hc.height + 14
        radius: 6
        opacity: wasHad ? 0.55 : 1
        color: on ? Theme.surface3 : ha.containsMouse && !wasHad ? Theme.surface2 : "transparent"
        Icon { x: 10; anchors.verticalCenter: parent.verticalCenter; name: hr.k === "folder" ? "folder" : "file"; size: 13; color: Theme.text3 }
        Column { id: hc; x: 36; y: 7; width: parent.width - 36 - 130
            Txt { width: parent.width; text: page.leaf(hr.p); font.pixelSize: 13; font.weight: Font.DemiBold }
            Txt { width: parent.width; text: hr.p; mono: true; color: Theme.text3; font.pixelSize: 13 } }
        Txt { visible: hr.wasHad; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: "already restricted"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
        Icon { visible: hr.on && !hr.wasHad; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; name: "check"; size: 13; color: Theme.text3 }
        MouseArea { id: ha; anchors.fill: parent; hoverEnabled: true; enabled: !hr.wasHad; cursorShape: hr.wasHad ? Qt.ArrowCursor : Qt.PointingHandCursor; onClicked: page.take(hr.p, hr.k) }
    }

    // --- what to restrict -------------------------------------------------------------------------------------------------------------
    Rectangle {
        visible: page.step === 0
        width: parent.width
        height: card.height + 30
        radius: 8
        color: Theme.surface2
        Column {
            id: card
            x: 16; y: 14
            width: parent.width - 32
            spacing: 12
            Row { spacing: 10
                Icon { name: "desktop"; size: 13; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter }
                Txt { textFormat: Text.StyledText; color: Theme.text2; font.pixelSize: 13; elide: Text.ElideNone
                      text: "On <font face='" + Theme.mono + "' color='" + Theme.text + "'><b>" + page.host + "</b></font>, this PC. You restrict only what is on the machine you are at; it stays on it." } }
            Column { width: parent.width; spacing: 5
                Txt { text: "File or folder"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                Item { width: parent.width; height: Theme.control
                    Field { objectName: "markSearch"; width: parent.width - ex.width - 8; iconName: "search"; text: page.q; placeholderText: "Search this PC by name, for example payroll"; onTextEdited: page.q = text }
                    Btn { id: ex; anchors.right: parent.right; iconName: "folderopen"; text: "Pick in Explorer"; onClicked: fileD.open() } } }
            Column { visible: page.q.trim() !== ""; width: parent.width; spacing: 2
                Repeater { model: page.hits; Hit { required property var modelData; p: modelData.path; k: modelData.kind } }
                Txt { visible: page.hits.length === 0; topPadding: 8; bottomPadding: 8; leftPadding: 2; text: "Nothing on this PC by that name."; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone } }
            Column { visible: page.path !== ""; width: parent.width; spacing: 4; topPadding: 10
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Item { width: 1; height: 6 }
                Txt { text: "Picked"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                Hit { p: page.path; k: page.pkind } }
            Txt { width: parent.width; text: "A folder covers every file in it, and any added later. Files are recognised by their content, so a renamed copy is still caught."; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone }
        }
    }

    // --- where it may be ----------------------------------------------------------------------------------------------------------------
    NfSec { visible: page.step === 1; first: true; title: "Where may " + (page.nm || "it") + " be?"
        NfPick { title: "Only exactly where it is"; desc: "A copy anywhere else is caught, even in another folder on this PC."; on: page.keep === "path"; onPicked: page.keep = "path" }
        NfPick { title: "Anywhere on this PC"; desc: "It may be moved or copied around this PC; a copy on any other machine is caught."; on: page.keep === "machine"; onPicked: page.keep = "machine" } }

    // --- check and restrict ---------------------------------------------------------------------------------------------------------------
    FactRows { visible: page.step === 2
        rows: [["What", page.nm + " (" + page.pkind + ")"], ["On", page.host + ", this PC"], ["Path", page.path], ["May be", page.keep === "path" ? "only exactly where it is" : "anywhere on this PC"], ["Flows", "none may carry it until you allow one"]] }
    Decide { objectName: "markAssess"; visible: page.step === 2 && (page.large || page.tooLarge); c: Theme.med
             text: page.tooLarge ? (page.assessed.filter(function (a) { return a.verdict === "too_large" })[0].reason || "It is too large to restrict as it is.") : "This is large: reading it takes " + page.span(page.seconds) + "." }
    Check { objectName: "markConfirmLarge"; visible: page.step === 2 && page.large && !page.tooLarge; controlled: true; checked: page.confirmLarge; text: "Go ahead, it may take that long"; onToggled: function (v) { page.confirmLarge = v } }
    Decide { visible: page.step === 2; text: "Before it is restricted, every machine is checked for copies of it. Any found are listed under Copies on other machines straight away." }
}
