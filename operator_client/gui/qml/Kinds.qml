pragma Singleton

// THE KINDS OF THING THE RECORD HOLDS, each with its colour and its word: session, action, flow,
// assistance, rollout, deviation, violation. `of(action)` sorts an audit action into one of them.
import QtQuick

QtObject {
    // the concept's seven, then what else the Engine's trail sorts into (audit.events): quiet, never a hue
    readonly property var keys: ["session", "action", "flow", "assistance", "rollout", "deviation", "violation", "task", "report", "admin", "system"]
    readonly property var words: ({ session: "Session", action: "Action", flow: "Flow", assistance: "Assistance",
                                    rollout: "Rollout", deviation: "Deviation", violation: "Violation",
                                    task: "Task", report: "Report", admin: "Administration", system: "Sign-in" })
    function color(k) {
        return k === "session" ? Theme.ser1 : k === "action" ? Theme.ser3 : k === "flow" ? Theme.ser2
             : k === "assistance" ? Theme.ser5 : k === "rollout" ? Theme.ser6 : k === "deviation" ? Theme.high
             : k === "violation" ? Theme.crit : Theme.text4
    }
    // The trail, newest first, as entries: audit.events when the Engine has it (it sorts the kinds itself),
    // else audit.recent sorted here. payload: {limit?, pc_id?, since?}; fn(entries).
    function load(payload, fn) {
        var p = payload || {}
        falcon.call("audit.events", p, function (ok, r) {
            if (ok && r && r.events) { fn(r.events.map(function (e) { return { t: Time.ms(e.at), kind: e.kind, actor: e.actor || "System", what: e.what || "",
                                                                                host: e.host || "", id: e.id, pc_id: e.pc_id, rid: String(e.id), raw: e } })); return }
            falcon.call("audit.recent", { limit: p.limit || 500 }, function (ok2, r2) {
                var es = ok2 ? (r2.entries || []).map(function (e) { return Object.assign(entry(e), { rid: String(e.id), raw: e }) }) : []
                if (p.pc_id !== undefined && Fleet.byPc[p.pc_id]) es = es.filter(function (e) { return e.host === Fleet.byPc[p.pc_id].host })
                fn(es)
            })
        })
    }
    function of(action) {
        var a = String(action || "")
        if (/^resource\.violation|violation/.test(a)) return "violation"
        if (/^deviation|^auth\.failed|mismatch/.test(a)) return "deviation"
        if (/^(session|hierarchy\.(traverse|end_session|extend)|assisted_access)/.test(a)) return "session"
        if (/^(control|action|event)/.test(a)) return "action"
        if (/^flow/.test(a)) return "flow"
        if (/^assistance/.test(a)) return "assistance"
        if (/^(update|rollout)/.test(a)) return "rollout"
        return "action"
    }
    // an audit entry as the concept reads it: {t (ms), kind, actor, what, host}
    function entry(e) {
        return { t: Time.ms(e.occurred_at), kind: of(e.action), actor: e.actor_name || "System",
                 what: e.summary || String(e.action || "").replace(/[._]/g, " "), host: e.target_hostname || "", id: e.id }
    }
}
