import QtQuick
import "."

// A TIME OF DAY, as two numbers rather than as text to be parsed. An automation that fires at 18:30
// should be set by saying 18 and 30, not by typing a string somebody has to validate.
Row {
    id: root
    property int hour: 9
    property int minute: 0
    property int step: 5
    signal changed(int hour, int minute)

    readonly property string value: (hour < 10 ? "0" : "") + hour + ":" + (minute < 10 ? "0" : "") + minute
    spacing: Theme.s2

    Num {
        width: 96
        value: root.hour
        from: 0
        to: 23
        unit: "h"
        onChanged: function (v) { root.hour = v; root.changed(root.hour, root.minute) }
    }
    Num {
        width: 104
        value: root.minute
        from: 0
        to: 59
        step: root.step
        unit: "min"
        onChanged: function (v) { root.minute = v; root.changed(root.hour, root.minute) }
    }
    Txt {
        text: root.value
        tone: "quiet"
        mono: true
        font.pixelSize: Theme.fSmall
        anchors.verticalCenter: parent.verticalCenter
    }
}
