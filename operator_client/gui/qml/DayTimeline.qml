import QtQuick
import "."

// WHO HELD EACH MACHINE, AND WHEN. The one place in this console licensed to use colour for meaning
// beyond the two status hues, because a bar has nothing else to say with: at the PC, entered from
// above, assisted. The night is shaded and never cropped -- sneaky things happen at unusual times.
//
// 24 hours is the default span. 6 to 6 is there for a normal working day, and it is a switch, not a
// setting: the day does not change, only the window you read it through (docs/UI.md).
Item {
    id: root

    property var sessions: []             // hierarchy.sessions_today
    property int fromHour: 0
    property int toHour: 24
    property int laneHeight: 26
    property int labelWidth: 120

    readonly property int span: toHour - fromHour
    readonly property real dayStart: {
        var d = new Date()
        d.setHours(0, 0, 0, 0)
        return d.getTime()
    }
    // one bar per session, in hours from midnight, clipped to the window being read
    readonly property var lanes: {
        var byHost = {}
        for (var i = 0; i < sessions.length; i++) {
            var s = sessions[i]
            var host = s.hostname || ("pc " + s.pc_id)
            var a = (new Date(s.entered_at).getTime() - dayStart) / 3600000
            var b = s.ended_at ? (new Date(s.ended_at).getTime() - dayStart) / 3600000
                               : (Date.now() - dayStart) / 3600000
            if (b <= root.fromHour || a >= root.toHour) continue
            if (!byHost[host]) byHost[host] = []
            byHost[host].push({ from: Math.max(a, root.fromHour), to: Math.min(b, root.toHour),
                                who: s.occupant_name || "someone", via: s.occupied_via,
                                running: !s.ended_at, entered_at: s.entered_at, ended_at: s.ended_at })
        }
        var out = []
        for (var host in byHost) out.push({ host: host, bars: byHost[host] })
        out.sort(function (x, y) { return String(x.host).localeCompare(String(y.host)) })
        return out
    }

    // the licensed exception: three ways a machine can be held, and a bar has only colour to say it
    function hue(via) {
        return via === "native" ? "#8c8c8c"              // at the PC: the quiet one, and the usual one
               : via === "assisted" ? "#722ed1"          // helped across departments, by consent
               : "#1677ff"                               // entered from above
    }
    function word(via) {
        return via === "native" ? "at the PC" : via === "assisted" ? "assisted" : "entered"
    }
    function clock(h) {
        var hh = Math.floor(h) % 24
        return (hh < 10 ? "0" + hh : hh) + ":00"
    }

    implicitHeight: head.height + Math.max(1, lanes.length) * laneHeight + legend.height + Theme.s3

    // --- the hour axis, with the night shaded rather than cut off -------------------------------
    Item {
        id: head
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 22

        Item {
            id: plot
            anchors.left: parent.left
            anchors.leftMargin: root.labelWidth
            anchors.right: parent.right
            height: parent.height
        }

        Repeater {
            model: root.span + 1
            delegate: Txt {
                required property int index
                readonly property int hour: root.fromHour + index
                visible: index % (root.span > 12 ? 3 : 2) === 0
                x: root.labelWidth + (plot.width * index / root.span) - (index === root.span ? 28 : 0)
                anchors.bottom: parent.bottom
                text: root.clock(hour)
                tone: "quiet"
                mono: true
                font.pixelSize: 10
            }
        }
    }

    // --- the lanes ------------------------------------------------------------------------------
    Item {
        id: body
        anchors.top: head.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: Math.max(1, root.lanes.length) * root.laneHeight

        // night, behind everything: 18:00 to 06:00, shaded, never cropped
        Repeater {
            model: [{ a: 0, b: 6 }, { a: 18, b: 24 }]
            delegate: Rectangle {
                required property var modelData
                readonly property real a: Math.max(modelData.a, root.fromHour)
                readonly property real b: Math.min(modelData.b, root.toHour)
                visible: b > a
                x: root.labelWidth + (body.width - root.labelWidth) * (a - root.fromHour) / root.span
                width: (body.width - root.labelWidth) * (b - a) / root.span
                height: parent.height
                color: Qt.rgba(0, 0, 0, 0.03)
            }
        }

        Column {
            anchors.fill: parent
            spacing: 0

            Repeater {
                model: root.lanes
                delegate: Item {
                    required property var modelData
                    width: body.width
                    height: root.laneHeight

                    Txt {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: root.labelWidth - Theme.s2
                        text: modelData.host
                        mono: true
                        font.pixelSize: Theme.fSmall
                    }
                    Rectangle {
                        anchors.left: parent.left
                        anchors.leftMargin: root.labelWidth
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        height: 1
                        color: Theme.split
                    }

                    Repeater {
                        model: modelData.bars
                        delegate: Rectangle {
                            required property var modelData
                            readonly property real track: body.width - root.labelWidth
                            x: root.labelWidth + track * (modelData.from - root.fromHour) / root.span
                            width: Math.max(3, track * (modelData.to - modelData.from) / root.span)
                            height: 12
                            radius: 3
                            anchors.verticalCenter: parent.verticalCenter
                            color: root.hue(modelData.via)
                            opacity: hov.hovered ? 1 : 0.85

                            HoverHandler { id: hov }
                            Rectangle {
                                visible: hov.hovered
                                y: -26
                                x: -2
                                z: 5
                                width: tip.implicitWidth + 2 * Theme.s2
                                height: 22
                                radius: Theme.radiusSm
                                color: Theme.ink
                                Txt {
                                    id: tip
                                    anchors.centerIn: parent
                                    text: modelData.who + " · " + root.word(modelData.via) + " · "
                                          + root.clock(modelData.from)
                                          + (modelData.running ? ", still there" : "")
                                    color: Theme.onDark
                                    font.pixelSize: 11
                                }
                            }
                        }
                    }
                }
            }
        }

        Empty {
            anchors.centerIn: parent
            width: 260
            visible: root.lanes.length === 0
            text: "Nobody held anything"
            hint: "No session was opened in this window."
        }
    }

    // --- what the colours mean, once ------------------------------------------------------------
    Row {
        id: legend
        anchors.top: body.bottom
        anchors.topMargin: Theme.s3
        anchors.left: parent.left
        anchors.leftMargin: root.labelWidth
        spacing: Theme.s4
        height: 16

        Repeater {
            model: ["native", "traversal", "assisted"]
            delegate: Row {
                required property var modelData
                spacing: Theme.s1 + 2
                Rectangle {
                    width: 10
                    height: 10
                    radius: 2
                    color: root.hue(modelData)
                    anchors.verticalCenter: parent.verticalCenter
                }
                Txt {
                    text: root.word(modelData)
                    tone: "quiet"
                    font.pixelSize: 11
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
