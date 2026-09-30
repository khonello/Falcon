import QtQuick
import "."

// THE KIT, DRAWN IN ITSELF. The same board as the published Console Kit, but made of the real QML
// components rather than of antd -- so what you are judging is what ships. Reached only from the
// preview script (`scripts/preview.py --view kit`); it is not an area of the console.
Item {
    id: root

    // the frame every item sits in, so the page reads as an inventory and not as a demo
    component Piece: Rectangle {
        id: piece
        property string name: ""
        property string use: ""
        property string mark: "P0"
        default property alias body: inner.data

        width: parent ? parent.width : 0
        height: head.height + inner.implicitHeight + 2 * Theme.s4
        radius: Theme.radiusLg
        color: Theme.surface
        border.width: 1
        border.color: Theme.split

        Rectangle {
            id: head
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 38
            radius: Theme.radiusLg
            color: Theme.fill
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: Theme.radiusLg
                color: Theme.fill
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.split }

            Txt {
                id: nm
                anchors.left: parent.left
                anchors.leftMargin: Theme.s4
                anchors.verticalCenter: parent.verticalCenter
                text: piece.name
                strong: true
                font.pixelSize: Theme.fSmall
            }
            Txt {
                anchors.left: nm.right
                anchors.leftMargin: Theme.s3
                anchors.right: tag.left
                anchors.rightMargin: Theme.s3
                anchors.verticalCenter: parent.verticalCenter
                text: piece.use
                tone: "mid"
                font.pixelSize: Theme.fSmall
            }
            Tag {
                id: tag
                anchors.right: parent.right
                anchors.rightMargin: Theme.s4
                anchors.verticalCenter: parent.verticalCenter
                text: piece.mark
            }
        }
        Column {
            id: inner
            anchors.top: head.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: Theme.s4
            spacing: Theme.s3
        }
    }

    component Head: Column {
        property string title: ""
        property string note: ""
        width: parent ? parent.width : 0
        spacing: 2
        topPadding: Theme.s5
        Txt { text: parent.title; strong: true; font.pixelSize: Theme.fTitle }
        Txt { text: parent.note; tone: "mid"; font.pixelSize: Theme.fSmall }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: page.implicitHeight + 2 * Theme.s5
        clip: true

        Column {
            id: page
            x: Theme.s5
            y: Theme.s5
            width: root.width - 2 * Theme.s5
            spacing: Theme.s3

            PageHeader {
                width: parent.width
                title: "The kit"
                subtitle: "Every component the console is made of, drawn in itself"
            }

            // ---------------------------------------------------------------- colour
            Head { title: "1 \u00b7 Colour"; note: "Tone carries information; hue carries urgency, and only twice." }
            Piece {
                name: "The ladder"
                use: "Three tones of ink, two hues that mean somebody must act"
                Repeater {
                    model: [["quiet", "Quiet", "free, unused, nothing recorded"],
                            ["mid", "Present", "at the PC, running, syncing \u2014 most of the screen"],
                            ["ink", "The subject", "the row you picked, the count that matters"],
                            ["warn", "Will need someone", "a version behind, waiting for a yes"],
                            ["danger", "Needs someone now", "a file out of place, an update past the limit"]]
                    delegate: Row {
                        required property var modelData
                        width: parent.width
                        spacing: Theme.s3
                        Rectangle {
                            width: 44; height: 20; radius: Theme.radiusSm
                            color: Theme.tone(modelData[0])
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Txt { width: 150; text: modelData[1]; strong: true; font.pixelSize: Theme.fSmall
                              anchors.verticalCenter: parent.verticalCenter }
                        Txt { text: modelData[2]; tone: "mid"; font.pixelSize: Theme.fSmall
                              anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }

            // ---------------------------------------------------------------- general
            Head { title: "2 \u00b7 General"; note: "The vocabulary every screen uses." }
            Piece {
                name: "Btn"
                use: "One primary per page. At most two words \u2014 it names the act"
                Flow {
                    width: parent.width
                    spacing: Theme.s2
                    Btn { kind: "primary"; text: "New task" }
                    Btn { text: "Cancel" }
                    Btn { kind: "primary"; danger: true; text: "End session" }
                    Btn { danger: true; text: "Retire" }
                    Btn { kind: "text"; text: "Skip" }
                    Btn { kind: "link"; text: "Open trail" }
                    Btn { kind: "primary"; loading: true; text: "Asking" }
                    Btn { small: true; text: "Small" }
                    Btn { enabled: false; text: "Enter" }
                }
            }
            Piece {
                name: "Txt \u00b7 Tag \u00b7 Dot \u00b7 Avatar \u00b7 Count"
                use: "Type, status, a person, a number that needs somebody"
                mark: "P0"
                Column {
                    width: parent.width
                    spacing: Theme.s2
                    Txt { text: "Operations"; strong: true; font.pixelSize: Theme.fTitle }
                    Txt { text: "Seven machines, two Admins."; tone: "mid" }
                    Flow {
                        width: parent.width
                        spacing: Theme.s2
                        Tag { text: "on 1.4.2" }
                        Tag { text: "free" }
                        Tag { text: "a version behind"; tone: "warn" }
                        Tag { text: "a file out of place"; tone: "danger" }
                        Avatar { name: "R. Mensah" }
                        Avatar { name: "A. Quaye"; muted: true }
                        Count { value: 3 }
                        Count { value: 128; tone: "warn" }
                        Spin { }
                    }
                    Divider { text: "and a divider says where a block ends" }
                }
            }

            // ---------------------------------------------------------------- navigation
            Head { title: "3 \u00b7 Navigation"; note: "The sider is the only navigation. These say depth and order." }
            Piece {
                name: "Crumb \u00b7 Tabs \u00b7 Steps"
                use: "Where you are, what else is about this subject, and how far through"
                mark: "P0 \u00b7 P1"
                Column {
                    width: parent.width
                    spacing: Theme.s4
                    Crumb { path: ["Falcon", "Departments", "Operations", "R. Mensah"] }
                    Tabs {
                        width: parent.width
                        current: "checks"
                        tabs: [{ key: "checks", label: "Checks" }, { key: "files", label: "Files", count: 2 },
                               { key: "history", label: "History" }]
                    }
                    Steps { width: parent.width; current: 1; steps: ["When", "Where", "Do"] }
                }
            }
            Piece {
                name: "RowMenu \u00b7 Pagination"
                use: "The acts on one row without opening it; and the position, always in words"
                Row {
                    width: parent.width
                    spacing: Theme.s5
                    RowMenu {
                        anchors.verticalCenter: parent.verticalCenter
                        items: [{ key: "enter", label: "Enter" }, { key: "run", label: "Run action" },
                                { key: "off", label: "Offboard", danger: true, divided: true }]
                    }
                    Pagination { total: 284; pageSize: 20; anchors.verticalCenter: parent.verticalCenter }
                }
            }

            // ---------------------------------------------------------------- data entry
            Head { title: "4 \u00b7 Data entry"; note: "Nothing typed that can be picked." }
            Piece {
                name: "Field \u00b7 Search \u00b7 Secret \u00b7 Area"
                use: "Words, a table's search, a key that should not sit on screen, several lines"
                Column {
                    width: parent.width
                    spacing: Theme.s3
                    Row {
                        spacing: Theme.s3
                        Field { width: 200; placeholderText: "OPS-08" }
                        Search { width: 220; placeholder: "Search the record" }
                        Secret { width: 260; text: "3f9c1a7e2b4d6058"; placeholder: "Client key" }
                    }
                    Area { width: parent.width; placeholderText: "Reconcile the Q3 invoices by Friday" }
                }
            }
            Piece {
                name: "Select \u00b7 TreeSelect \u00b7 Suggest"
                use: "One of a few; one out of the hierarchy; one out of thousands, typed"
                Row {
                    width: parent.width
                    spacing: Theme.s3
                    Select {
                        width: 200
                        value: "ops"
                        options: [{ value: "ops", label: "Operations" }, { value: "fin", label: "Finance" }]
                    }
                    TreeSelect {
                        width: 240
                        placeholder: "Pick a folder"
                        nodes: [{ key: "ops", label: "Operations", depth: 0, kids: true, pickable: false },
                                { key: "w", label: "/workers/", depth: 1 },
                                { key: "r", label: "/restricted/", depth: 1 },
                                { key: "c", label: "/common/", depth: 1 }]
                    }
                    Suggest {
                        width: 220
                        placeholder: "A file name"
                        options: ["budget-2026.xlsx", "reconciliation.xlsx", "q3-summary.docx"]
                    }
                }
            }
            Piece {
                name: "Check \u00b7 Radio \u00b7 Toggle \u00b7 Num \u00b7 TimeField"
                use: "Several, one of a few shown in full, on/off, a number with its unit, a time of day"
                mark: "P0 \u00b7 P1"
                Column {
                    width: parent.width
                    spacing: Theme.s4
                    Row {
                        spacing: Theme.s5
                        Column {
                            spacing: Theme.s2
                            Check { text: "Warn before it runs"; checked: true }
                            Check { text: "Run on idle only" }
                            Check { text: "Every machine"; partial: true }
                        }
                        Radio {
                            width: 280
                            value: "stack"
                            options: [{ value: "stack", label: "Watch for the lines above",
                                        hint: "The Engine watches; only you close the task." },
                                      { value: "none", label: "Nothing to check",
                                        hint: "You are saying so on purpose." }]
                        }
                    }
                    Row {
                        spacing: Theme.s4
                        Toggle { on: true; anchors.verticalCenter: parent.verticalCenter }
                        Txt { text: "Automation is on"; anchors.verticalCenter: parent.verticalCenter }
                        Num { width: 150; value: 30; from: 1; to: 600; unit: "s" }
                        TimeField { hour: 18; minute: 30 }
                    }
                }
            }
            Piece {
                name: "DateRange \u00b7 Level \u00b7 Upload \u00b7 Transfer"
                use: "A span of days, a threshold against what is normal, a file, two lists and a direction"
                mark: "P0 \u00b7 P2"
                Column {
                    width: parent.width
                    spacing: Theme.s4
                    Row {
                        spacing: Theme.s4
                        DateRange { }
                        Level { width: 300; value: 0.85 }
                    }
                    Row {
                        width: parent.width
                        spacing: Theme.s4
                        Upload { width: 240 }
                        Transfer {
                            width: parent.width - 240 - Theme.s4
                            height: 160
                            leftTitle: "Not watched"
                            rightTitle: "Watched"
                            chosen: [1, 3]
                            all: [{ key: 1, label: "OPS-01" }, { key: 2, label: "OPS-02" },
                                  { key: 3, label: "OPS-03" }, { key: 4, label: "FIN-01" }]
                        }
                    }
                }
            }

            // ---------------------------------------------------------------- data display
            Head { title: "5 \u00b7 Data display"; note: "The Table is the backbone. Everything else supports it." }
            Piece {
                name: "Table"
                use: "Sort, filter, select, page \u2014 and a MachineCell in the first column"
                Table {
                    width: parent.width
                    height: 210
                    pageSize: 4
                    selectable: true
                    rows: [{ host: "OPS-01", who: "Kojo", state: "fine", line: "at the PC" },
                           { host: "OPS-02", who: "Efua", state: "free", line: "nobody on it" },
                           { host: "OPS-06", who: "Kwame", state: "behind", line: "a version behind" },
                           { host: "LOG-02", who: "Abena", state: "needs you", line: "update past the limit" }]
                    columns: [{ title: "Machine", key: "host", width: 140, mono: true, strong: true },
                              { title: "State", key: "state", width: 130, tag: true,
                                filters: ["fine", "free", "behind", "needs you"],
                                tone: function (r) { return r.state === "needs you" ? "danger"
                                                     : r.state === "behind" ? "warn" : "" } },
                              { title: "Why", key: "line",
                                tone: function (r) { return r.state === "needs you" ? "danger"
                                                     : r.state === "behind" ? "warn" : "mid" } },
                              { title: "Signed in", key: "who", width: 130 }]
                }
            }
            Piece {
                name: "Descriptions \u00b7 Statistic \u00b7 Progress \u00b7 Trail"
                use: "Label and value read down; one figure; how far through; what happened to one subject"
                Row {
                    width: parent.width
                    spacing: Theme.s5
                    Column {
                        width: (parent.width - Theme.s5) / 2
                        spacing: Theme.s3
                        Descriptions {
                            width: parent.width
                            items: [{ label: "Department", value: "Operations" },
                                    { label: "Signed in", value: "Yaw" },
                                    { label: "Version", value: "1.4.2", mono: true },
                                    { label: "State", value: "a file out of place", tag: true, tone: "danger" }]
                        }
                        Row {
                            spacing: Theme.s5
                            Statistic { label: "Machines"; value: "14" }
                            Statistic { label: "Behind"; value: "2"; tone: "warn"; note: "of eleven" }
                            Statistic { label: "Waiting on you"; value: "3"; tone: "danger" }
                        }
                        Progress { width: parent.width; value: 0.82; caption: "9 of 11 on 1.4.2" }
                    }
                    Trail {
                        width: (parent.width - Theme.s5) / 2
                        items: [{ at: "10:02", text: "budget-2026.xlsx found here", tone: "danger" },
                                { at: "09:40", text: "Yaw signed in" },
                                { at: "08:30", text: "Updated to 1.4.2" }]
                    }
                }
            }
            Piece {
                name: "Tree \u00b7 Collapse \u00b7 Feed"
                use: "The hierarchy as a list; what most people need not see; the one place a table is wrong"
                mark: "P1"
                Row {
                    width: parent.width
                    spacing: Theme.s5
                    Column {
                        width: (parent.width - Theme.s5) / 2
                        spacing: Theme.s3
                        Tree {
                            width: parent.width
                            open: ({ ops: true })
                            current: "ops-01"
                            nodes: [{ key: "ops", label: "Operations", sub: "7 machines", depth: 0, kids: true },
                                    { key: "rm", label: "R. Mensah", sub: "Admin", depth: 1 },
                                    { key: "ops-01", label: "OPS-01", sub: "Kojo", depth: 1 },
                                    { key: "fin", label: "Finance", sub: "2 machines", depth: 0, kids: true },
                                    { key: "kb", label: "K. Boateng", sub: "Admin", depth: 1 }]
                        }
                        Collapse {
                            width: parent.width
                            title: "Advanced"
                            open: true
                            Txt { text: "Run only when the machine is idle."; tone: "mid"
                                  font.pixelSize: Theme.fSmall }
                        }
                    }
                    Feed {
                        width: (parent.width - Theme.s5) / 2
                        items: [{ who: "Ama", body: "The payroll folder will not open on OPS-07.", at: "09:40" },
                                { who: "You", mine: true, body: "Which error does it give you?", at: "09:44" },
                                { who: "Ama", body: "Access denied, straight away.", at: "09:46" }]
                    }
                }
            }
            Piece {
                name: "Empty \u00b7 Skeleton \u00b7 Tip \u00b7 Popover"
                use: "Nothing yet; the first reply outstanding; the full value; a summary without a page"
                Row {
                    width: parent.width
                    spacing: Theme.s5
                    Empty {
                        width: 260
                        text: "No machines yet"
                        hint: "A machine appears here once it is registered."
                    }
                    Skeleton { width: 240; rows: 4 }
                    Column {
                        spacing: Theme.s3
                        Btn {
                            id: tipped
                            text: "Hover me"
                            Tip { text: "budget-2026.xlsx \u00b7 found on OPS-07"; over: tipped }
                        }
                        Btn {
                            text: "Popover"
                            onClicked: peek.open()
                            Popover {
                                id: peek
                                title: "OPS-03"
                                y: 36
                                Txt { text: "Yaw, since 09:40"; tone: "mid"; font.pixelSize: Theme.fSmall }
                                Txt { text: "A file out of place"; tone: "danger"; font.pixelSize: Theme.fSmall }
                            }
                        }
                    }
                }
            }

            // ---------------------------------------------------------------- feedback
            Head { title: "6 \u00b7 Feedback"; note: "What happened, what is about to, and what went wrong." }
            Piece {
                name: "Alert \u00b7 Msg \u00b7 Popconfirm \u00b7 Result"
                use: "One line three ways; the result of an act; a small cost named in place; a dead end with a way out"
                Column {
                    width: parent.width
                    spacing: Theme.s3
                    Alert { width: parent.width; kind: "note"; text: "Nothing is transformed on the way." }
                    Alert { width: parent.width; kind: "warn"; text: "Some of this was a guess. Read every line." }
                    Alert { width: parent.width; kind: "danger"
                            text: "The destination folder is gone. Make it, or point the flow somewhere else." }
                    Row {
                        spacing: Theme.s3
                        Btn { text: "Say something"; onClicked: Msg.ok("Task assigned") }
                        Btn { text: "Something arrived"
                              onClicked: Msg.urgent("Kojo", "asked for you, twice") }
                        Btn {
                            id: asker
                            danger: true
                            text: "Pause"
                            onClicked: small.open()
                            Popconfirm {
                                id: small
                                y: 36
                                destructive: true
                                verb: "Pause"
                                cost: "It stops copying until somebody resumes it."
                            }
                        }
                    }
                    Result {
                        width: parent.width
                        height: 190
                        kind: "danger"
                        title: "Not connected"
                        hint: "The Engine did not answer on 127.0.0.1:7400. Nothing here is live."
                        Btn { kind: "primary"; text: "Reconnect" }
                        Btn { text: "Settings" }
                    }
                }
            }

            // ---------------------------------------------------------------- Falcon's own
            Head { title: "7 \u00b7 Falcon's own"; note: "Ant Design has no vocabulary for these; they are the product." }
            Piece {
                name: "SessionBanner"
                use: "You are inside somebody's machine: whose, which, how long is left, the way out"
                SessionBanner {
                    width: parent.width
                    inCharge: true
                    session: ({ hostname: "ADM-01" })
                    // relative to now, so the clock on the board always reads like a live one
                    since: new Date(Date.now() - 20 * 60000).toISOString()
                    until: new Date(Date.now() + 40 * 60000).toISOString()
                }
            }
            Piece {
                name: "MachineCell \u00b7 FleetGrid"
                use: "A machine in a row; and the whole department at a glance"
                Column {
                    width: parent.width
                    spacing: Theme.s3
                    FleetGrid {
                        width: parent.width
                        height: 130
                        machines: [{ host: "OPS-01", department: "Operations", state: "ok", stateWord: "fine" },
                                   { host: "OPS-02", department: "Operations", state: "free", stateWord: "free" },
                                   { host: "OPS-06", department: "Operations", state: "warn", stateWord: "behind" },
                                   { host: "OPS-07", department: "Operations", state: "danger", stateWord: "needs you" },
                                   { host: "FIN-01", department: "Finance", state: "ok", stateWord: "fine" },
                                   { host: "LOG-02", department: "Logistics", state: "danger", stateWord: "needs you" }]
                    }
                }
            }
            Piece {
                name: "FlowGraph"
                use: "Source, where it lands, and the branch that broke"
                FlowGraph {
                    width: parent.width
                    source: "OPS-07"
                    sourcePath: "C:/reports/weekly"
                    destinations: [{ destination_hostname: "LOG-01", destination_path: "D:/handover/weekly",
                                     suggestion: "The destination folder is gone." },
                                   { destination_hostname: null, destination_path: "//archive/weekly" }]
                }
            }
            Piece {
                name: "ScriptPanel"
                use: "A custom action's script and what is wrong with it"
                mark: "P2"
                ScriptPanel {
                    width: parent.width
                    readOnly: true
                    language: "python"
                    text: "import os, time, shutil\ncut = time.time() - 7 * 86400\nroot = os.environ['TEMP']"
                }
            }

            Item { width: 1; height: Theme.s6 }
        }
    }
}
