import QtQuick
import "."

// MARK FILES. Marking is one decision with one setting, so it is a page of its own, not steps: your
// PC's files on the left with room to browse; what you ticked, and where it may be, on the right.
// Only what the file index has seen is listed; only your own files can be marked.
//
// The left is the concept's tree: drives, folders and files from marks.tree, the drives and their first folders
// open. A file or a folder can be ticked; ticking a folder does not tick what is in it (it covers it). What is
// marked already is drawn faint with its tag, and what a marked folder covers says so; neither can be ticked.
Page {
    id: page
    objectName: "markFiles"
    bare: true

    property var files: []                // marks.tree's files: [{path, name, marked, covered_by}]
    property var folderMarks: []          // your folder marks on this PC (marks.list): their paths
    property var checked: []              // node keys
    property var open: ({})               // node key -> open; unset falls back to the default (drives and their first folders)
    property string keep: "machine"
    property string q: ""
    property string host: ""
    property bool loaded: false

    property bool busy: false
    Component.onCompleted: {
        falcon.call("marks.tree", {}, function (ok, r) {
            page.loaded = true
            page.files = ok && r ? r.files || [] : []
            page.host = ok && r ? r.hostname || "" : ""
            if (ok && r) falcon.call("marks.list", { scope: "mine" }, function (ok2, r2) {
                page.folderMarks = ok2 ? (r2.marks || []).filter(function (k) { return k.kind === "folder" && k.pc_id === r.pc_id }).map(function (k) { return page.norm(k.path) }) : []
            })
        })
    }
    function norm(p) { return String(p).replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase() }

    // the tree: every file under its drive and folders. A folder's path keeps the spelling its files have, so the
    // Engine finds it in the index as it is.
    readonly property var tree: {
        var roots = [], byKey = {}
        function node(key, path, name, depth, leaf, parent) {
            var n = byKey[key]
            if (n) return n
            n = { key: key, path: path, name: name, depth: depth, leaf: leaf, kids: [], own: false, under: false, n: 0 }
            byKey[key] = n
            ;(parent ? parent.kids : roots).push(n)
            return n
        }
        files.forEach(function (f) {
            var raw = String(f.path), sep = raw.indexOf("\\") >= 0 ? "\\" : "/"
            var parts = raw.split(/[\\\/]/).filter(function (x) { return x !== "" })
            var parent = null, at = ""
            for (var i = 0; i < parts.length; i++) {
                at = i ? at + sep + parts[i] : parts[i]
                var leaf = i === parts.length - 1
                var n = node(norm(at) + (leaf ? "" : "/"), at, parts[i], i, leaf, parent)
                if (leaf) { n.own = f.marked !== null && f.marked !== undefined; n.under = f.covered_by !== null && f.covered_by !== undefined && !n.own }
                parent = n
            }
        })
        // folders: their file counts, and whether a folder mark is on them or above them
        function walk(n, coveredAbove) {
            if (n.leaf) { n.n = 1; if (coveredAbove) n.under = !n.own; return 1 }
            n.own = page.folderMarks.indexOf(norm(n.path)) >= 0
            n.under = coveredAbove && !n.own
            n.kids.sort(function (a, b) { return a.leaf === b.leaf ? a.name.localeCompare(b.name) : a.leaf ? -1 : 1 })
            n.n = n.kids.reduce(function (s, k) { return s + walk(k, coveredAbove || n.own) }, 0)
            return n.n
        }
        roots.sort(function (a, b) { return a.name.localeCompare(b.name) })
        roots.forEach(function (r) { walk(r, false) })
        return { roots: roots, byKey: byKey }
    }
    function isOpen(n) { return open[n.key] !== undefined ? open[n.key] : n.depth <= 1 }
    function flip(n) { var o = Object.assign({}, open); o[n.key] = !isOpen(n); open = o }
    // the rows to draw: open folders show what is in them; a search keeps every match and the folders leading to it
    readonly property var rows: {
        var out = [], needle = q.trim().toLowerCase()
        function hit(n) { return n.name.toLowerCase().indexOf(needle) >= 0 || n.kids.some(hit) }
        function add(n) {
            if (needle && !hit(n)) return
            out.push(n)
            if (!n.leaf && (needle || isOpen(n))) n.kids.forEach(add)
        }
        tree.roots.forEach(add)
        return out
    }
    readonly property var picked: checked.map(function (k) { return page.tree.byKey[k] }).filter(function (x) { return !!x })
    readonly property int nDirs: picked.filter(function (x) { return !x.leaf }).length
    readonly property int nFiles: picked.reduce(function (a, x) { return a + x.n }, 0)
    function toggle(k) { var c = checked.slice(), i = c.indexOf(k); if (i >= 0) c.splice(i, 1); else c.push(k); checked = c }

    // what marking would cost, asked of the Engine before anything is done (files, how long, whether it is too large): so a folder like node_modules is met with a reason, not a surprise
    property var assessed: []
    property bool confirmLarge: false
    readonly property bool tooLarge: assessed.some(function (a) { return a.verdict === "too_large" })
    readonly property bool large: assessed.some(function (a) { return a.verdict === "large" })
    readonly property real seconds: assessed.reduce(function (t, a) { return t + (a.seconds || 0) }, 0)
    onPickedChanged: { confirmLarge = false; if (!picked.length) assessed = []; else assessTimer.restart() }
    Timer { id: assessTimer; interval: 350; onTriggered: page.runAssess() }
    function runAssess() {
        var want = picked.map(function (x) { return x.path })
        falcon.call("marks.assess", { paths: want }, function (ok, r) { if (ok && r && page.picked.length === want.length) page.assessed = r.assessed || [] })
    }
    function span(sec) { return sec < 60 ? "under a minute" : sec < 5400 ? "about " + Math.round(sec / 60) + " minutes" : "about " + (sec / 3600).toFixed(1) + " hours" }

    function mark() {
        busy = true
        falcon.call("marks.create", { paths: picked.map(function (x) { return x.path }), keep: keep, confirm_large: confirmLarge }, function (ok, r) {
            page.busy = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not marked"); return }
            var n = r.copies_found || 0
            Msg.ok("Marked " + (page.picked.length === 1 ? page.picked[0].name : page.picked.length + " items") + " restricted · nothing was moved"
                   + (n ? " · " + Theme.many(n, "copy") + " found elsewhere already" : ""))
            Nav.go("restricted")
        })
    }

    EditorShell {
        width: parent.width
        problem: !page.picked.length ? "Tick at least one file or folder." : page.tooLarge ? "Too large to mark as it is: the reasons are on the right." : page.large && !page.confirmLarge ? "This is large: tick the box on the right to go ahead." : page.busy ? "Marking…" : ""
        onSave: page.mark()
        note: "Nothing is moved or copied."
        saveLabel: "Mark restricted"
        onCancel: Nav.go("restricted")
        leftPane: Panel {
            width: parent.width
            height: 660
            fill: true
            flush: true
            title: page.host ? "Files on " + page.host : "Files on your PC"
            sub: "your PC · tick what to mark"
            extra: SearchBox { width: 240; placeholderText: "Find a file or folder"; onTextChanged: page.q = text }
            Flickable {
                anchors.fill: parent
                anchors.bottomMargin: foot.height
                contentHeight: tcol.height + 16
                clip: true
                Column {
                    id: tcol
                    x: 10; y: 8
                    width: parent.width - 20
                    Txt { visible: page.loaded && page.files.length === 0; text: "Nothing indexed on this PC yet. Its files appear after the machine's next idle sweep."; color: Theme.text3; wrapMode: Text.WordWrap; width: parent.width; elide: Text.ElideNone; padding: 8 }
                    Txt { visible: page.files.length > 0 && page.rows.length === 0; text: "Nothing on " + (page.host || "your PC") + " matches “" + page.q + "”."; color: Theme.text3; width: parent.width; padding: 8 }
                    Repeater {
                        model: page.rows
                        Rectangle {
                            required property var modelData
                            readonly property bool off: modelData.own || modelData.under
                            width: tcol.width
                            height: 28
                            radius: 4
                            color: ta.containsMouse ? Theme.surface2 : "transparent"
                            Row {
                                x: 6 + modelData.depth * 24
                                height: parent.height
                                spacing: 8
                                Item { width: 14; height: parent.height
                                       Icon { visible: !modelData.leaf; anchors.centerIn: parent; name: modelData.leaf ? "" : page.q.trim() || page.isOpen(modelData) ? "caretd" : "caretr"; size: 12; color: Theme.text2 }
                                       MouseArea { enabled: !modelData.leaf; anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.flip(modelData) } }
                                Check { controlled: true; enabled: !parent.parent.off; checked: page.checked.indexOf(modelData.key) >= 0; onToggled: page.toggle(modelData.key); anchors.verticalCenter: parent.verticalCenter }
                                Icon { name: modelData.leaf ? "file" : "folder"; size: 14; color: parent.parent.off ? Theme.text4 : Theme.text2; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: modelData.name; mono: modelData.leaf; color: parent.parent.off ? Theme.text4 : Theme.text; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                                Txt { visible: !modelData.leaf; text: Theme.fmt(modelData.n) + (modelData.n === 1 ? " file" : " files"); color: Theme.text4; font.pixelSize: 11; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                                Tag { visible: modelData.own; text: "marked"; c: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
                                Txt { visible: modelData.under; text: "covered by its folder"; color: Theme.text4; font.pixelSize: 11; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                            }
                            MouseArea { id: ta; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                        }
                    }
                }
            }
            Rectangle {
                id: foot
                anchors.bottom: parent.bottom
                width: parent.width
                height: footText.implicitHeight + 20
                color: "transparent"
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Txt { id: footText; x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 28; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                      text: "Only what the file index has seen is listed; the rest appears after the machine's next idle sweep. Only your own files can be marked: what is on someone else's machine is theirs to mark." }
            }
        }
        rightPane: Panel {
            width: parent.width
            flush: true
            title: "To mark"
            sub: page.picked.length ? (page.nDirs ? Theme.many(page.nDirs, "folder") + " and " : "") + (page.picked.length - page.nDirs ? Theme.many(page.picked.length - page.nDirs, "file") + ", " : "") + Theme.fmt(page.nFiles) + " files in all"
                                    : "nothing ticked yet"
            Column {
                width: parent.width
                Txt { visible: page.picked.length === 0; x: 14; topPadding: 14; bottomPadding: 14; width: parent.width - 28; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: "Tick files or folders on the left. A folder covers everything in it, and anything added to it later." }
                Repeater {
                    model: page.picked
                    Rectangle {
                        required property var modelData
                        width: parent.width; height: 48; color: "transparent"
                        Icon { x: 14; anchors.verticalCenter: parent.verticalCenter; name: modelData.leaf ? "file" : "folder"; size: 14; color: Theme.text3 }
                        Column { x: 38; width: parent.width - 150; anchors.verticalCenter: parent.verticalCenter
                                 Txt { text: modelData.name; font.weight: Font.Medium; width: parent.width }
                                 Txt { text: modelData.path; mono: true; color: Theme.text3; font.pixelSize: 11; width: parent.width } }
                        Txt { anchors.right: rm.left; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; text: modelData.leaf ? "1 file" : Theme.fmt(modelData.n) + " files"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                        Btn { id: rm; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; small: true; kind: "text"; iconName: "close"; onClicked: page.toggle(modelData.key) }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Column {
                    x: 14
                    width: parent.width - 28
                    topPadding: 14; bottomPadding: 14
                    spacing: 8
                    Txt { text: page.picked.length === 1 ? "WHERE IT IS ALLOWED" : "WHERE THEY ARE ALLOWED"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                    Choice { width: parent.width; on: page.keep === "machine"; icon: "desktop"; title: "Only on your PC"; desc: "Moving or copying on it is fine. A copy on any other machine is caught."; onClicked: page.keep = "machine" }
                    Choice { width: parent.width; on: page.keep === "path"; icon: "aim"; title: "Only where it is now"; desc: "A copy anywhere else is caught, even elsewhere on your PC."; onClicked: page.keep = "path" }
                }
                Rectangle { visible: page.assessed.length > 0; width: parent.width; height: 1; color: Theme.border }
                Column {
                    objectName: "markAssess"
                    visible: page.assessed.length > 0
                    x: 14
                    width: parent.width - 28
                    topPadding: 14; bottomPadding: 14
                    spacing: 8
                    Txt { text: "WHAT MARKING COSTS"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                    Repeater {
                        model: page.assessed
                        Column {
                            required property var modelData
                            width: parent.width
                            spacing: 3
                            Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.weight: Font.Medium
                                  color: modelData.verdict === "too_large" ? Theme.crit : modelData.verdict === "large" ? Theme.med : Theme.text
                                  text: (modelData.verdict === "too_large" ? "Too large · " : modelData.verdict === "large" ? "Large · " : "") + Theme.fmt(modelData.tracked) + (modelData.tracked === 1 ? " file" : " files")
                                        + " tracked" + (modelData.junk ? " · " + Theme.fmt(modelData.junk) + " generated, covered but not tracked" : "") + " · " + page.span(modelData.seconds || 0) }
                            Repeater {
                                model: modelData.reasons || []
                                Txt { required property string modelData; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12; text: modelData }
                            }
                        }
                    }
                    Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text4; font.pixelSize: 11
                          text: page.assessed.length && page.assessed[0].basis ? "The time is " + page.assessed[0].basis + (page.assessed[0].capacity ? "; the Engine is " + page.assessed[0].capacity.state + " now." : ".") : "" }
                    Check { objectName: "markConfirmLarge"; visible: page.large && !page.tooLarge; controlled: true; checked: page.confirmLarge; text: "I understand: this will take " + page.span(page.seconds); onToggled: function (on) { page.confirmLarge = on } }
                }
            }
        }
    }
}
