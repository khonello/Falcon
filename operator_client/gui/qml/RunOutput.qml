import QtQuick
import "."

// WHAT A RUN RETURNED. Three kinds, each shown its own way: text (what it printed), a list (programs,
// files on a USB device), or a picture (a screenshot, fetched only when opened, and every view audited).
// Kept with the run for 90 days, like the audit log.
Column {
    id: root
    property int executionId: 0
    property var ex: null
    property var lines: []
    property var result: null
    property bool expired: false
    property string image: ""
    property bool loaded: false
    spacing: 8

    onExecutionIdChanged: load()
    Component.onCompleted: load()
    function load() {
        if (!executionId) return
        falcon.call("control.execution", { execution_id: executionId }, function (ok, r) {
            root.loaded = true
            if (!ok) return
            root.ex = r.execution; root.lines = r.output || []; root.result = r.result; root.expired = !!r.expired
            if (r.execution && r.execution.has_image)
                falcon.call("control.execution_image_get", { execution_id: root.executionId }, function (ok2, r2) {
                    if (ok2 && r2.data) root.image = "data:" + (r2.mime || "image/png") + ";base64," + r2.data
                })
        })
    }
    readonly property var rows: result && result.rows ? result.rows : Array.isArray(result) ? result : []
    readonly property var cols: result && result.columns ? result.columns : rows.length && typeof rows[0] === "object" && !Array.isArray(rows[0]) ? Object.keys(rows[0]).slice(0, 2) : []

    Txt { visible: !root.loaded; text: "Reading what it returned…"; color: Theme.text3; font.pixelSize: 12 }
    Txt { visible: root.expired; text: "Cleared after 90 days, like the audit log."; color: Theme.text3; font.pixelSize: 12 }
    // a picture
    Column {
        visible: root.image !== ""
        spacing: 4
        Image { source: root.image; width: 240; fillMode: Image.PreserveAspectFit; smooth: true }
        Txt { text: "Only the department's Admins and the Super User can see it; every view is recorded."; color: Theme.text3; font.pixelSize: 12; width: 360; wrapMode: Text.WordWrap; elide: Text.ElideNone }
    }
    // a list
    Rectangle {
        visible: root.rows.length > 0 && root.image === ""
        width: Math.min(420, root.width)
        height: lc.height
        radius: 5
        color: "transparent"
        border.width: 1
        border.color: Theme.border
        clip: true
        Column {
            id: lc
            width: parent.width
            Rectangle { width: parent.width; height: 26; color: Theme.surface2
                        Txt { x: 10; anchors.verticalCenter: parent.verticalCenter; text: root.cols[0] || "Item"; color: Theme.text3; font.pixelSize: 11 }
                        Txt { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: root.cols[1] || ""; color: Theme.text3; font.pixelSize: 11 } }
            Repeater {
                model: root.rows.slice(0, 8)
                Rectangle {
                    required property var modelData
                    width: lc.width; height: 26; color: "transparent"
                    readonly property var a: Array.isArray(modelData) ? modelData : [modelData[root.cols[0]], modelData[root.cols[1]]]
                    Rectangle { width: parent.width; height: 1; color: Theme.grid }
                    Txt { x: 10; width: parent.width - 100; anchors.verticalCenter: parent.verticalCenter; text: String(parent.a[0] === undefined ? "" : parent.a[0]); mono: true; font.pixelSize: 12 }
                    Txt { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: String(parent.a[1] === undefined ? "" : parent.a[1]); mono: true; color: Theme.text3; font.pixelSize: 12 }
                }
            }
            Txt { visible: root.rows.length > 8; x: 10; topPadding: 4; bottomPadding: 4; text: "+" + (root.rows.length - 8) + " more"; color: Theme.text3; font.pixelSize: 12 }
        }
    }
    // text
    Rectangle {
        visible: root.loaded && root.rows.length === 0 && root.image === ""
        width: root.width
        height: Math.min(160, pre.implicitHeight + 16)
        radius: 5
        color: Theme.surface2
        clip: true
        Txt {
            id: pre
            x: 10; y: 8
            width: parent.width - 20
            mono: true
            font.pixelSize: 12
            wrapMode: Text.WrapAnywhere
            elide: Text.ElideNone
            text: root.lines.length ? root.lines.join("\n") : (root.ex && root.ex.summary ? root.ex.summary : "Finished with no output.")
        }
    }
}
