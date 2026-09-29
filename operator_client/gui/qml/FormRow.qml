import QtQuick
import "."

// One row of a Form: the label above, the control, and -- only once something has been tried -- what
// is wrong with it, in the same place the hint was. A required field is marked, not explained.
Column {
    id: root
    property string label: ""
    property bool required: false
    property string problem: ""
    property string hint: ""
    default property alias control: holder.data

    spacing: Theme.s1

    Row {
        spacing: 3
        Txt { text: root.label; tone: "mid"; font.pixelSize: Theme.fSmall }
        Txt { text: "*"; tone: "danger"; font.pixelSize: Theme.fSmall; visible: root.required }
    }
    Column { id: holder; width: root.width }
    Txt {
        width: root.width
        visible: root.problem !== "" || root.hint !== ""
        text: root.problem !== "" ? root.problem : root.hint
        tone: root.problem !== "" ? "danger" : "quiet"
        font.pixelSize: Theme.fSmall
        wrapMode: Text.WordWrap
        elide: Text.ElideNone
    }
}
