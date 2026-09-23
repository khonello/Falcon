pragma Singleton

// Every colour, space, radius and type size the Operator Client uses, stated once.
//
// The language (design canvas, "The language" board): one gradient frame that never changes, dark
// surfaces on top of it, and four toned meanings. Colour says state and nothing else -- a person is
// never a colour, a border is a toned variation of a core colour, never a new hue.

import QtQuick

QtObject {
    // --- the frame: one gradient, always ------------------------------------------------------
    readonly property color frameA: "#121220"          // ink, top left
    readonly property color frameB: "#2A1F50"          // 45 %
    readonly property color frameC: "#4B2F8A"          // violet, bottom right
    readonly property color frameSolid: "#1A1626"      // where a gradient cannot go

    // --- surfaces -----------------------------------------------------------------------------
    readonly property color ground: "#12151C"          // inside a card, a container, an input
    readonly property color pane: "#1B2028"            // the sheet, the detail card
    readonly property color side: "#171C25"            // the sidebar

    // --- lines and text -----------------------------------------------------------------------
    readonly property color line: "#2A313C"
    readonly property color line2: "#3B4450"
    readonly property color ink: "#E8ECF2"
    readonly property color dim: "#A6B0BC"
    readonly property color faint: "#7D8896"

    // --- four meanings, toned -----------------------------------------------------------------
    readonly property color accent: "#8AA6E0"          // selected, yours, the primary action
    readonly property color ok: "#7FB396"              // free, done, synced, confirmed
    readonly property color warn: "#D2A468"            // careful: a deadline, a pause, a session running
    readonly property color danger: "#DD8A8A"          // blocked, violation, failed, occupied

    readonly property color accentSoft: Qt.rgba(0.541, 0.651, 0.878, 0.14)
    readonly property color okSoft: Qt.rgba(0.498, 0.702, 0.588, 0.14)
    readonly property color warnSoft: Qt.rgba(0.824, 0.643, 0.408, 0.15)
    readonly property color dangerSoft: Qt.rgba(0.867, 0.541, 0.541, 0.14)

    // bands and destructive fills stay the deep solids: white text must hold on them
    readonly property color warnDeep: "#B4650A"
    readonly property color dangerDeep: "#B92828"
    readonly property color assistDeep: "#0E6E77"

    // --- selection ----------------------------------------------------------------------------
    readonly property color select: "#33446B"                                   // a selected sidebar row
    readonly property color selectSub: Qt.rgba(1, 1, 1, 0.68)
    readonly property color selectLine: Qt.rgba(0.541, 0.651, 0.878, 0.40)      // a 1 px inset, never a ring

    function soft(c) { return Qt.rgba(c.r, c.g, c.b, 0.14) }
    function tone(name) {
        return name === "ok" ? ok : name === "warn" ? warn : name === "danger" ? danger
             : name === "accent" ? accent : dim
    }
    function toneSoft(name) {
        return name === "ok" ? okSoft : name === "warn" ? warnSoft : name === "danger" ? dangerSoft
             : name === "accent" ? accentSoft : ground
    }

    // --- the session vocabulary: an icon, never a dot on a person -----------------------------
    function sessionIcon(state) {
        return state === "free" ? "monitor" : state === "native" ? "user" : state === "traversed" ? "lock"
             : state === "assisted" ? "assistance" : state === "su" ? "shield" : "user"
    }
    function sessionColor(state) {
        return state === "free" ? faint : state === "native" ? dim : state === "traversed" ? warn
             : state === "assisted" ? accent : state === "su" ? danger : accent
    }
    function sessionWord(state) {
        return state === "free" ? "Free" : state === "native" ? "At the PC" : state === "traversed" ? "Entered"
             : state === "assisted" ? "Assisted" : state === "su" ? "Super User" : ""
    }
    // what hierarchy.tree gives us, turned into that vocabulary
    function stateOf(session) {
        if (!session) return "free"
        if (session.occupied_via === "native") return "native"
        if (session.occupied_via === "assisted") return "assisted"
        if (session.occupant_role === "super_user") return "su"
        return "traversed"
    }

    // --- geometry -----------------------------------------------------------------------------
    readonly property int radiusSm: 9
    readonly property int radiusMd: 12
    readonly property int radiusLg: 16
    readonly property int radiusXl: 18
    readonly property int pill: 999

    readonly property int s1: 4
    readonly property int s2: 8
    readonly property int s3: 12
    readonly property int s4: 16
    readonly property int s5: 22
    readonly property int s6: 28

    readonly property int railWidth: 64
    readonly property int sideWidth: 280
    readonly property int bodyWidth: 620          // the body never reflows
    readonly property int laneWidth: 372          // the detail card always lands here
    readonly property int rowHeight: 52           // comfortable
    readonly property int topBarHeight: 44
    readonly property int statusHeight: 24

    // --- type ---------------------------------------------------------------------------------
    // the first of these that the system actually has; IBM Plex when it is installed, Segoe otherwise
    function pick(candidates) {
        var have = Qt.fontFamilies()
        for (var i = 0; i < candidates.length; i++)
            if (have.indexOf(candidates[i]) >= 0) return candidates[i]
        return candidates[candidates.length - 1]
    }
    readonly property string sans: pick(["IBM Plex Sans", "Segoe UI Variable Display", "Segoe UI", "Arial"])
    readonly property string monoFamily: pick(["IBM Plex Mono", "Cascadia Mono", "Consolas", "Courier New"])

    readonly property int fSmall: 11
    readonly property int fMeta: 12
    readonly property int fBody: 13
    readonly property int fRow: 14
    readonly property int fSection: 15
    readonly property int fTitle: 24

    // --- motion: one curve, two durations -----------------------------------------------------
    readonly property int durFast: 120
    readonly property int durBase: 220
    readonly property int easing: Easing.OutCubic

    // ==========================================================================================
    // Back-compatible names, so the views not yet rebuilt keep working while the new kit lands.
    readonly property color canvas: frameSolid
    readonly property color surface: side
    readonly property color surfaceHigh: pane
    readonly property color overlay: line
    readonly property color border: line
    readonly property color borderStrong: line2
    readonly property color text: ink
    readonly property color textDim: dim
    readonly property color textFaint: faint
    readonly property color accentDim: select
    readonly property color assist: accent
    readonly property int radius: radiusSm
    readonly property int radiusLarge: radiusMd
    readonly property int space1: s1
    readonly property int space2: s2
    readonly property int space3: s3
    readonly property int space4: s4
    readonly property int space5: s5
    readonly property int controlHeight: 30
    readonly property int fontTiny: 10
    readonly property int fontSmall: fSmall
    readonly property int fontBody: fMeta
    readonly property int fontMedium: fBody
    readonly property int fontLarge: fSection
    readonly property int fontHuge: 20
    readonly property string mono: "IBM Plex Mono, Consolas, monospace"
    readonly property int durationFast: durFast
    readonly property int durationBase: durBase

    function wash(c, a) { return Qt.rgba(c.r, c.g, c.b, a === undefined ? 0.14 : a) }
    function roleTint(role) { return role === "super_user" ? danger : role === "admin" ? accent : dim }
    function roleLabel(role) {
        return role === "super_user" ? "Super User" : role === "admin" ? "Admin" : role === "worker" ? "Worker" : ""
    }
    function sessionTint(session) { return sessionColor(stateOf(session)) }
}
