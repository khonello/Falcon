import QtQuick
import "."

// Every piece of text goes through here, so the type scale is stated once.
Text {
    property bool monospace: false
    color: Theme.ink
    font.family: monospace ? Theme.monoFamily : Theme.sans
    font.pixelSize: Theme.fBody
    renderType: Text.NativeRendering
    elide: Text.ElideRight
    verticalAlignment: Text.AlignVCenter
}
