import QtQuick
import "."

// TWO PAGES THAT ARE ONE: the tabs across the top of a page whose sibling the menu does not list (Departments and its Machines and
// accounts, Automation and its Actions). A tab is a page of its own; the menu entry of the pair stays lit on either.
Item {
    id: root
    property var options: []
    property string current: ""
    width: parent ? parent.width : 0
    height: 30
    Segmented { objectName: "pageTabs"; value: root.current; options: root.options; onPicked: function (v) { if (v !== root.current) Nav.go(v) } }
}
