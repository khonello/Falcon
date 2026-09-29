import QtQuick
import "."

// The state of a thing, as one mark. Hollow means quiet: free, unused, nothing recorded.
Rectangle {
    property string tone: "mid"
    property bool hollow: false
    width: 7
    height: 7
    radius: 4
    color: hollow ? "transparent" : Theme.tone(tone)
    border.width: hollow ? 1.5 : 0
    border.color: Theme.tone(tone)
}
