pragma Singleton

// THE KINDS OF THING THE RECORD HOLDS, each with its colour and its word: session, action, flow,
// assistance, rollout, deviation, violation. `of(action)` sorts an audit action into one of them.
import QtQuick

QtObject {
    // the concept's seven, then what else the Engine's trail sorts into (audit.events): quiet, never a hue
    // (the Engine's catalogue, engine/console/feed.py, 10 Nov 2026: a mark is a protected file, an issue an issue, a message a message)
    readonly property var keys: ["session", "action", "flow", "violation", "protected", "task", "issue", "message", "detective", "deviation", "rollout", "admin", "system"]
    readonly property var words: ({ session: "In a machine", action: "Action", flow: "Flow", assistance: "Message",
                                    rollout: "Update", deviation: "Rule not met", violation: "Caught",
                                    protected: "Protected file", task: "Task", issue: "Issue", message: "Message", detective: "Detective",
                                    report: "Report", admin: "People and machines", system: "Falcon" })
    function color(k) {
        return k === "session" ? Theme.ser1 : k === "action" ? Theme.ser3 : k === "flow" ? Theme.ser2
             : k === "assistance" ? Theme.ser5 : k === "rollout" ? Theme.ser6 : k === "deviation" ? Theme.high
             : k === "violation" ? Theme.crit : Theme.text4
    }
    // The trail, newest first, as entries: audit.events when the Engine has it (it sorts the kinds itself),
    // else audit.recent sorted here. payload: {limit?, pc_id?, since?}; fn(entries).
    // payload.routine: the machinery too (connections, each file a flow carried), which the Engine leaves out unless asked
    function load(payload, fn) {
        var p = payload || {}
        falcon.call("audit.events", p, function (ok, r) {
            if (ok && r && r.events) { fn(r.events.map(function (e) { return { t: Time.ms(e.at), kind: e.kind, actor: e.actor || "Falcon", what: e.what || "", level: e.level || "done",
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
        if (/^(session|hierarchy\.(traverse|end_session|extend))/.test(a)) return "session"
        if (/^(control|action|event)/.test(a)) return "action"
        if (/^flow/.test(a)) return "flow"
        if (/^assistance/.test(a)) return "assistance"
        if (/^(update|rollout)/.test(a)) return "rollout"
        return "action"
    }
    // an audit entry as the concept reads it: {t (ms), kind, actor, what, host}
    // (only where audit.events is not answered: its level is guessed here, the Engine's own is in feed.py)
    function entry(e) {
        var k = of(e.action), what = e.summary || String(e.action || "").replace(/[._]/g, " ")
        return { t: Time.ms(e.occurred_at), kind: k, actor: e.actor_name || "Falcon", what: what, host: e.target_hostname || "", id: e.id,
                 level: k === "violation" || k === "deviation" || / failed|not run|refused/i.test(what) ? "worth" : "done" }
    }
}
