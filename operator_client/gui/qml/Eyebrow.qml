import QtQuick
import QtQuick.Controls
import "."

// A quiet uppercase letterspaced label: section names, column heads, rail headers.
Label {
    property string label: ""
    text: label.toUpperCase()
    color: Theme.textDim
    font.pixelSize: Theme.fontTiny
    font.bold: true
    font.letterSpacing: 1.1
}
