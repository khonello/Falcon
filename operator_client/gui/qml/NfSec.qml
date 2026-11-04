import QtQuick
import "."

// A question in a stepped editor (nfv-sec): the question, a line on it, and what answers it. The first in a step has none of the space above.
Column {
    id: root
    property string title: ""
    property string optional: ""
    property string note: ""
    property bool first: false
    width: parent ? parent.width : 0
    spacing: 8
    topPadding: first ? 0 : 10
    bottomPadding: first ? 8 : 0
    Txt { visible: root.title !== ""; width: parent.width; font.pixelSize: 13; font.weight: Font.DemiBold; textFormat: Text.StyledText
          text: root.title + (root.optional ? " <font color='" + Theme.text4 + "'>" + root.optional + "</font>" : "") }
    Txt { visible: root.note !== ""; width: parent.width; text: root.note; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone }
}
