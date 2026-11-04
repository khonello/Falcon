import QtQuick
import "."

// WHAT A RUN RETURNED, machine by machine (the concept's OutputModal). Several machines: the list on the left, worst
// first; one machine: its output alone. `show` takes { action, at, from, xs: [run] }, each run as actions.runs answers it.
Modal {
    id: root
    property var run: null
    property string host: ""
    width: 1040
    readonly property var xs: run ? run.xs.filter(bad).concat(run.xs.filter(function (y) { return !bad(y) })) : []
    readonly property var cur: xs.filter(function (y) { return y.host === root.host })[0] || xs[0] || null
    readonly property var who: cur ? Fleet.byHost[cur.host] || {} : {}
    readonly property bool many: xs.length > 1
    title: run ? run.action : ""
    titleNote: run ? (many ? xs.length + " machines" : xs.length ? xs[0].host : "") + " · " + (Time.sameDay(Time.ms(run.at), Time.now) ? "today " : Time.dayName(run.at) + " ") + Time.hhmm(run.at) + " · " + run.from : ""

    function bad(y) { return Auto.problem(y.outcome) }
    function word(y) { return y.outcome === "Success" ? "worked" : y.outcome === "Timed out" ? "ran out of time" : y.outcome === "Failed" ? "failed" : String(y.outcome).toLowerCase() }
    function show(r) { run = r; host = (r.xs.filter(bad)[0] || r.xs[0]).host; open() }

    Item {
        width: root.width - 48
        height: Math.max(360, main.height)
        Column {
            id: list
            visible: root.many
            width: 168
            spacing: 2
            Repeater {
                model: root.xs
                delegate: Rectangle {
                    required property var modelData
                    width: list.width; height: 33; radius: 6
                    color: root.cur && root.cur.host === modelData.host ? Theme.surface3 : ha.containsMouse ? Theme.surface2 : "transparent"
                    Txt { x: 8; anchors.verticalCenter: parent.verticalCenter; text: modelData.host; mono: true; elide: Text.ElideNone }
                    Txt { anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 13; elide: Text.ElideNone
                          text: root.word(modelData); color: root.bad(modelData) ? Theme.crit : Theme.text3 }
                    MouseArea { id: ha; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.host = modelData.host }
                }
            }
        }
        Rectangle { visible: root.many; x: 180; width: 1; height: parent.height; color: Theme.border }
        Column {
            id: main
            x: root.many ? 200 : 0
            width: parent.width - x
            spacing: 12
            Item {
                width: parent.width
                height: 20
                Txt { id: mh; text: root.cur ? root.cur.host : ""; mono: true; font.weight: Font.Bold; elide: Text.ElideNone }
                Txt { x: mh.implicitWidth + 12; y: mh.baselineOffset - baselineOffset; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone
                      text: root.who.user ? root.who.user + " signed in" : "nobody signed in" }
                Row {
                    anchors.right: parent.right
                    spacing: 12
                    Txt { text: root.cur ? root.word(root.cur) : ""; color: root.cur && root.bad(root.cur) ? Theme.crit : Theme.ok; font.pixelSize: 13; elide: Text.ElideNone }
                    Txt { color: Theme.text3; mono: true; font.pixelSize: 13; elide: Text.ElideNone
                          text: root.cur ? "exit " + (root.cur.outcome === "Success" ? 0 : root.cur.exit || 1) + " · " + (root.cur.took_s || 0) + "s of " + root.cur.limit_s + "s" : "" }
                }
            }
            RunOutput { id: ro; width: parent.width; executionId: root.visible && root.cur ? root.cur.run_id : 0; wide: true }
            Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12
                  text: (ro.ex && ro.ex.summary ? ro.ex.summary + ". " : "") + "Kept with the run for 90 days; who opens it is recorded." }
        }
    }
}
