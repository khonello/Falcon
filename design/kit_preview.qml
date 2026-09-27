import QtQuick
import QtQuick.Controls
import "../operator_client/gui/qml"

// The shared kit, drawn by the real QML components, so the build can be checked against PATTERNS.md.
// Rendered offscreen by design/shot_kit.py.
ApplicationWindow {
    width: 1440
    height: 900
    visible: true
    color: Theme.frameSolid

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.frameA }
            GradientStop { position: 0.45; color: Theme.frameB }
            GradientStop { position: 1.0; color: Theme.frameC }
        }
    }

    Column {
        x: 40; y: 30
        spacing: 22

        Txt { text: "The kit — real QML components"; color: "#ffffff"; font.pixelSize: 22; font.weight: Font.Bold }

        Row {
            spacing: 20
            GridCell {
                width: 900; height: 250; title: "MachineMark in a PagedRow"; topAlign: true
                narration: ({ brief: "12 machines · one needs you", tone: "warn", state: "ok" })
                PagedRow {
                    width: parent.width; height: 150; itemWidth: 118
                    model: [
                        { n: "01", s: "ok", who: "Kojo", line: "at the PC" }, { n: "02", s: "free", who: "Efua", line: "free" },
                        { n: "03", s: "ok", who: "Yaw", line: "at the PC" }, { n: "04", s: "entered", who: "Adjoa", line: "you entered it", t: "warn" },
                        { n: "05", s: "ok", who: "Nana", line: "at the PC" }, { n: "06", s: "warn", who: "Kwame", line: "a version behind", t: "warn" },
                        { n: "07", s: "ok", who: "Ama", line: "at the PC" }, { n: "08", s: "ok", who: "Kofi", line: "at the PC" },
                        { n: "09", s: "ok", who: "Esi", line: "at the PC" }, { n: "10", s: "ok", who: "Abena", line: "at the PC" },
                        { n: "11", s: "danger", who: "Akua", line: "a file out of place", t: "danger" }, { n: "12", s: "ok", who: "Kwesi", line: "at the PC" }]
                    attention: function (m) { return m.s === "danger" ? "OPS-" + m.n : "" }
                    delegate: MachineMark {
                        property var modelData: ({})
                        size: 84; label: modelData.n || ""; status: modelData.s || "ok"
                        name: modelData.who || ""; line: modelData.line || ""; lineTone: modelData.t || ""
                    }
                }
            }
            GridCell {
                width: 420; height: 250; title: "InfoCard in a PagedColumn"; topAlign: true
                narration: ({ brief: "five things", tone: "danger", state: "ok" })
                PagedColumn {
                    width: parent.width; height: 180; itemHeight: 58
                    model: [
                        { i: "shield", t: "danger", a: "A restricted file on OPS-07", b: "budget-2026.xlsx · 11:41", w: "new" },
                        { i: "clock", t: "danger", a: "Ama's report is overdue", b: "final deadline was yesterday", w: "" },
                        { i: "reports", t: "warn", a: "A report routed here", b: "flow failure · OPS-03", w: "open" },
                        { i: "ping", t: "warn", a: "Kojo pinged twice", b: "OPS-01", w: "answer", bad: true }]
                    attention: function (m) { return m.bad ? "Kojo pinged" : "" }
                    delegate: InfoCard {
                        iconName: modelData ? modelData.i : ""; iconTone: modelData ? modelData.t : "accent"
                        title: modelData ? modelData.a : ""; line: modelData ? modelData.b : ""
                        stateWord: modelData ? modelData.w : ""; stateTone: modelData ? modelData.t : ""
                    }
                }
            }
        }

        Row {
            spacing: 20
            GridCell {
                width: 900; height: 300; title: "FlowTree"; topAlign: true
                narration: ({ brief: "one branch paused", tone: "danger", state: "ok" })
                FlowTree {
                    width: parent.width; height: 220
                    nodes: [
                        { id: "s", x: 0, y: 87, w: 190, icon: "folder", label: "OPS-02", sub: "Raw submissions · source" },
                        { id: "p", x: 250, y: 20, w: 160, icon: "file", label: "Make PDF", sub: "transform", tone: "warn" },
                        { id: "c", x: 460, y: 20, w: 160, icon: "folder", label: "Sort by type", sub: "categorize", tone: "warn" },
                        { id: "a", x: 680, y: 0, w: 160, icon: "monitor", label: "Archive", sub: "synced 11:40", tone: "ok" },
                        { id: "b", x: 680, y: 56, w: 160, icon: "monitor", label: "Backup", sub: "synced 11:40", tone: "ok" },
                        { id: "q", x: 250, y: 160, w: 160, icon: "file", label: "Make PDF", sub: "failed at 11:20", bad: true },
                        { id: "w", x: 680, y: 160, w: 160, icon: "monitor", label: "WS-OPS-A1", sub: "paused, not stale", bad: true }]
                    links: [{ from: "s", to: "p" }, { from: "p", to: "c" }, { from: "c", to: "a" }, { from: "c", to: "b" },
                            { from: "s", to: "q", bad: true }, { from: "q", to: "w", bad: true }]
                }
            }
            GridCell {
                width: 420; height: 300; title: "InfoCard, SentenceSlot, tabs"; topAlign: true
                narration: ({ brief: "", state: "ok" })
                Column {
                    width: parent.width; spacing: 12
                    SegmentedControl { segments: [{ text: "Tree" }, { text: "Sentence" }, { text: "Card" }] }
                    InfoCard { width: parent.width; initials: "AQ"; title: "A. Quaye"; line: "helping Finance since 10:40"; lineTone: "accent" }
                    InfoCard { width: parent.width; initials: "RM"; title: "R. Mensah"; line: "at their workstation"; selected: true; stateWord: "selected" }
                    Flow {
                        width: parent.width; spacing: 6
                        Txt { text: "Copy"; color: Theme.dim; font.pixelSize: Theme.fRow; height: 26; verticalAlignment: Text.AlignVCenter }
                        SentenceSlot { text: "Raw submissions" }
                        Txt { text: "to"; color: Theme.dim; font.pixelSize: Theme.fRow; height: 26; verticalAlignment: Text.AlignVCenter }
                        SentenceSlot { text: "Archive"; tone: "ok" }
                        SentenceSlot { text: "+ then…"; dashed: true }
                    }
                }
            }
        }
    }
}
