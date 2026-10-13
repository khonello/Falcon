pragma Singleton

// TIME, AS THE CONCEPT SAYS IT. "13:20" today, "Mon 09:30" this week, "12 Sep" before that; lengths
// as "42m" or "2h 10m"; ages as "3d". Everything takes an ISO string, a Date or epoch milliseconds.
import QtQuick

QtObject {
    id: tm
    // the console's clock, ticking once a second; bindings that read `now` stay current
    property real now: Date.now() + skew
    property Timer ticker: Timer { interval: 1000; running: true; repeat: true; onTriggered: tm.now = Date.now() + tm.skew }
    // only the preview sets this (scripts/preview.py), so its sample day reads as the concept's 13:20
    property real skew: 0
    onSkewChanged: now = Date.now() + skew

    readonly property var days: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    readonly property var months: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    function d(x) {
        if (x === null || x === undefined || x === "") return null
        if (x instanceof Date) return x
        var v = new Date(x)
        return isNaN(v.getTime()) ? null : v
    }
    function ms(x) { var v = d(x); return v ? v.getTime() : null }
    function pad(n) { return (n < 10 ? "0" : "") + n }
    function hhmm(x) { var v = d(x); return v ? pad(v.getHours()) + ":" + pad(v.getMinutes()) : "—" }
    function startOfDay(t) { var v = new Date(t); v.setHours(0, 0, 0, 0); return v.getTime() }
    function sameDay(a, b) { return startOfDay(a) === startOfDay(b) }
    // hours since today's midnight; negative for earlier days (the concept's own time axis)
    function hoursOf(x) { var t = ms(x); return t === null ? null : (t - startOfDay(now)) / 3600000 }
    function nowHours() { return (now - startOfDay(now)) / 3600000 }

    // "13:20" today, "Mon 09:30" within a week, "12 Sep" before that
    function at(x) {
        var v = d(x); if (!v) return "—"
        if (sameDay(v.getTime(), now)) return hhmm(v)
        if (now - v.getTime() < 6.5 * 86400000 && v.getTime() < now) return days[v.getDay()] + " " + hhmm(v)
        if (v.getTime() > now && v.getTime() - now < 6.5 * 86400000) return days[v.getDay()] + " " + hhmm(v)
        return v.getDate() + " " + months[v.getMonth()]
    }
    // "Today 13:20" / "Mon 09:30"
    function atDay(x) { var v = d(x); return v ? (sameDay(v.getTime(), now) ? "Today " + hhmm(v) : at(v)) : "—" }
    function dayName(x) { var v = d(x); return v ? days[v.getDay()] : "" }
    function day(x) { var v = d(x); return v ? v.getDate() + " " + months[v.getMonth()] : "—" }       // "5 Sep"
    function date(x) { var v = d(x); return v ? days[v.getDay()] + " " + v.getDate() + " " + months[v.getMonth()] + ", " + hhmm(v) : "—" }

    // a length of time in hours -> "42m", "2h 10m"
    function dur(h) {
        var m = Math.max(0, Math.round(h * 60))
        return m >= 60 ? Math.floor(m / 60) + "h " + pad(m % 60) + "m" : m + "m"
    }
    // minutes -> "42m", "2h 10m"
    function mins(m) { return dur(m / 60) }
    // a long length in hours -> "3d 4h", else as dur
    function span(h) { h = Math.abs(h); return h > 24 ? Math.floor(h / 24) + "d " + Math.round(h % 24) + "h" : dur(h) }
    // how long ago, compactly: "42m", "3h 05m", "4d"
    function age(x) {
        var t = ms(x); if (t === null) return "—"
        var h = (now - t) / 3600000
        return h > 24 ? Math.floor(h / 24) + "d" : dur(h)
    }
    function ago(x) { var t = ms(x); return t === null ? "never" : ((now - t) < 90000 ? "now" : age(x) + " ago") }
    // a deadline -> "2d 4h left" / "5h late"
    function left(x) {
        var t = ms(x); if (t === null) return "No deadline"
        var h = (t - now) / 3600000
        return h >= 0 ? span(h) + " left" : span(-h) + " late"
    }
    function past(x) { var t = ms(x); return t !== null && t < now }
    // the range the top bar picks, as hours back from now
    function rangeHours(r) { return r === "1h" ? 1 : r === "6h" ? 6 : r === "7d" ? 168 : 24 }
}
