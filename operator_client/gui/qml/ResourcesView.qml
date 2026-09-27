import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Layouts
import "."

// RESOURCES (board RS03), reached from the Admin's home -- it has no rail entry.
//
//   top     the shelves: the tiers are folders, the access policy itself. Find a file and drop it on a shelf to
//           tag it; the shelf under it opens.
//   bottom  what is out of place (never deleted; ignored until moved, its owner told), and the chosen one said
//           in words with Ping its owner and It has moved.
//
// "Where it should be" (a file every machine must have) and "a file's journey" wait on the Engine: see
// design/ENGINE-WORK.md.
Item {
    id: root

    property var shelves: []
    property var violations: []
    property var tree: []
    property var results: []
    property int chosenId: 0
    property string hoverTag: ""
    property string clock: ""
    signal back()

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("resource.shelves", {}, function (ok, r) { if (ok) root.shelves = r.shelves })
        falcon.call("resource.violations", {}, function (ok, r) {
            if (!ok) return
            root.violations = r.violations
            if (!root.chosen && r.violations.length) root.chosenId = r.violations[0].id
        })
        falcon.call("hierarchy.tree", {}, function (ok, r) { if (ok) root.tree = r.departments })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { if (falcon.isConnected) root.refresh() }
        function onPushReceived(type, p) { if (type.indexOf("resource.") === 0 || type === "report.new") root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    onVisibleChanged: if (visible) refresh()

    readonly property string dept: tree.length === 1 ? tree[0].name : "your department"
    readonly property var chosen: { for (var i = 0; i < violations.length; i++) if (violations[i].id === chosenId) return violations[i]; return null }
    readonly property bool superUser: falcon && falcon.role === "super_user"
    function tierWord(tag) { return tag === "worker_dept" ? "Workers" : tag ? tag.charAt(0).toUpperCase() + tag.slice(1) : "" }
    function toneOf(tag) { return tag === "restricted" ? "danger" : tag === "admin" ? "warn" : tag === "worker_dept" ? "accent" : "ok" }
    function whoMay(tag) {
        if (tag === "common") return "everyone"
        if (tag === "admin") return "you alone"
        if (tag === "restricted") return superUser ? "you and the Admins" : "the Admins and the Super User"
        return "you and " + dept + (/s$/.test(dept) ? "'" : "'s") + " workers"
    }
    function person(accountId) {
        for (var i = 0; i < tree.length; i++) {
            var all = tree[i].admins.concat(tree[i].workers)
            for (var j = 0; j < all.length; j++) if (all[j].account_id === accountId) return all[j]
        }
        return null
    }
    function timeOf(iso) {
        if (!iso) return ""
        var d = new Date(iso)
        return d.toDateString() === new Date().toDateString() ? "today, " + Qt.formatDateTime(d, "HH:mm") : Qt.formatDateTime(d, "ddd d MMM")
    }
    function search(text) {
        if (text.trim().length < 2) { results = []; return }
        falcon.call("assistance.search", { query: text.trim() }, function (ok, r) { if (ok) root.results = r.results.slice(0, 6) })
    }
    function shelve(file, tag) {
        var payload = { file_index_id: file.id, tag: tag }
        if (tag === "worker_dept") payload.scope_department_id = tree.length ? tree[0].department_id : null
        falcon.call("resource.tag", payload, function (ok, r) {
            shell.notify(ok ? file.filename + " is on the " + root.tierWord(tag) + " shelf" : r.message, !ok)
            root.refresh()
            root.search(findField.text)
        })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 16

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Column {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                Row {
                    spacing: 6
                    Txt { text: root.dept; color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody
                          MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: root.back() } }
                    Icon { name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: "Resources"; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                }
                Row {
                    spacing: 12
                    Txt { text: "Resources"; color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody; color: root.violations.length ? Theme.warn : Qt.rgba(1, 1, 1, 0.55)
                          text: "the folders are the access policy"
                                + (root.violations.length ? " · " + root.violations.length + (root.violations.length === 1 ? " file" : " files") + " out of place" : "") }
                }
            }
            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "Esc to go back"
                  color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody }
        }

        // --- the shelves ----------------------------------------------------------------------------------
        GridCell {
            objectName: "resourceShelves"
            Layout.fillWidth: true
            Layout.preferredHeight: 330
            topAlign: true
            title: "The shelves"
            narration: ({ brief: root.shelves.length + " tiers", state: "ok" })
            Column {
                width: parent.width
                spacing: 12
                // files to shelve: found by name, then dragged
                Row {
                    spacing: 12
                    height: 34
                    Field { id: findField; objectName: "shelveSearch"; width: 260; placeholderText: "find a file to shelve"; onTextEdited: root.search(text) }
                    Repeater {
                        model: root.results
                        delegate: Rectangle {
                            id: chip
                            required property var modelData
                            width: chipText.implicitWidth + 44; height: 32; radius: 9
                            color: Theme.pane; border.width: 1; border.color: Theme.line2
                            Drag.active: chipArea.drag.active
                            Drag.keys: ["file"]
                            Drag.hotSpot.x: width / 2; Drag.hotSpot.y: height / 2
                            property var file: modelData
                            Icon { x: 11; anchors.verticalCenter: parent.verticalCenter; name: "file"; size: 14; color: Theme.dim }
                            Txt { id: chipText; x: 32; anchors.verticalCenter: parent.verticalCenter; text: modelData.filename; color: Theme.ink
                                  font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                            MouseArea {
                                id: chipArea; anchors.fill: parent; cursorShape: Qt.OpenHandCursor
                                drag.target: chip
                                onReleased: { if (chip.Drag.target) chip.Drag.drop(); chip.x = 0; chip.y = 0; root.hoverTag = "" }
                            }
                            states: State { when: chipArea.drag.active; ParentChange { target: chip; parent: root } }
                        }
                    }
                }
                Row {
                    width: parent.width
                    spacing: 32
                    Repeater {
                        model: root.shelves
                        delegate: Item {
                            id: shelf
                            required property var modelData
                            width: (parent.width - 32 * (root.shelves.length - 1)) / Math.max(1, root.shelves.length)
                            height: 170
                            readonly property bool open: root.hoverTag === modelData.tag
                            readonly property color tone: Theme.tone(root.toneOf(modelData.tag))
                            Shape {
                                width: parent.width; height: 70
                                antialiasing: true
                                ShapePath {
                                    strokeColor: shelf.open ? shelf.tone : Qt.rgba(1, 1, 1, 0.22)
                                    strokeWidth: 1.4
                                    strokeStyle: shelf.open ? ShapePath.DashLine : ShapePath.SolidLine
                                    fillColor: shelf.open ? Qt.rgba(shelf.tone.r, shelf.tone.g, shelf.tone.b, 0.12) : Qt.rgba(1, 1, 1, 0.03)
                                    startX: 2; startY: 10
                                    PathLine { x: shelf.width * 0.16; y: 10 }
                                    PathLine { x: shelf.width * 0.2; y: 16 }
                                    PathLine { x: shelf.width - 2; y: 16 }
                                    PathLine { x: shelf.width - 2; y: 68 }
                                    PathLine { x: 2; y: 68 }
                                    PathLine { x: 2; y: 10 }
                                }
                            }
                            Column {
                                y: 80
                                spacing: 3
                                Txt { text: root.tierWord(shelf.modelData.tag); color: shelf.open ? shelf.tone : Theme.ink; font.pixelSize: Theme.fRow; font.weight: Font.DemiBold }
                                Txt { text: root.whoMay(shelf.modelData.tag); color: Theme.faint; font.pixelSize: Theme.fMeta }
                                Txt { text: shelf.modelData.files + (shelf.modelData.files === 1 ? " file" : " files"); color: Theme.dim; font.pixelSize: Theme.fMeta }
                            }
                            DropArea {
                                width: parent.width; height: 70
                                keys: ["file"]
                                onEntered: root.hoverTag = shelf.modelData.tag
                                onExited: if (root.hoverTag === shelf.modelData.tag) root.hoverTag = ""
                                onDropped: function (drop) { root.shelve(drop.source.file, shelf.modelData.tag); root.hoverTag = "" }
                            }
                        }
                    }
                }
                Txt { text: "Drop a file on a shelf to tag it. The shelf you hover opens; the tier is who may have it."
                      color: Theme.faint; font.pixelSize: Theme.fMeta }
            }
        }

        // --- out of place ----------------------------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20
            GridCell {
                id: placeCell
                objectName: "resourceOutOfPlace"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "Out of place"
                narration: ({ brief: root.violations.length ? root.violations.length + (root.violations.length === 1 ? " file" : " files") : "none",
                              tone: root.violations.length ? "warn" : "ok", state: root.violations.length ? "ok" : "empty",
                              note: "Everything is where it belongs", sentence: "A file on the wrong shelf shows here." })
                PagedColumn {
                    width: parent.width
                    height: Math.max(70, placeCell.room)
                    itemHeight: 58
                    model: root.violations
                    delegate: InfoCard {
                        iconName: "file"; iconTone: modelData ? root.toneOf(modelData.expected_tag) : ""
                        title: modelData ? modelData.filename : ""
                        line: modelData ? root.tierWord(modelData.expected_tag) + " · on " + modelData.hostname + " · " + root.timeOf(modelData.detected_at) : ""
                        selected: modelData && modelData.id === root.chosenId
                        onClicked: root.chosenId = modelData.id
                    }
                }
            }
            GridCell {
                objectName: "resourceChosen"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: root.chosen ? root.chosen.filename : "A file"
                narration: ({ brief: root.chosen ? "out of place" : "", tone: "danger", state: root.chosen ? "ok" : "empty",
                              note: "Nothing chosen", sentence: "Pick a file on the left." })
                Column {
                    visible: root.chosen !== null
                    width: parent.width
                    spacing: 10
                    readonly property var owner: root.chosen ? root.person(root.chosen.surfaced_to_account_id) : null
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold
                          text: root.chosen ? root.chosen.filename + " is out of place." : "" }
                    Repeater {
                        model: !root.chosen ? [] : [
                            ["Tier", root.tierWord(root.chosen.expected_tag), root.toneOf(root.chosen.expected_tag)],
                            ["Found on", root.chosen.hostname + ", in " + Automate.folderName(String(root.chosen.path).replace(/[\\/][^\\/]*$/, "")), ""],
                            ["Noticed", root.timeOf(root.chosen.detected_at) + (root.chosen.detected_via === "polling_fallback" ? " · on a sweep" : ""), ""],
                            ["Recognised by", "its content, not its name", ""]]
                        delegate: Item {
                            required property var modelData
                            width: parent.width; height: 34
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                            Txt { anchors.verticalCenter: parent.verticalCenter; text: modelData[0]; color: Theme.dim; font.pixelSize: Theme.fBody }
                            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]
                                  color: modelData[2] ? Theme.tone(modelData[2]) : Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                        }
                    }
                    Row {
                        spacing: 8
                        GBtn { visible: parent.parent.owner !== null; text: parent.parent.owner ? "Ping " + parent.parent.owner.name.split(" ")[0] : ""; iconName: "ping"
                               onClicked: falcon.call("assistance.ping", { to_account_id: root.chosen.surfaced_to_account_id }, function (ok, r) {
                                   shell.notify(ok ? "Pinged" : r.message, !ok) }) }
                        TBtn { objectName: "resolveViolation"; text: "It has moved"; iconName: "check"; tone: "ok"
                               onClicked: falcon.call("resource.resolve", { violation_id: root.chosen.id }, function (ok, r) {
                                   shell.notify(ok ? "Marked as moved" : r.message, !ok); root.chosenId = 0; root.refresh() }) }
                    }
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                          text: "Not deleted. Ignored until moved" + (parent.owner ? "; " + parent.owner.name + " has been told." : ".")
                                + " If a copy is still there, it is flagged again." }
                }
            }
        }
    }
}
