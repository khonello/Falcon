import QtQuick
import "."

// A SECTION A CLICK CHANGED PULSES ONCE (the user, 1 Nov 2026), so the eye goes to what changed. Laid over the section,
// it draws nothing until `key` changes; never on the first draw, never while `Theme.pulseOn` is off. A card that was picked
// pulses as a card (`radius` follows the card).
Rectangle {
    id: root
    property var key: null
    property bool armed: false
    anchors.fill: parent
    radius: Theme.radius
    color: "transparent"
    border.width: 2
    border.color: Theme.alpha(Theme.accent, 0.55)
    opacity: 0
    z: 50

    onKeyChanged: {
        if (!armed) { armed = true; return }
        if (key === null || key === undefined || !Theme.pulseOn) return
        flash.restart()
    }
    Component.onCompleted: armed = key !== null && key !== undefined

    SequentialAnimation {
        id: flash
        NumberAnimation { target: root; property: "opacity"; from: 0; to: 1; duration: Theme.pulseMs * 0.25; easing.type: Easing.OutQuad }
        NumberAnimation { target: root; property: "opacity"; from: 1; to: 0; duration: Theme.pulseMs * 0.75; easing.type: Easing.InQuad }
    }
}
