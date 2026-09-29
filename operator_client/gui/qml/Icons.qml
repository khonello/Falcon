pragma Singleton

// One stroke set, drawn as SVG path data on a 24x24 grid. No image assets: `Icon` strokes these
// with QtQuick.Shapes, so an icon takes any colour and any size without a second file.
import QtQuick

QtObject {
    readonly property var glyph: ({
        // the rail
        "pulse":      ["M3 12h4l3 8 4-16 3 8h4"],
        "dept":       ["M3 21h18", "M5 21V7l7-4 7 4v14", "M9 21v-6h6v6"],
        "people":     ["M16 21v-2a4 4 0 0 0-8 0v2", "M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8", "M22 21v-2a4 4 0 0 0-3-3.87"],
        "monitor":    ["M3 4h18v12H3z", "M8 20h8", "M12 16v4"],
        "tasks":      ["M4 5h16v16H4z", "M8 11l3 3 5-5"],
        "flows":      ["M6 3v12", "M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6", "M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6", "M18 9v3a6 6 0 0 1-6 6H9"],
        "bolt":       ["M13 2L4 14h7l-1 8 9-12h-7l1-8z"],
        "play":       ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18", "M10 9l5 3-5 3z"],
        "message":    ["M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z"],
        "folder":     ["M3 7h6l2 2h10v10H3z"],
        "file":       ["M14 3H6v18h12V7z", "M14 3v4h4", "M9 13h6", "M9 17h6"],
        "cloud":      ["M12 16V8", "M9 11l3-3 3 3", "M6 20h12a4 4 0 0 0 .5-8 6 6 0 0 0-11.7-1.5A3.5 3.5 0 0 0 6 20"],
        "history":    ["M3 12a9 9 0 1 0 3-6.7", "M3 4v5h5", "M12 8v5l3 2"],
        "gear":       ["M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6", "M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7.5 19.4l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 3 14.6a2 2 0 1 1 0-4 1.6 1.6 0 0 0 1.1-2.7l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 9.4 3V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0 1.1 2.7H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1.3z"],
        // furniture
        "chevd":      ["M6 9l6 6 6-6"],
        "chevu":      ["M18 15l-6-6-6 6"],
        "chevl":      ["M15 18l-6-6 6-6"],
        "chevr":      ["M9 18l6-6-6-6"],
        "caretu":     ["M12 8l4 5H8z"],
        "caretd":     ["M12 16l-4-5h8z"],
        "search":     ["M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16", "M21 21l-4.3-4.3"],
        "plus":       ["M12 5v14", "M5 12h14"],
        "close":      ["M6 6l12 12", "M18 6L6 18"],
        "min":        ["M5 12h14"],
        "max":        ["M5 5h14v14H5z"],
        "restore":    ["M8 8h11v11H8z", "M16 8V5H5v11h3"],
        "more":       ["M12 6h.01", "M12 12h.01", "M12 18h.01"],
        "filter":     ["M4 5h16l-6 7v6l-4 2v-8z"],
        "download":   ["M12 3v12", "M8 11l4 4 4-4", "M4 21h16"],
        "calendar":   ["M4 5h16v16H4z", "M4 10h16", "M9 3v4", "M15 3v4"],
        "check":      ["M5 13l4 4L19 7"],
        "warn":       ["M12 3l9 16H3z", "M12 10v4", "M12 17h.01"],
        "info":       ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18", "M12 11v5", "M12 8h.01"],
        "user":       ["M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2", "M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8"],
        "lock":       ["M5 11h14v10H5z", "M8 11V7a4 4 0 0 1 8 0v4"],
        "stop":       ["M6 6h12v12H6z"]
    })
    function has(name) { return glyph[name] !== undefined }
}
