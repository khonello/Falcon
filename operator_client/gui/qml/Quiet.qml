import QtQuick
import "."

// NOTHING HERE, SAID QUIETLY (the concept's ib-quiet): an optional icon and a line in text-3 at 12.5, padded 6 0.
Item {
    id: root
    property string icon: ""
    property string text: ""
    width: parent ? parent.width : 300
    height: t.height + 12
    Icon { id: i; visible: root.icon !== ""; anchors.verticalCenter: parent.verticalCenter; name: root.icon; size: 13; color: Theme.text3 }
    Txt { id: t; y: 6; x: i.visible ? 21 : 0; width: parent.width - x; text: root.text; color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
}
