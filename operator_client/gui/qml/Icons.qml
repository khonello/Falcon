pragma Singleton

// The icon set, as SVG path data on a 24x24 grid. Stroke only: Icon.qml draws them with Shapes, so
// there are no image files to ship and every glyph takes the colour it is given.
//
// Circles are written as two arcs because path data has no circle. Each entry is a list of paths.

import QtQuick

QtObject {
    readonly property var paths: ({
        // navigation
        "hierarchy":  ["M3 21h18", "M5 21V8l7-4 7 4v13", "M9 21v-5h6v5", "M9 11h2", "M13 11h2"],
        "dept":       ["M3 21h18", "M5 21V8l7-4 7 4v13", "M9 21v-5h6v5", "M9 11h2", "M13 11h2"],
        "tasks":      ["M4.5 4.5h15v15h-15z", "M8.5 12.2l2.5 2.5 4.5-5"],
        "flows":      ["M6 5v14", "M6 12h6", "M12 12V6h6", "M12 12v6h6"],
        "automation": ["M13 2L4 14h7l-1 8 9-12h-7z"],
        "play":       ["M7 4l12 8-12 8z"],
        "assistance": ["M4 5h16v11H9l-5 4V5z", "M8 9h8", "M8 12h5"],
        "reports":    ["M6 3h8l4 4v14H6z", "M14 3v4h4", "M9 12h6", "M9 16h6"],
        "eye":        ["M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z", "M15 12a3 3 0 1 0 -6 0a3 3 0 1 0 6 0"],
        "shield":     ["M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"],

        // chrome
        "search":  ["M16.5 11.5a5 5 0 1 0 -10 0a5 5 0 1 0 10 0", "M15.4 15.4l5 5"],
        "back":    ["M15 5l-7 7 7 7"],
        "fwd":     ["M9 5l7 7-7 7"],
        "chev":    ["M9 6l6 6-6 6"],
        "chevd":   ["M6 9l6 6 6-6"],
        "min":     ["M5 12h14"],
        "close":   ["M6 6l12 12", "M18 6L6 18"],
        "x":       ["M6 6l12 12", "M18 6L6 18"],
        "plus":    ["M12 5v14", "M5 12h14"],
        "check":   ["M5 12l5 5 9-10"],

        // the hierarchy and its states
        "user":    ["M16 8a4 4 0 1 0 -8 0a4 4 0 1 0 8 0", "M4 21a8 8 0 0 1 16 0"],
        "monitor": ["M3 4h18v12H3z", "M8 20h8", "M12 16v4"],
        "lock":    ["M5 11h14v10H5z", "M8 11V8a4 4 0 0 1 8 0v3"],
        "clock":   ["M20.5 12a8.5 8.5 0 1 0 -17 0a8.5 8.5 0 1 0 17 0", "M12 7.5V12l3 2"],
        "ping":    ["M15 12a3 3 0 1 0 -6 0a3 3 0 1 0 6 0", "M5.6 5.6a9 9 0 0 0 0 12.8", "M18.4 5.6a9 9 0 0 1 0 12.8"],
        "warn":    ["M12 3l10 18H2z", "M12 10v4", "M12 17.4v.2"],
        "bell":    ["M6 16V11a6 6 0 0 1 12 0v5l2 2H4z", "M10 21h4"],

        // files and work
        "file":    ["M6 3h8l4 4v14H6z", "M14 3v4h4"],
        "folder":  ["M3 6h6l2 2h10v11H3z"],
        "camera":  ["M4 8h4l2-3h4l2 3h4v11H4z", "M15.5 13a3.5 3.5 0 1 0 -7 0a3.5 3.5 0 1 0 7 0"],
        "pulse":   ["M3 12h3.5l2-7 3.5 14 2.5-7H21"],
        "keyboard":["M2 6h20v12H2z", "M7 14h10", "M6 10h.2", "M10 10h.2", "M14 10h.2", "M18 10h.2"],
        "globe":   ["M21 12a9 9 0 1 0 -18 0a9 9 0 1 0 18 0", "M3 12h18", "M12 3c2.6 3 2.6 15 0 18", "M12 3c-2.6 3-2.6 15 0 18"],
        "cpu":     ["M4 4h16v16H4z", "M9 9h6v6H9z", "M9 2v2", "M15 2v2", "M9 20v2", "M15 20v2"],
        "window":  ["M3 4h18v16H3z", "M3 9h18"],
        "key":     ["M12 12a4 4 0 1 0 -8 0a4 4 0 1 0 8 0", "M12 12h9", "M18 12v4"],
        "branch":  ["M6 5v14", "M6 12c0-3 3-3 6-3h4"],
        "stop":    ["M6 6h12v12H6z"],
        "pause":   ["M8 5v14", "M16 5v14"],
        "power":   ["M12 3v9", "M6.5 7a8 8 0 1 0 11 0"],
        "terminal":["M3 4h18v16H3z", "M7 9l3 3-3 3", "M13 15h4"]
    })

    function get(name) {
        var p = paths[name]
        return p === undefined ? [] : p
    }
}
