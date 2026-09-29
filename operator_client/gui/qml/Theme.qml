pragma Singleton

// THE TOKENS (docs/UI.md). Ant Design 6's values, with Falcon's two rationed status hues.
// Nothing in this console names a colour of its own; it names one of these.
import QtQuick

QtObject {
    // --- the one accent: interaction, never status -------------------------------------------
    readonly property color primary:      "#1677ff"
    readonly property color primaryHover: "#4096ff"
    readonly property color primaryPress: "#0958d9"
    readonly property color primarySoft:  "#e6f4ff"

    // --- the two hues that mean somebody must act ---------------------------------------------
    readonly property color warn:      "#ad6800"     // will need someone
    readonly property color warnSoft:  "#fffbe6"
    readonly property color danger:    "#cf1322"     // needs someone now
    readonly property color dangerSoft: "#fff1f0"
    readonly property color dangerStrong: "#ff4d4f"  // a destructive button's fill

    // --- ink: three weights, and they carry the information ----------------------------------
    readonly property color ink:   Qt.rgba(0, 0, 0, 0.88)
    readonly property color mid:   Qt.rgba(0, 0, 0, 0.45)
    readonly property color quiet: Qt.rgba(0, 0, 0, 0.25)
    readonly property color onDark: "#ffffff"

    // --- surfaces and edges --------------------------------------------------------------------
    readonly property color page:     "#f5f5f5"      // behind the content
    readonly property color surface:  "#ffffff"      // the content itself
    readonly property color fill:     "#fafafa"      // a filled card, a table header
    readonly property color fillStrong: "#f0f0f0"    // a source node, a pressed row
    readonly property color hover:    "#f5f5f5"
    readonly property color border:   "#d9d9d9"      // a control's edge
    readonly property color split:    "#f0f0f0"      // a divider, a row rule

    // --- shape, space, motion -------------------------------------------------------------------
    readonly property int radius:   6
    readonly property int radiusSm: 4
    readonly property int radiusLg: 8
    readonly property int s1: 4
    readonly property int s2: 8
    readonly property int s3: 12
    readonly property int s4: 16
    readonly property int s5: 24
    readonly property int s6: 32
    readonly property int control:    32             // every input, button, select
    readonly property int controlSm:  24
    readonly property int controlLg:  40
    readonly property int durFast: 110
    readonly property int durBase: 200

    // --- type ------------------------------------------------------------------------------------
    readonly property int fSmall: 12
    readonly property int fBody:  14
    readonly property int fLead:  16
    readonly property int fTitle: 20
    readonly property int fPage:  24
    readonly property real lineHeight: 1.5714
    // ONE family each: QML's font.family is not a CSS stack, and a list renders as tofu. The client
    // is Windows (implementation-spec 4.2); the fallbacks are for a developer machine elsewhere.
    readonly property string sans: Qt.platform.os === "windows" ? "Segoe UI"
                                   : Qt.platform.os === "osx" ? "Helvetica Neue" : "DejaVu Sans"
    readonly property string mono: Qt.platform.os === "windows" ? "Consolas"
                                   : Qt.platform.os === "osx" ? "Menlo" : "DejaVu Sans Mono"

    // --- the status ladder, in one place ----------------------------------------------------------
    // tone("warn") etc; anything not listed is quiet, which is the point.
    function tone(name) {
        if (name === "danger") return danger
        if (name === "warn") return warn
        if (name === "accent") return primary
        if (name === "ink") return ink
        if (name === "quiet") return quiet
        return mid
    }
    function toneSoft(name) {
        if (name === "danger") return dangerSoft
        if (name === "warn") return warnSoft
        if (name === "accent") return primarySoft
        return fill
    }
    function initials(name) {
        if (!name) return "?"
        var parts = String(name).replace(".", " ").split(" ").filter(function (p) { return p.length > 0 })
        return (parts.length > 1 ? parts[0][0] + parts[1][0] : String(name).substring(0, 2)).toUpperCase()
    }
}
