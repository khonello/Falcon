import QtQuick
import "."

// DETECTIVE: a place held in the menu while it is decided what it is. Nothing here works yet, and the page says so rather than showing something else.
Page {
    objectName: "detectiveView"
    Panel {
        width: parent.width
        Empty {
            width: parent.width
            icon: "filesearch"
            title: "Detective is not built yet"
            text: "This page is held while its place in the menu is decided."
            h: 160
        }
    }
}
