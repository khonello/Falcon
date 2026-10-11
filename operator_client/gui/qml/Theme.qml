pragma Singleton

// THE TOKENS, as the published concept (Falcon Concepts) defines them: an operations console, dense
// 13px type, tabular figures, one accent, and severity hues spent only where someone has to act.
// Light and dark are both first-class; `mode` is system | light | dark. Nothing else in the console
// names a colour of its own: it names one of these.
import QtQuick

QtObject {
    id: t

    property string mode: "system"
    readonly property bool dark: mode === "dark" || (mode === "system" && Qt.styleHints.colorScheme === Qt.ColorScheme.Dark)

    // --- surfaces and edges ----------------------------------------------------------------------
    readonly property color bg:           dark ? "#0c0f14" : "#f3f4f6"
    readonly property color surface:      dark ? "#12161d" : "#ffffff"
    readonly property color surface2:     dark ? "#161b23" : "#f8f9fb"
    readonly property color surface3:     dark ? "#1d232d" : "#eef0f3"
    readonly property color border:       dark ? "#232a35" : "#e2e5ea"
    readonly property color borderStrong: dark ? "#323b48" : "#cdd2da"
    readonly property color grid:         dark ? "#1c222b" : "#eef0f3"

    // --- ink: four weights, and they carry the information -------------------------------------
    readonly property color text:  dark ? "#e4e7ed" : "#191d25"
    readonly property color text2: dark ? "#aab1be" : "#4a5160"
    readonly property color text3: dark ? "#7c8595" : "#737b8a"
    readonly property color text4: dark ? "#555e6d" : "#a6adb9"

    // --- the one accent: interaction, never status ---------------------------------------------
    readonly property color accent:     dark ? "#5b8cff" : "#2459d6"
    readonly property color accentSoft: dark ? Qt.rgba(91 / 255, 140 / 255, 1, 0.13) : Qt.rgba(36 / 255, 89 / 255, 214 / 255, 0.09)

    // --- severity, and the one green for a completed outcome ------------------------------------
    readonly property color crit: dark ? "#f2604c" : "#c8331f"
    readonly property color high: dark ? "#f08a3e" : "#d4610f"
    readonly property color med:  dark ? "#d9a93a" : "#b58105"
    readonly property color low:  dark ? "#8796b0" : "#5b6b85"
    readonly property color ok:   dark ? "#3fb877" : "#1d8a4f"

    // --- series: kinds of thing, never good or bad -----------------------------------------------
    readonly property color ser1: dark ? "#5b8cff" : "#2459d6"
    readonly property color ser2: dark ? "#2bb8b1" : "#0f8f8a"
    readonly property color ser3: dark ? "#9a85f2" : "#7357d9"
    readonly property color ser4: dark ? "#f08a3e" : "#d4610f"
    readonly property color ser5: dark ? "#d9a93a" : "#b58105"
    readonly property color ser6: dark ? "#7d889b" : "#8a94a6"
    readonly property color own: dark ? "#3a4352" : "#c9ced7"
    readonly property color shadow: dark ? Qt.rgba(0, 0, 0, 0.6) : Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.18)

    // --- the names the kit already uses, on the new tokens --------------------------------------
    readonly property color primary:      accent
    readonly property color primaryHover: Qt.lighter(accent, 1.12)
    readonly property color primaryPress: Qt.darker(accent, 1.15)
    readonly property color primarySoft:  accentSoft
    readonly property color warn:         med
    readonly property color warnSoft:     mix(med, surface, 0.10)
    readonly property color danger:       crit
    readonly property color dangerSoft:   mix(crit, surface, 0.10)
    readonly property color dangerStrong: crit
    readonly property color ink:   text
    readonly property color mid:   text3
    readonly property color quiet: text4
    readonly property color inverse: "#ffffff"
    // the dim behind a dialog, and the dark of a remote screen (the session window)
    readonly property color scrim: Qt.rgba(10 / 255, 14 / 255, 20 / 255, 0.45)
    readonly property color scrimLight: Qt.rgba(10 / 255, 14 / 255, 20 / 255, 0.32)
    readonly property color screen: "#141a24"
    readonly property color screenText: "#dfe6f2"
    readonly property color screenMute: "#8c97aa"
    readonly property color page:       bg
    readonly property color fill:       surface2
    readonly property color fillStrong: surface3
    readonly property color hover:      surface3
    readonly property color split:      grid

    // --- shape, space, motion ---------------------------------------------------------------------
    readonly property int radius:   6
    readonly property int radiusSm: 4
    readonly property int radiusLg: 8
    readonly property int s1: 4
    readonly property int s2: 8
    readonly property int s3: 12
    readonly property int s4: 16
    readonly property int s5: 24
    readonly property int s6: 32
    readonly property int control:   30
    readonly property int controlSm: 24
    readonly property int controlLg: 36
    readonly property int durFast: 120
    readonly property int durBase: 200
    readonly property int listRows: 6            // a list panel shows six rows a page
    readonly property int listHeight: 452        // and stands this tall, with its side panel beside it

    // --- type ----------------------------------------------------------------------------------------
    readonly property int fTiny:  11
    readonly property int fSmall: 12
    readonly property int fBody:  13
    readonly property int fLead:  15
    readonly property int fTitle: 18
    readonly property int fPage:  20
    readonly property int fFigure: 24
    readonly property string sans: "IBM Plex Sans"
    readonly property string mono: "IBM Plex Mono"

    // --- helpers ------------------------------------------------------------------------------------
    // a in b at share p (CSS color-mix(in srgb, a p%, b))
    function mix(a, b, p) {
        return Qt.rgba(a.r * p + b.r * (1 - p), a.g * p + b.g * (1 - p), a.b * p + b.b * (1 - p), 1)
    }
    function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }

    // severity by name: critical | high | medium | low
    function sev(name) {
        return name === "critical" ? crit : name === "high" ? high : name === "medium" ? med : low
    }
    // a "now" cell: good | bad | wait
    function nowColor(k) { return k === "good" ? ok : k === "bad" ? crit : text4 }

    function tone(name) {
        if (name === "danger" || name === "crit") return crit
        if (name === "warn" || name === "med") return med
        if (name === "ok") return ok
        if (name === "accent") return accent
        if (name === "ink") return text
        if (name === "t2") return text2
        if (name === "quiet" || name === "t4") return text4
        return text3
    }
    function toneSoft(name) {
        if (name === "danger") return dangerSoft
        if (name === "warn") return warnSoft
        if (name === "accent") return accentSoft
        return surface2
    }
    // "1 file", "4 files" -- said in one place so no page has to remember the s
    function many(n, word, plural) {
        return fmt(n) + " " + (n === 1 ? word : (plural ? plural : word + "s"))
    }
    // numbers are grouped: 3,532
    function fmt(n) {
        if (typeof n !== "number") return n
        return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
    }
    function initials(name) {
        if (!name) return "?"
        var parts = String(name).split(/[ .]+/).filter(function (p) { return p.length > 0 })
        return (parts.length > 1 ? parts[0][0] + parts[1][0] : String(name).substring(0, 2)).toUpperCase()
    }
    // "A and B", "A, B and 3 more"
    function listNames(xs, n) {
        n = n || 2
        if (!xs || !xs.length) return ""
        return xs.length <= n ? xs.join(" and ") : xs.slice(0, n).join(", ") + " and " + (xs.length - n) + " more"
    }
}
