import QtQuick
import "."

// THE FLEET MAP. Machines as tiles grouped by department (three departments, then "+N more"); one
// switch -- Status, CPU, Version, Check-in -- and every view uses the same five marks, so one legend
// reads them all. A tile shows the number at the end of the machine's name. Hover shows its card; a
// click pins the card in place, and only the card's own link, which names the page, leaves the page.
Item {
    id: root
    property string by: "Status"
    property var cpu: ({})                   // host -> CPU % right now (the CPU view)
    property string openLabel: "Open {h}'s page →"
    property string moreLabel: "on Machines →"
    signal open(string host)
    signal more()

    property var hov: null
    property string pin: ""
    readonly property var shown: hov ? hov : (pin !== "" ? Fleet.byHost[pin] : null)
    implicitHeight: col.height + legend.height + 12

    function tileFor(m) {
        if (by === "Status") return Fleet.mark(m.status)
        if (by === "Version") return !m.online ? "offline" : !m.behind ? "quiet" : m.escalated ? "high" : "watch"
        if (by === "Check-in") return m.online ? "quiet" : "high"
        var v = cpu[m.host]
        return !m.online || v === undefined || v === null ? "offline" : v >= 90 ? "crit" : v >= 75 ? "high" : v >= 60 ? "watch" : "quiet"
    }
    readonly property var rank: ({ crit: 0, high: 1, watch: 2, offline: 3, quiet: 4 })
    // the worst first into the shown set, then the order they were in
    function pickShown(ms, n) {
        if (ms.length <= n) return { shown: ms, rest: 0 }
        var idx = ms.map(function (m, i) { return i })
        idx.sort(function (a, b) { return root.rank[root.tileFor(ms[a])] - root.rank[root.tileFor(ms[b])] || a - b })
        idx = idx.slice(0, n).sort(function (a, b) { return a - b })
        return { shown: idx.map(function (i) { return ms[i] }), rest: ms.length - n }
    }
    function tileNo(h) { var m = /(\d+)$/.exec(h); return m ? m[1] : h.slice(-3) }

    readonly property var legend: by === "Status" ? [["quiet", "Healthy"], ["watch", "Worth a look"], ["high", "High"], ["crit", "Critical"], ["offline", "Offline"]]
        : by === "Version" ? [["quiet", (Fleet.version || "Current") + " (current)"], ["watch", "One version behind"], ["high", "Two or more behind"], ["offline", "Offline"]]
        : by === "Check-in" ? [["quiet", "Within the last minute"], ["high", "Over an hour ago"]]
        : [["quiet", "Under 60%"], ["watch", "60–75%"], ["high", "75–90%"], ["crit", "90% and over"], ["offline", "Offline"]]

    Column {
        id: col
        width: parent.width
        spacing: 14
        Repeater {
            model: Fleet.depts.slice(0, 3)
            delegate: Column {
                required property var modelData
                readonly property var pk: root.pickShown(modelData.machines, 35)
                width: col.width
                spacing: 6
                Row {
                    spacing: 8
                    width: parent.width
                    Txt { id: dn; text: modelData.name; font.weight: Font.DemiBold; width: Math.min(implicitWidth, parent.width * 0.45) }
                    Txt {
                        width: parent.width - dn.width - 8
                        color: modelData.admins.length ? Theme.text3 : Theme.crit
                        text: Theme.many(modelData.machines.length, "machine") + " · "
                              + (modelData.admins.length ? Theme.listNames(modelData.admins.map(function (a) { return a.name }), 3) : "no Admin")
                    }
                }
                Flow {
                    width: parent.width
                    spacing: 5
                    Txt {
                        visible: modelData.machines.length === 0
                        text: "No machines yet. They appear here as they are registered."
                        color: Theme.text3; font.pixelSize: 12
                    }
                    Repeater {
                        model: pk.shown
                        delegate: Item {
                            required property var modelData
                            width: 46; height: 46
                            HealthMark {
                                anchors.fill: parent
                                size: 46
                                bordered: false
                                k: root.tileFor(modelData)
                                label: root.tileNo(modelData.host)
                                fontSize: root.tileNo(modelData.host).length > 3 ? 9 : root.tileNo(modelData.host).length > 2 ? 10 : 12
                                scale: area.containsMouse ? 1.06 : 1
                                Behavior on scale { NumberAnimation { duration: 120 } }
                            }
                            Rectangle {
                                visible: root.pin === modelData.host
                                anchors.fill: parent
                                anchors.margins: -2
                                radius: 6
                                color: "transparent"
                                border.width: 2
                                border.color: Theme.text2
                            }
                            MouseArea {
                                id: area
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onEntered: root.hov = modelData
                                onExited: root.hov = null
                                onClicked: root.pin = root.pin === modelData.host ? "" : modelData.host
                            }
                        }
                    }
                    Rectangle {
                        visible: pk.rest > 0
                        width: 46; height: 46; radius: 4
                        color: "transparent"
                        border.width: 1
                        border.color: Theme.borderStrong
                        Txt { anchors.centerIn: parent; text: "+" + pk.rest; color: Theme.text3; font.pixelSize: 11; elide: Text.ElideNone }
                    }
                }
            }
        }
        More {
            visible: Fleet.depts.length > 3
            n: Fleet.depts.length - 3
            what: "departments " + root.moreLabel
            onClicked: root.more()
        }
    }

    Row {
        id: legend
        anchors.top: col.bottom
        anchors.topMargin: 12
        spacing: 14
        Txt { visible: root.by === "CPU"; text: "CPU right now:"; color: Theme.text3; font.pixelSize: Theme.fSmall; elide: Text.ElideNone }
        Repeater {
            model: root.legend
            Row {
                required property var modelData
                spacing: 6
                HealthMark { k: modelData[0]; size: 14; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: modelData[1]; color: Theme.text3; font.pixelSize: Theme.fSmall; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
            }
        }
    }

    // the card speaks for the view you are in: its first line is this view's band, in this view's words
    Rectangle {
        id: card
        visible: root.shown !== null
        anchors.right: parent.right
        y: 0
        width: 250
        height: cardCol.height + 18
        radius: 5
        color: Theme.surface
        border.width: 1
        border.color: Theme.borderStrong
        z: 10
        readonly property var m: root.shown
        readonly property string k: m ? root.tileFor(m) : "quiet"
        readonly property string band: {
            for (var i = 0; i < root.legend.length; i++) if (root.legend[i][0] === k) return root.legend[i][1]
            return m ? Fleet.words[m.status] : ""
        }
        readonly property color bandColor: k === "crit" || k === "high" ? Theme.crit : k === "watch" ? Theme.med : Theme.text2
        Column {
            id: cardCol
            x: 10; y: 9
            width: parent.width - 20
            spacing: 2
            Row {
                width: parent.width
                spacing: 6
                Txt { text: card.m ? card.m.host : ""; mono: true; font.weight: Font.DemiBold; elide: Text.ElideNone; width: parent.width - bandRow.width - 6 }
                Row {
                    id: bandRow
                    spacing: 6
                    HealthMark { k: card.k; size: 14; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: card.band; color: card.bandColor; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                }
            }
            Txt { text: card.m ? (card.m.user || "No one signed in") + " · " + card.m.deptName : ""; color: Theme.text2; width: parent.width; bottomPadding: 4 }
            Repeater {
                model: card.m ? [["CPU", "CPU", root.cpu[card.m.host] !== undefined ? Math.round(root.cpu[card.m.host]) + "%" : "—"],
                                 ["Version", "Version", card.m.ver || "—"],
                                 ["Check-in", "Check-in", card.m.online ? "seconds ago" : Time.ago(card.m.seen)]] : []
                Row {
                    required property var modelData
                    spacing: 0
                    Txt { width: 64; text: modelData[0]; color: Theme.text3; font.weight: modelData[1] === root.by ? Font.DemiBold : Font.Normal }
                    Txt { text: modelData[2]; mono: true; elide: Text.ElideNone; color: modelData[1] === root.by ? Theme.text : Theme.text2; font.weight: modelData[1] === root.by ? Font.DemiBold : Font.Normal }
                }
            }
            Txt {
                visible: card.m !== null && (root.by === "Status" ? card.m.note !== "" : true)
                topPadding: 4
                width: parent.width
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
                font.pixelSize: root.by === "Status" ? Theme.fBody : Theme.fSmall
                color: root.by === "Status" ? card.bandColor : Theme.text3
                text: !card.m ? "" : root.by === "Status" ? card.m.note
                      : "Overall health: " + Fleet.words[card.m.status].toLowerCase() + (card.m.note ? " · " + card.m.note : "")
            }
            Item { width: 1; height: 6 }
            Rectangle { visible: root.pin !== "" && card.m && card.m.host === root.pin; width: parent.width; height: 1; color: Theme.border }
            Row {
                visible: root.pin !== "" && card.m !== null && card.m.host === root.pin
                width: parent.width
                topPadding: 6
                Link { text: root.openLabel.replace("{h}", root.pin); onClicked: root.open(root.pin) }
                Item { width: parent.width - 150 - closeL.width; height: 1 }
                Link { id: closeL; text: "Close"; quiet: true; onClicked: root.pin = "" }
            }
            Txt {
                visible: !(root.pin !== "" && card.m !== null && card.m.host === root.pin)
                text: "Click the tile to keep this open"
                color: Theme.text4
                font.pixelSize: 11
            }
        }
    }
}
