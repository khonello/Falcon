import QtQuick
import "."

// A page the concept draws whose port has not landed yet. It says so plainly rather than showing an
// older page under a new name.
Page {
    Panel {
        width: parent.width
        Empty {
            width: parent.width
            icon: "fieldtime"
            title: Nav.title(Nav.page) + " is being built to the concept"
            text: "This page lands in a later step of the port. Everything else in the menu works."
            h: 160
        }
    }
}
