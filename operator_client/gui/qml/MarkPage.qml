import QtQuick
import "."

// MARK FILES. Marking is one decision with one setting, so it is a page of its own, not steps: your
// PC's folders on the left with room to browse; what you ticked, and where it may be, on the right.
// Only what the file index has seen is listed; only your own files can be marked.
Page {
    id: page
    objectName: "markFiles"
    bare: true

    property var folders: []
    property var checked: []
    property string keep: "machine"
    property string q: ""
    property string host: ""

    property bool eng: false              // marks.tree answered: the Engine marks files and folders where they are
    property bool busy: false
    Component.onCompleted: falcon.call("marks.tree", {}, function (ok, r) {
        if (ok && r && r.folders) {
            page.eng = true
            page.host = r.hostname || ""
            page.folders = r.folders.map(function (f) { var parts = f.path.split(/[\\\/]/).filter(function (x) { return x }); return { path: f.path, name: parts.length ? parts[parts.length - 1] : f.path, files: f.files } })
            return
        }
        falcon.call("index.folders", { pc_id: falcon.pcId }, function (ok2, r2) {
            page.folders = ok2 ? (r2.folders || []) : []
            page.host = ok2 ? (r2.hostname || "") : ""
        })
    })
    function mark() {
        busy = true
        falcon.call("marks.create", { paths: checked, keep: keep }, function (ok, r) {
            page.busy = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not marked"); return }
            var n = r.copies_found || 0
            Msg.ok(Theme.many((r.marks || []).length, "mark") + " made" + (n ? " · " + Theme.many(n, "copy") + " found elsewhere already" : " · no copy anywhere else"))
            Nav.go("restricted")
        })
    }
    // the folders as a tree: each with its depth, the path segments it is under
    readonly property var tree: folders.slice().sort(function (a, b) { return a.path.localeCompare(b.path) })
        // indented under the folders that are listed, and named from the nearest of them: the index lists
        // only folders with files, so C:/Shared/Templates can come without C:/Shared
        .map(function (f, i, all) {
            var p = f.path.replace(/\\/g, "/"), up = all.filter(function (a) { return p.indexOf(a.path.replace(/\\/g, "/") + "/") === 0 })
            var near = up.length ? up[up.length - 1].path.replace(/\\/g, "/") : ""
            return Object.assign({}, f, { depth: up.length, name: near ? p.slice(near.length + 1) : p })
        })
        .filter(function (f) { return q === "" || f.path.toLowerCase().indexOf(q.toLowerCase()) >= 0 })
    readonly property var picked: folders.filter(function (f) { return page.checked.indexOf(f.path) >= 0 })
    readonly property int nFiles: picked.reduce(function (a, f) { return a + (f.files || 0) }, 0)
    function toggle(p) { var c = checked.slice(), i = c.indexOf(p); if (i >= 0) c.splice(i, 1); else c.push(p); checked = c }

    EditorShell {
        width: parent.width
        problem: !page.picked.length ? "Tick at least one folder." : !page.eng ? "This Engine marks single indexed files only; folder marks need its marks.* handlers." : page.busy ? "Marking…" : ""
        onSave: page.mark()
        note: "Nothing is moved or copied."
        saveLabel: "Mark restricted"
        onCancel: Nav.go("restricted")
        leftPane: Panel {
            width: parent.width
            height: 620
            fill: true
            flush: true
            title: page.host ? "Files on " + page.host : "Files on your PC"
            sub: "your PC · tick what to mark"
            extra: SearchBox { placeholderText: "Find a folder"; onTextChanged: page.q = text }
            Flickable {
                anchors.fill: parent
                anchors.bottomMargin: 40
                contentHeight: tcol.height + 16
                clip: true
                Column {
                    id: tcol
                    x: 10; y: 8
                    width: parent.width - 20
                    Txt { visible: page.folders.length === 0; text: "Nothing indexed on this PC yet. Its folders appear after the machine's next idle sweep."; color: Theme.text3; wrapMode: Text.WordWrap; width: parent.width; elide: Text.ElideNone }
                    Repeater {
                        model: page.tree
                        Rectangle {
                            required property var modelData
                            width: tcol.width
                            height: 28
                            radius: 4
                            color: ta.containsMouse ? Theme.surface2 : "transparent"
                            Row {
                                x: 6 + modelData.depth * 20
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 8
                                Check { controlled: true; checked: page.checked.indexOf(modelData.path) >= 0; onToggled: page.toggle(modelData.path); anchors.verticalCenter: parent.verticalCenter }
                                Icon { name: "folder"; size: 14; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: modelData.name; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: Theme.fmt(modelData.files || 0) + " files"; color: Theme.text4; font.pixelSize: 11; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                            }
                            MouseArea { id: ta; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                        }
                    }
                }
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 40
                color: "transparent"
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Txt { x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 28; color: Theme.text3; font.pixelSize: 12
                      text: "Only what the file index has seen is listed. Only your own files can be marked: what is on someone else's machine is theirs to mark." }
            }
        }
        rightPane: Panel {
            width: parent.width
            flush: true
            title: "To mark"
            sub: page.picked.length ? Theme.many(page.picked.length, "folder") + ", " + Theme.fmt(page.nFiles) + " files in all" : "nothing ticked yet"
            Column {
                width: parent.width
                Txt { visible: page.picked.length === 0; x: 14; topPadding: 14; bottomPadding: 14; width: parent.width - 28; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: "Tick folders on the left. A folder covers everything in it, and anything added to it later." }
                Repeater {
                    model: page.picked
                    Rectangle {
                        required property var modelData
                        width: parent.width; height: 48; color: "transparent"
                        Icon { x: 14; anchors.verticalCenter: parent.verticalCenter; name: "folder"; size: 14; color: Theme.text3 }
                        Column { x: 38; width: parent.width - 150; anchors.verticalCenter: parent.verticalCenter
                                 Txt { text: modelData.name; font.weight: Font.Medium; width: parent.width }
                                 Txt { text: modelData.path; mono: true; color: Theme.text3; font.pixelSize: 11; width: parent.width } }
                        Txt { anchors.right: rm.left; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; text: Theme.fmt(modelData.files || 0) + " files"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                        Btn { id: rm; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; small: true; kind: "text"; iconName: "close"; onClicked: page.toggle(modelData.path) }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Column {
                    x: 14
                    width: parent.width - 28
                    topPadding: 14; bottomPadding: 14
                    spacing: 8
                    Txt { text: "WHERE THEY ARE ALLOWED"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                    Choice { width: parent.width; on: page.keep === "machine"; icon: "desktop"; title: "Only on your PC"; desc: "Moving or copying on it is fine. A copy on any other machine is caught."; onClicked: page.keep = "machine" }
                    Choice { width: parent.width; on: page.keep === "path"; icon: "aim"; title: "Only where it is now"; desc: "A copy anywhere else is caught, even elsewhere on your PC."; onClicked: page.keep = "path" }
                }
            }
        }
    }
}
