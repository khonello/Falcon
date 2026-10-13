import QtQuick
import "."

// WHERE A MARKED FILE MAY BE, AND WHERE COPIES TURNED UP (6 Oct 2026). On the left the zone it is
// allowed in, drawn as a boundary with the original inside; on the right everywhere else, a card for
// each copy found there (three, then "+N more"). Nothing found keeps the same shape. A card picks it.
Item {
    id: root
    property var mark: null                 // {name, host, path, kind, keep, files}
    property var copies: []                 // [{id, host, user, folder, file, at, sev}]
    property string picked: ""
    property var acted: ({})
    signal pick(string id)
    signal changeKeep()

    readonly property var shown: copies.slice(0, 3)
    readonly property int ch: 58
    readonly property int cg: 10
    readonly property int topY: 30
    readonly property int zh: 3 * (ch + cg) - cg
    readonly property real zw: Math.min(340, Math.round(width * 0.38))
    readonly property real cardW: Math.max(300, Math.min(400, Math.round(width * 0.34)))
    readonly property real ex: Math.max(zw + 90, width - cardW - 2)
    implicitHeight: topY + zh + 24
    function cy(j) { return topY + j * (ch + cg) + ((3 - shown.length) * (ch + cg)) / 2 }
    readonly property real fmid: topY + zh / 2 + 14

    Txt { y: 2; text: "ALLOWED"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
    Txt { x: root.ex; y: 2; text: "ELSEWHERE"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }

    // the zone it may be in
    Rectangle {
        y: root.topY
        width: root.zw
        height: root.zh
        radius: 10
        color: Theme.surface2
        border.width: 1
        border.color: Theme.borderStrong
        // on this console's own PC the concept says so: "ADM-01 · your PC", "allowed anywhere on this PC"
        readonly property bool mine: !!root.mark && root.mark.pc !== undefined && root.mark.pc === falcon.pcId
        Row { x: 14; y: 12; spacing: 0
              Txt { text: root.mark ? root.mark.host || "its machine" : ""; mono: true; font.weight: Font.DemiBold; elide: Text.ElideNone }
              Txt { visible: parent.parent.mine; text: "  · your PC"; color: Theme.text3; elide: Text.ElideNone } }
        Row {
            x: 14; y: 30
            width: parent.width - 28
            Txt { width: parent.width - cl.width; color: Theme.text2; font.pixelSize: 12
                  text: root.mark ? (root.mark.keep === "path" ? "allowed only in " + (root.mark.kind === "folder" ? root.mark.path : String(root.mark.path || "").replace(/[^\\/]+$/, ""))
                                                   : "allowed anywhere on " + (parent.parent.mine ? "this PC" : root.mark.host || "its machine")) : "" }
            Link { id: cl; text: "change"; quiet: true; font.pixelSize: 12; font.underline: true; onClicked: root.changeKeep() }
        }
        Rectangle {
            x: 22
            y: root.fmid - root.topY - 25
            width: parent.width - 44
            height: 50
            radius: 6
            color: Theme.surface
            border.width: 1
            border.color: Theme.borderStrong
            Icon { x: 12; anchors.verticalCenter: parent.verticalCenter; name: root.mark && root.mark.kind === "folder" ? "folder" : "file"; size: 16; color: Theme.text2 }
            Column {
                x: 38
                width: parent.width - 48
                anchors.verticalCenter: parent.verticalCenter
                Txt { width: parent.width; text: root.mark ? root.mark.name : ""; font.weight: Font.DemiBold }
                Txt { width: parent.width; color: Theme.text3; font.pixelSize: 11
                      text: root.mark && root.mark.kind === "folder" ? "folder · " + Theme.fmt(root.mark.files || 0) + " files, and any added later" : "file · the original" }
            }
        }
    }

    // the lines from the original to each copy
    Canvas {
        id: lines
        anchors.fill: parent
        onPaint: {
            var c = getContext("2d"); c.reset()
            c.strokeStyle = Theme.alpha(Theme.crit, 0.55); c.fillStyle = Theme.alpha(Theme.crit, 0.55); c.lineWidth = 1.25
            for (var j = 0; j < root.shown.length; j++) {
                var y = root.cy(j) + root.ch / 2, x1 = root.zw - 22, m = (x1 + root.ex) / 2
                c.setLineDash([4, 4]); c.beginPath(); c.moveTo(x1, root.fmid); c.bezierCurveTo(m, root.fmid, m, y, root.ex - 7, y); c.stroke(); c.setLineDash([])
                c.beginPath(); c.moveTo(root.ex - 7, y - 3.5); c.lineTo(root.ex, y); c.lineTo(root.ex - 7, y + 3.5); c.closePath(); c.fill()
            }
        }
        Connections { target: root; function onShownChanged() { lines.requestPaint() } function onWidthChanged() { lines.requestPaint() } }
        Connections { target: Theme; function onDarkChanged() { lines.requestPaint() } }
    }

    // each copy found elsewhere
    Repeater {
        model: root.shown
        Rectangle {
            required property var modelData
            required property int index
            x: root.ex
            y: root.cy(index)
            width: root.cardW
            height: root.ch
            radius: 7
            color: Theme.surface
            opacity: root.acted[modelData.id] ? 0.55 : 1
            border.width: root.picked === modelData.id ? 1.75 : 1
            border.color: root.picked === modelData.id ? Theme.text2 : Theme.mix(Theme.crit, Theme.borderStrong, 0.45)
            Txt { x: 14; y: 12; width: parent.width - 120; textFormat: Text.RichText
                  text: "<span style='font-family:" + Theme.mono + ";font-weight:600'>" + modelData.host + "</span><span style='color:" + Theme.text3 + "'>  "
                        + (modelData.user ? "· " + modelData.user + " was signed in" : "· nobody signed in") + "</span>" }
            Txt { x: 14; y: 32; width: parent.width - 120; mono: true; color: Theme.text3; font.pixelSize: 11; text: modelData.folder || modelData.file }
            Txt { anchors.right: parent.right; anchors.rightMargin: 14; y: 12; text: Time.age(modelData.at) + " ago"; color: Theme.crit; font.pixelSize: 11; elide: Text.ElideNone }
            Txt { anchors.right: parent.right; anchors.rightMargin: 14; y: 32; color: Theme.text3; font.pixelSize: 11; elide: Text.ElideNone
                  text: root.acted[modelData.id] ? "dealt with" : root.picked === modelData.id ? "picked" : "deal with it ›" }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.pick(modelData.id) }
        }
    }
    // nothing found keeps the same shape
    Rectangle {
        visible: root.shown.length === 0
        x: root.ex
        y: root.topY
        width: root.cardW
        height: root.zh
        radius: 10
        color: "transparent"
        border.width: 1
        border.color: Theme.borderStrong
        Column {
            anchors.centerIn: parent
            spacing: 4
            Txt { anchors.horizontalCenter: parent.horizontalCenter; text: "No copy anywhere else"; color: Theme.accent; font.weight: Font.DemiBold }
            Txt { anchors.horizontalCenter: parent.horizontalCenter; text: "watched on every machine, by content"; color: Theme.text3; font.pixelSize: 12 }
        }
    }
    Txt {
        visible: root.copies.length > 3
        x: root.ex
        y: root.height - 16
        color: Theme.text3; font.pixelSize: 12
        text: "+" + Theme.fmt(root.copies.length - 3) + " more " + (root.copies.length - 3 === 1 ? "copy" : "copies") + ", less serious · all listed on the right"
    }
}
