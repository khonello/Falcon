import QtQuick
import "."

// A ROW OF CARDS THAT PAGES IN PLACE (the concept's dv-pages): "1 to 5 of 18" at the left, "‹ 1 of 4 ›" at the right
// (dr-step: 12px in text-3, the steps 22px and borderless), 6px above.
Item {
    id: root
    property var of: null                       // a Paged: everything below is read from it, and a step moves it
    property int from: of ? of.from : 0
    property int to: of ? of.to : 0
    property int total: of ? of.total : 0
    property int pageNo: of ? of.pi : 0         // zero-based
    property int pages: of ? of.pages : 1
    visible: of ? of.more : true
    Connections { target: root; function onStep(d) { if (root.of) root.of.pg = root.of.pi + d } }
    property bool showCount: true
    property string noun: ""                    // what is counted: "1 to 5 of 9 runs"
    signal step(int d)
    height: 6 + 22

    Txt { visible: root.showCount; y: 6; height: 22; text: Theme.fmt(root.from) + " to " + Theme.fmt(root.to) + " of " + Theme.fmt(root.total) + (root.noun ? " " + root.noun : ""); color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
    Row {
        anchors.right: parent.right
        y: 6
        spacing: 6
        component Step: Rectangle {
            id: st
            property string glyph: "left"
            property bool on: true
            signal hit()
            width: 22; height: 22; radius: 4
            color: sa.containsMouse && on ? Theme.surface3 : "transparent"
            opacity: on ? 1 : 0.35
            Icon { anchors.centerIn: parent; name: st.glyph; size: 10; color: Theme.text2 }
            MouseArea { id: sa; anchors.fill: parent; hoverEnabled: true; enabled: st.on; cursorShape: st.on ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: st.hit() }
        }
        Step { objectName: "stepEarlier"; glyph: "left"; on: root.pageNo > 0; onHit: root.step(-1) }
        Txt { height: 22; text: (root.pageNo + 1) + " of " + root.pages; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
        Step { objectName: "stepLater"; glyph: "right"; on: root.pageNo < root.pages - 1; onHit: root.step(1) }
    }
}
