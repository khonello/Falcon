pragma Singleton
import QtQuick

// A day, as sessions on machines: the arithmetic every timeline needs, in one place.
//
// This lived inside OverviewView, which meant the department page had to reach into a sibling view
// to draw its own day. The numbers belong to neither view: a lane is a PC and a block is a session,
// whatever page is asking.
QtObject {
    id: day

    // hours since midnight, as the timeline's axis counts them
    function nowHours() {
        var d = new Date()
        return d.getHours() + d.getMinutes() / 60
    }

    function hoursOf(iso) {
        if (!iso) return NaN
        var d = new Date(iso)
        var today = new Date()
        var midnight = new Date(today.getFullYear(), today.getMonth(), today.getDate())
        return (d.getTime() - midnight.getTime()) / 3600000
    }

    // what a block MEANS: at your own PC, entered from above, or helped by consent. The occupant's
    // role is what separates a Super User's entry from an Admin's.
    function sessionState(s) {
        if (s.occupied_via === "native") return "native"
        if (s.occupied_via === "assisted_access") return "assisted_access"
        return s.occupant_role === "super_user" ? "super_user" : "traversal"
    }

    function blocksFor(sessions, pcId) {
        var out = []
        var now = nowHours()
        for (var i = 0; i < sessions.length; i++) {
            var s = sessions[i]
            if (s.pc_id !== pcId) continue
            var from = hoursOf(s.entered_at)
            var to = s.ended_at ? hoursOf(s.ended_at) : now
            if (isNaN(from) || to <= from) continue
            out.push({ state: sessionState(s), from: from, to: to,
                       label: (s.occupant_name || "someone") + " · "
                              + (s.occupied_via === "native" ? "at the PC"
                                                             : String(s.occupied_via).replace("_", " ")) })
        }
        return out
    }

    // One lane per PC, so a machine nobody signed into is an empty lane rather than a missing row --
    // absence is information here. Past nine lanes the bars get too thin to read, so the PCs nobody
    // touched collapse into one lane that says how many they are; every PC that was used keeps its own.
    function lanesFor(sessions, pcs) {
        var out = []
        for (var i = 0; i < pcs.length; i++) {
            var w = pcs[i]
            out.push({ name: w.hostname || w.name, blocks: blocksFor(sessions, w.pc_id) })
        }
        if (out.length <= 9) return out
        var used = out.filter(function (l) { return l.blocks.length > 0 })
        var quiet = out.length - used.length
        if (quiet > 0) used.push({ name: quiet + " more", blocks: [], quiet: true })
        return used
    }

    // the axis: wide enough for everything drawn, and never wider than the day
    function windowStart(lanes) {
        var lo = NaN
        for (var i = 0; i < lanes.length; i++)
            for (var j = 0; j < lanes[i].blocks.length; j++)
                lo = isNaN(lo) ? lanes[i].blocks[j].from : Math.min(lo, lanes[i].blocks[j].from)
        if (isNaN(lo)) return Math.max(0, Math.floor(nowHours() - 4))
        return Math.max(0, Math.floor(lo))
    }

    function windowEnd(lanes) {
        var hi = nowHours() + 0.5
        for (var i = 0; i < lanes.length; i++)
            for (var j = 0; j < lanes[i].blocks.length; j++)
                hi = Math.max(hi, lanes[i].blocks[j].to)
        return Math.min(24, Math.ceil(hi))
    }
    // --- a held session's clock: the lid and the container read the same arithmetic ------------
    // `nowMs` is passed in (the shell's one ticking clock) so a binding re-evaluates every second.
    function secondsLeft(deadlineIso, nowMs) {
        if (!deadlineIso) return 0
        return Math.max(0, Math.floor((new Date(deadlineIso).getTime() - nowMs) / 1000))
    }
    function leftText(deadlineIso, nowMs) {
        var s = secondsLeft(deadlineIso, nowMs)
        var m = Math.floor(s / 60), r = s % 60
        return m + ":" + (r < 10 ? "0" : "") + r
    }
    // how much of the session is left, 0..1 -- what the ring draws
    function leftFraction(enteredIso, deadlineIso, nowMs) {
        if (!enteredIso || !deadlineIso) return 0
        var a = new Date(enteredIso).getTime(), b = new Date(deadlineIso).getTime()
        return b <= a ? 0 : Math.max(0, Math.min(1, (b - nowMs) / (b - a)))
    }
}
