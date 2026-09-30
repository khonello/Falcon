import QtQuick
import "."

// WHO IS IN CONTROL, when it is not simply you. One row on a red tint: no stripe down the left, no
// hairline on an edge, no second treatment -- this is the only banner in the console, and it says one
// of three things (hierarchy-system-design.md):
//
//   a Super User inside an Admin   "Super User in charge"  -- the red banner the design names
//   an Admin inside a worker PC    "You are inside OPS-03"
//   somebody inside YOUR session   "R. Mensah is in your session" -- the clock stays, because the
//                                  design says you always see how long is left on it, but the acts
//                                  go: there is nothing to do but wait
Rectangle {
    id: root
    property var session: null
    property string mode: "inside"        // inside | held
    property bool inCharge: false         // the Super User banner, which names itself
    property string who: ""               // whose, when somebody is in your session
    property string until: ""             // deadline, ISO
    property string since: ""             // entered_at, ISO
    signal leave()
    signal extend()

    property int tick: 0                   // the clock moves; the bindings read this

    readonly property real remaining: {
        void root.tick
        if (!until || !since) return 1
        var a = new Date(since).getTime(), b = new Date(until).getTime(), now = Date.now()
        if (!(b > a)) return 1
        return Math.max(0, Math.min(1, (b - now) / (b - a)))
    }
    readonly property int minutes: {
        void root.tick
        if (!until) return 0
        return Math.max(0, Math.round((new Date(until).getTime() - Date.now()) / 60000))
    }

    implicitHeight: 52
    color: Theme.dangerSoft
    border.width: 1
    border.color: "#ffccc7"
    radius: 0

    // the clock has to move, or the bar is a picture of one moment
    Timer { interval: 20000; running: root.visible && root.until !== ""; repeat: true
            onTriggered: root.tick++ }

    Icon {
        id: mark
        name: "lock"
        size: 16
        color: Theme.danger
        anchors.left: parent.left
        anchors.leftMargin: Theme.s4
        anchors.verticalCenter: parent.verticalCenter
    }
    Txt {
        id: what
        anchors.left: mark.right
        anchors.leftMargin: Theme.s2
        anchors.verticalCenter: parent.verticalCenter
        text: root.mode === "held"
              ? (root.who || "Somebody") + " is in your session"
              : root.inCharge ? "Super User in charge"
              : root.session && root.session.hostname ? "You are inside " + root.session.hostname
              : "You are inside somebody's machine"
        tone: "danger"
        strong: true
    }
    Txt {
        anchors.left: what.right
        anchors.leftMargin: Theme.s3
        anchors.right: bar.left
        anchors.rightMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter
        text: root.mode === "held"
              ? "You will have it back when they leave. You do not need to do anything."
              : root.inCharge && root.session && root.session.hostname
                ? "Everything here is answered as this Admin, and every act is logged as yours · "
                  + root.session.hostname
              : "They cannot use it until you leave"
        tone: "danger"
        font.pixelSize: Theme.fSmall
    }

    // a real bar, not a stripe: it is the clock, and it empties
    Rectangle {
        id: bar
        width: 160
        height: 6
        radius: 3
        color: "#ffccc7"
        visible: root.until !== ""
        anchors.right: clock.left
        anchors.rightMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter

        Rectangle {
            width: parent.width * root.remaining
            height: parent.height
            radius: parent.radius
            color: Theme.danger
            Behavior on width { NumberAnimation { duration: Theme.durBase } }
        }
    }
    Txt {
        id: clock
        anchors.right: acts.left
        anchors.rightMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter
        visible: root.until !== ""
        text: root.minutes + " min left"
        tone: "danger"
        mono: true
        font.pixelSize: Theme.fSmall
    }

    Row {
        id: acts
        visible: root.mode !== "held"
        spacing: Theme.s2
        anchors.right: parent.right
        anchors.rightMargin: Theme.s4
        anchors.verticalCenter: parent.verticalCenter

        Btn {
            objectName: "extendSession"
            small: true
            text: "Extend"
            visible: root.until !== ""
            onClicked: root.extend()
        }
        Btn {
            objectName: "leaveSession"
            kind: "primary"
            danger: true
            small: true
            text: "Leave"
            onClicked: root.leave()
        }
    }
}
