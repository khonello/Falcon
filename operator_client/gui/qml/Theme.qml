pragma Singleton

// Every colour, spacing step, radius and type size the Operator Client uses. Imported as
// `Theme.x` from every other file; nothing else invents its own values.
//
// The idiom is a monitoring console (ui-reference.md): near-black canvas, raised surfaces with
// hairline borders, and the data is the only bright thing on screen. Colour carries meaning, not
// decoration, and the vocabulary is small enough to learn from one legend:
//   accent   selected / active / mine
//   ok       free, completed, applied, connected
//   warn     careful: a deadline near, a pause, a pending consent, a traversal in progress
//   danger   blocked, violation, failed, the Super User is inside your view
//   assist   an assisted-access session (a peer helping by consent) -- distinct from traversal

import QtQuick

QtObject {
    // --- surfaces, back to front -------------------------------------------------------------
    readonly property color canvas:      "#0d1014"
    readonly property color surface:     "#141920"
    readonly property color surfaceHigh: "#1b212a"
    readonly property color overlay:     "#232b36"

    // --- lines ---------------------------------------------------------------------------------
    readonly property color border:       "#242c37"
    readonly property color borderStrong: "#333d4b"

    // --- text ----------------------------------------------------------------------------------
    readonly property color text:      "#e6ebf2"
    readonly property color textDim:   "#94a1b2"
    readonly property color textFaint: "#5d6b7c"

    // --- meaning -------------------------------------------------------------------------------
    readonly property color accent:    "#4c8dff"
    readonly property color accentDim: "#1e3a63"
    readonly property color ok:        "#3fb950"
    readonly property color warn:      "#d29922"
    readonly property color danger:    "#f04747"
    readonly property color assist:    "#b48cff"

    // A colour at low alpha, for a row or banner that carries that meaning.
    function wash(c, a) { return Qt.rgba(c.r, c.g, c.b, a === undefined ? 0.14 : a) }

    // Who someone is, at a glance, everywhere they appear.
    function roleTint(role) {
        return role === "super_user" ? danger : role === "admin" ? accent : textDim
    }
    function roleLabel(role) {
        return role === "super_user" ? "SUPER USER" : role === "admin" ? "ADMIN" : role === "worker" ? "WORKER" : ""
    }
    // The one colour vocabulary for "what state is this PC in".
    function sessionTint(session) {
        if (!session) return ok
        switch (session.occupied_via) {
        case "native": return textFaint
        case "assisted": return assist
        default: return warn
        }
    }

    // --- geometry ------------------------------------------------------------------------------
    readonly property int radius:      4
    readonly property int radiusLarge: 6

    readonly property int space1: 4
    readonly property int space2: 8
    readonly property int space3: 12
    readonly property int space4: 16
    readonly property int space5: 24

    readonly property int controlHeight: 30
    readonly property int rowHeight:     34
    readonly property int railWidth:     300

    // --- type ----------------------------------------------------------------------------------
    readonly property int fontTiny:   10
    readonly property int fontSmall:  11
    readonly property int fontBody:   12
    readonly property int fontMedium: 13
    readonly property int fontLarge:  15
    readonly property int fontHuge:   20

    readonly property string mono: "Consolas, 'Cascadia Mono', monospace"

    // --- motion: one curve, two durations -----------------------------------------------------
    readonly property int durationFast: 120
    readonly property int durationBase: 220
    readonly property int easing: Easing.OutCubic
}
