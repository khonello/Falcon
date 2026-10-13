import QtQuick
import "."

// A FLOW DRAWN LEFT TO RIGHT: its sources (several merge into one point), the steps every file takes,
// then the destinations (several make it branch), with a branch's own steps written on its edge.
// Files only move left to right. An empty slot is dashed; one waiting for a person is amber.
//   srcs: [{host, path, via}]   stages: [{op, kind, scope: "all" | index}]   dests: [{host, path, ask, bad}]
Item {
    id: root
    property var srcs: []
    property var stages: []
    property var dests: []

    readonly property var srcList: srcs.length ? srcs : [{ host: "", path: "" }]
    readonly property var destList: dests.length ? dests : [{ host: "", path: "" }]
    readonly property var shared: stages.filter(function (s) { return s.scope === "all" })
    readonly property int ns: srcList.length
    readonly property int nd: destList.length
    readonly property int rowH: 66
    readonly property int nw: 168
    readonly property int nh: 48
    readonly property real w: Math.max(560, width)
    implicitHeight: Math.max(110, Math.max(ns, nd) * rowH + 24)
    readonly property bool join: ns > 1
    readonly property int cols: 2 + shared.length + (join ? 1 : 0)
    readonly property real gapX: (w - nw - 8) / (cols - 1)
    function colX(c) { return 4 + c * gapX }
    readonly property real midY: height / 2
    function dy(i) { return nd === 1 ? midY : height / 2 - ((nd - 1) * rowH) / 2 + i * rowH }
    function sy(i) { return ns === 1 ? midY : height / 2 - ((ns - 1) * rowH) / 2 + i * rowH }
    readonly property real mx: join ? colX(1) + nw / 2 : 0
    readonly property int firstStage: 1 + (join ? 1 : 0)
    readonly property real lastX: shared.length ? colX(firstStage + shared.length - 1) + nw : join ? mx : colX(0) + nw
    readonly property real destX: colX(cols - 1)

    onWidthChanged: cv.requestPaint()
    onSrcsChanged: cv.requestPaint()
    onDestsChanged: cv.requestPaint()
    onStagesChanged: cv.requestPaint()
    Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }

    Canvas {
        id: cv
        anchors.fill: parent
        onPaint: {
            var c = getContext("2d"); c.reset(); c.lineWidth = 2
            function edge(x1, y1, x2, y2, dash, col) {
                c.strokeStyle = col || Theme.ser2; c.setLineDash(dash ? [4, 4] : [])
                c.beginPath(); c.moveTo(x1, y1); c.bezierCurveTo((x1 + x2) / 2, y1, (x1 + x2) / 2, y2, x2, y2); c.stroke(); c.setLineDash([])
            }
            if (root.join) for (var i = 0; i < root.ns; i++) edge(root.colX(0) + root.nw, root.sy(i), root.mx, root.midY, !root.srcList[i].host)
            if (root.shared.length) edge(root.join ? root.mx : root.colX(0) + root.nw, root.midY, root.colX(root.firstStage), root.midY)
            for (var k = 1; k < root.shared.length; k++) edge(root.colX(root.firstStage + k - 1) + root.nw, root.midY, root.colX(root.firstStage + k), root.midY)
            for (var d = 0; d < root.nd; d++) {
                var dd = root.destList[d]
                edge(root.lastX, root.midY, root.destX, root.dy(d), !dd.host || dd.ask, dd.ask ? Theme.med : dd.bad ? Theme.crit : null)
            }
            if (root.join) { c.fillStyle = Theme.ser2; c.beginPath(); c.arc(root.mx, root.midY, 5, 0, Math.PI * 2); c.fill() }
        }
    }
    component Node: Rectangle {
        property string title: ""
        property string sub: ""
        property string tone: ""            // "" | empty | ask | bad
        width: root.nw
        height: root.nh
        radius: 5
        color: tone === "empty" ? "transparent" : tone === "ask" ? Theme.mix(Theme.med, Theme.surface, 0.07) : Theme.surface
        border.width: tone === "empty" || tone === "ask" ? 0 : 1
        border.color: tone === "bad" ? Theme.crit : Theme.borderStrong
        Canvas {
            visible: parent.tone === "empty" || parent.tone === "ask"
            anchors.fill: parent
            onPaint: { var c = getContext("2d"); c.reset(); c.strokeStyle = parent.tone === "ask" ? Theme.med : Theme.borderStrong; c.setLineDash([4, 3]); c.beginPath(); c.roundedRect(0.5, 0.5, width - 1, height - 1, 5, 5); c.stroke() }
        }
        Txt { x: 10; y: 7; width: parent.width - 20; text: parent.title; font.weight: Font.DemiBold; font.pixelSize: 12
              mono: /^[A-Z]{2,3}-/.test(parent.title); color: parent.tone === "empty" ? Theme.text4 : Theme.text }
        Txt { x: 10; y: 25; width: parent.width - 20; text: parent.sub; font.pixelSize: 11; mono: parent.tone !== "ask"; color: parent.tone === "ask" ? Theme.med : Theme.text3 }
    }
    Repeater {
        model: root.srcList
        Node {
            required property var modelData
            required property int index
            x: root.colX(0); y: root.sy(index) - root.nh / 2
            title: modelData.host || "Source"
            sub: modelData.host ? (modelData.path || "pick a folder") + (modelData.via ? " · " + modelData.via : "") : "not set"
            tone: modelData.host ? "" : "empty"
        }
    }
    Repeater {
        model: root.shared
        Node { required property var modelData; required property int index
               z: 1                                    // over a branch's label, as the concept draws the steps last
               x: root.colX(root.firstStage + index); y: root.midY - root.nh / 2; title: modelData.op; sub: modelData.kind; }
    }
    Repeater {
        model: root.destList
        Item {
            required property var modelData
            required property int index
            readonly property var branch: root.stages.filter(function (s) { return s.scope === index })
            // a branch's own steps, written on its edge with a halo of the panel's colour, as the concept's stroke
            Rectangle {
                visible: parent.branch.length > 0
                x: (root.lastX + root.destX) / 2 - width / 2
                y: (root.midY + root.dy(index)) / 2 - 6 - height + 3
                width: bl.implicitWidth + 6
                height: bl.implicitHeight
                radius: 3
                color: Theme.surface
                Txt { id: bl; x: 3; text: parent.parent.branch.map(function (b) { return b.op }).join(" · "); color: Theme.ser3; font.pixelSize: 11; elide: Text.ElideNone }
            }
            Node {
                x: root.destX; y: root.dy(index) - root.nh / 2
                title: modelData.host || "Destination"
                sub: modelData.host ? (modelData.ask ? "picks a folder" : modelData.path || "pick a folder") : "not set"
                tone: !modelData.host ? "empty" : modelData.ask ? "ask" : modelData.bad ? "bad" : ""
            }
        }
    }
}
