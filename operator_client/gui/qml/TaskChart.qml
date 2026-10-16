import QtQuick
import "."

// A TASK'S TARGETS ON ITS OWN CLOCK. One block per target: what done looks like for it, whether it has
// been found, its signs of progress shaded along the task's time (darker is busier), the found mark,
// and the task's own marks across every lane -- started, soft and final deadline, now.
// Verification and expectation stay apart (task-natural-combo.md): a target says what done looks
// like, and the system reports what it found there, never "passed".
Column {
    id: root
    property var task: null                 // the task.get view: items, expectations, deadlines
    property string host: ""
    spacing: 0

    readonly property real a: task ? Time.ms(task.created_at) : 0
    readonly property real fin: task && task.final_deadline_at ? Time.ms(task.final_deadline_at) : a + 86400000
    readonly property real b: Math.max(fin, Math.min(Time.now, fin + 86400000), a + 3600000)
    readonly property real end: Math.min(Time.now, b)
    property bool handedIn: false            // to verify: every target found, so the deadline is not missed
    readonly property bool finished: (task && task.status === "completed") || handedIn
    readonly property bool over: !finished && Time.now > fin
    function xAt(t, w) { return ((Math.max(a, Math.min(b, t)) - a) / (b - a)) * w }
    readonly property var marks: {
        if (!task) return []
        var out = []
        if (task.started_at) out.push(["Started", Time.ms(task.started_at), Theme.text3])
        if (task.soft_deadline_at) out.push(["Soft", Time.ms(task.soft_deadline_at), Theme.med])
        if (task.final_deadline_at) out.push(["Final", fin, over ? Theme.crit : Theme.text2])
        if (Time.now <= b) out.push(["Now", Time.now, Theme.accent])
        return out
    }
    readonly property var want: ({ create: "to be created", update: "to be changed after the task was given", exists: "to be there",
                                   used: "to be used", used_with_file: "to be used", installed_available: "to be installed", closed_not_running: "to be closed" })
    function nameOf(it) { return it.target_type === "program" ? (it.program_name || it.name || "a program") : (it.proposed_filename || it.name || it.proposed_path || "a file") }
    function linked(it) {
        if (!task || !it.linked_file_verification_item_id) return ""
        for (var i = 0; i < task.items.length; i++) if (task.items[i].id === it.linked_file_verification_item_id) return nameOf(task.items[i])
        return ""
    }
    function signals(it) { return (task && task.expectations ? task.expectations : []).filter(function (e) { return e.verification_item_id === it.id }) }
    function measure(it) {
        if (it.target_type === "program" && it.intent === "installed_available") return ["Shows up among the installed programs", "Read from " + (host || "the machine") + "'s list of installed programs each time it checks in."]
        if (it.target_type === "program") return ["Time in real use", "Counted only while the program is in use: keyboard, processor and memory moving. Open but idle does not count."]
        return [it.intent === "create" ? "The file appearing, then its saves" : "Saves, renames and moves of the file",
                "Watched through " + (host || "the machine") + "'s own file events, as they happen. Recognised by content, so a rename or a move does not lose it."]
    }

    // the marks' words across the top. Marks that fall within a few words of each other (a task given and started minutes ago has Started and
    // Now at the same place on a day-long clock) share one label, "Started · Now", instead of being written on top of each other
    readonly property var labels: {
        var out = [], gap = 56
        marks.slice().sort(function (p, q) { return p[1] - q[1] }).forEach(function (mk) {
            var x = xAt(mk[1], width), last = out.length ? out[out.length - 1] : null
            if (last && x - last.x < gap) { last.text += " · " + mk[0]; last.color = mk[2]; last.soft = last.soft && mk[0] === "Soft" }
            else out.push({ x: x, text: mk[0], color: mk[2], soft: mk[0] === "Soft" })
        })
        return out
    }
    Item {
        width: root.width; height: 16
        Repeater {
            model: root.labels
            Txt {
                required property var modelData
                x: Math.max(0, Math.min(root.width - implicitWidth, modelData.x - (modelData.soft ? implicitWidth + 3 : implicitWidth / 2)))
                text: modelData.text; color: modelData.color; font.pixelSize: 10; elide: Text.ElideNone
            }
        }
    }
    Repeater {
        model: root.task ? root.task.items : []
        delegate: Column {
            id: lane
            required property var modelData
            readonly property var sig: root.signals(modelData)
            readonly property string st: modelData.status
            width: root.width
            topPadding: 10
            bottomPadding: 12
            Row {
                width: parent.width
                spacing: 8
                Icon { name: modelData.target_type === "program" ? "appstore" : /[\/\\]$/.test(root.nameOf(modelData)) ? "folder" : "file"; size: 14; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                Txt {
                    width: parent.width - 300
                    textFormat: Text.RichText
                    anchors.verticalCenter: parent.verticalCenter
                    text: "<span style='font-family:" + Theme.mono + ";font-weight:500'>" + root.nameOf(lane.modelData) + "</span>"
                          + (root.linked(lane.modelData) ? "<span style='color:" + Theme.text3 + "'> with </span><span style='font-family:" + Theme.mono + "'>" + root.linked(lane.modelData) + "</span>" : "")
                          + " <span style='color:" + Theme.text3 + "'>" + (root.want[lane.modelData.intent] || lane.modelData.intent) + "</span>"
                }
                Txt {
                    width: 170
                    visible: lane.st !== "pending"
                    color: Theme.text3; font.pixelSize: 12
                    horizontalAlignment: Text.AlignRight
                    anchors.verticalCenter: parent.verticalCenter
                    text: lane.sig.length ? Theme.many(lane.sig.length, "sign") + " of progress" : ""
                }
                Row {
                    spacing: 5
                    anchors.verticalCenter: parent.verticalCenter
                    Icon { name: lane.st === "passed" ? "check" : lane.st === "failed" ? "exclaim" : "minus"; size: 13
                           color: lane.st === "passed" ? Theme.text2 : lane.st === "failed" ? Theme.med : Theme.text4; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: lane.st === "passed" ? "Found" : lane.st === "failed" ? "Missing at the deadline" : "Not seen yet"; elide: Text.ElideNone; font.pixelSize: 12
                          color: lane.st === "passed" ? Theme.text2 : lane.st === "failed" ? Theme.med : Theme.text4 }
                }
            }
            Item { width: 1; height: 8 }
            Canvas {
                id: strip
                width: root.width
                height: 22
                Connections { target: Theme; function onDarkChanged() { strip.requestPaint() } }
                onWidthChanged: requestPaint()
                Component.onCompleted: requestPaint()
                onPaint: {
                    var c = getContext("2d"); c.reset(); var w = width
                    c.fillStyle = Theme.surface2; c.fillRect(0, 5, w, 12)
                    if (root.over) { c.globalAlpha = 0.12; c.fillStyle = Theme.crit; c.fillRect(root.xAt(root.fin, w), 5, w - root.xAt(root.fin, w), 12); c.globalAlpha = 1 }
                    // signs of progress, binned along the task's clock
                    var nb = Math.max(24, Math.floor(w / 4)), bins = []
                    for (var k = 0; k < nb; k++) bins.push(0)
                    lane.sig.forEach(function (e) { var t = Time.ms(e.observed_at); if (t < root.a || t > root.end) return
                        bins[Math.min(nb - 1, Math.floor(((t - root.a) / (root.b - root.a)) * nb))] += 1 })
                    var mx = Math.max.apply(null, bins.concat([1]))
                    c.fillStyle = lane.modelData.target_type === "program" ? Theme.ser3 : Theme.ser2
                    for (var j = 0; j < nb; j++) if (bins[j] > 0) { c.globalAlpha = 0.25 + 0.75 * Math.min(1, bins[j] / mx); c.fillRect((j / nb) * w, 5, w / nb + 0.5, 12) }
                    c.globalAlpha = 1
                    root.marks.forEach(function (mk) {
                        c.strokeStyle = mk[2]; c.lineWidth = mk[0] === "Now" ? 1.5 : 1
                        if (mk[0] !== "Now") c.setLineDash([3, 2])
                        c.beginPath(); c.moveTo(root.xAt(mk[1], w), 1); c.lineTo(root.xAt(mk[1], w), 21); c.stroke(); c.setLineDash([])
                    })
                    if (lane.st === "passed") {
                        var first = lane.sig.length ? Math.min.apply(null, lane.sig.map(function (e) { return Time.ms(e.observed_at) })) : root.end
                        var fx = Math.max(7, Math.min(w - 7, root.xAt(first, w)))          // the whole mark stays on the strip, never half cut off at an edge
                        c.fillStyle = Theme.surface; c.strokeStyle = Theme.text; c.lineWidth = 1.5
                        c.beginPath(); c.arc(fx, 11, 5.5, 0, Math.PI * 2); c.fill(); c.stroke()
                        c.fillStyle = Theme.text; c.beginPath(); c.arc(fx, 11, 2.2, 0, Math.PI * 2); c.fill()
                    }
                }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.grid; y: parent.height - 1 }
        }
    }
    // the days along the bottom
    Item {
        width: root.width; height: 18
        Repeater {
            model: {
                var out = [], d0 = new Date(root.a); d0.setHours(0, 0, 0, 0)
                var step = root.b - root.a > 8 * 86400000 ? 2 : 1
                for (var t = d0.getTime() + 86400000; t <= root.b; t += step * 86400000) out.push(t)
                return out
            }
            Txt { required property var modelData; x: Math.max(0, Math.min(root.width - implicitWidth, root.xAt(modelData, root.width) - implicitWidth / 2)); y: 4
                  text: Time.sameDay(modelData, Time.now) ? "Today" : Time.dayName(modelData); mono: true; color: Theme.text3; font.pixelSize: 10; elide: Text.ElideNone }
        }
    }
    Row {
        topPadding: 8
        spacing: 14
        Repeater {
            model: [[Theme.ser2, "file activity", false], [Theme.ser3, "program in real use", false], [Theme.text, "found", true]]
            Row { required property var modelData; spacing: 6
                  Rectangle { width: 10; height: 10; radius: modelData[2] ? 5 : 2; color: modelData[0]; anchors.verticalCenter: parent.verticalCenter }
                  Txt { text: modelData[1]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
        }
        Txt { text: "darker is busier · nothing shaded means nothing seen"; color: Theme.text4; font.pixelSize: 12; elide: Text.ElideNone }
    }
    Column {
        topPadding: 14
        width: root.width
        spacing: 6
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        Txt { topPadding: 8; text: "HOW THESE ARE MEASURED"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
        Repeater {
            model: {
                if (!root.task) return []
                var seen = {}, out = []
                root.task.items.forEach(function (it) { var k = it.target_type === "program" ? "p:" + it.intent : "f"; if (!seen[k]) { seen[k] = 1; out.push(it) } })
                return out
            }
            Row {
                required property var modelData
                width: root.width
                spacing: 8
                Icon { name: modelData.target_type === "program" ? "appstore" : "file"; size: 13; color: Theme.text3 }
                Txt { width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: 12; textFormat: Text.RichText
                      text: "<span style='color:" + Theme.text2 + "'>" + (modelData.target_type === "program" ? "Programs" : "Files and folders") + ":</span> <span style='color:" + Theme.text3 + "'>" + root.measure(modelData)[1] + "</span>" }
            }
        }
    }
}
