pragma Singleton

// A department's machines as the screen mark reads them -- one place, so the department page, the Admin's home and
// a client PC agree on what "needs someone" means.
//
// Order of what is said about a machine: a file out of place (danger), then past the update limit (danger), then a
// version behind (warn), then who is on it -- someone else entered (warn), its own user (quiet), nobody (free).
// Stable order: by hostname.

import QtQuick

QtObject {
    function machines(workers, rollout, violations) {
        var behind = {}
        var rows = (rollout && rollout.pcs_behind) ? rollout.pcs_behind : []
        for (var i = 0; i < rows.length; i++) behind[rows[i].pc_id] = rows[i]
        var bad = {}
        for (var v = 0; v < (violations || []).length; v++) {
            var vi = violations[v]
            if (vi.found_on_pc_id) bad[vi.found_on_pc_id] = vi
            if (vi.hostname) bad["host:" + vi.hostname] = vi
        }
        var out = []
        for (var w = 0; w < (workers || []).length; w++) {
            var pc = workers[w]
            if (!pc.pc_id) continue
            var host = pc.hostname || ""
            var s = pc.session
            var b = behind[pc.pc_id]
            var vi2 = bad[pc.pc_id] || bad["host:" + host]
            var status, line
            if (vi2) { status = "danger"; line = "a file out of place" }
            else if (b && b.escalated) { status = "danger"; line = "update past the limit" }
            else if (b) { status = "warn"; line = "a version behind" }
            else if (!s) { status = "free"; line = "free" }
            else if (s.occupied_via === "native") { status = "ok"; line = "at the PC" }
            else { status = "entered"; line = (s.occupant_name || "someone") + " entered" }
            out.push({ pc_id: pc.pc_id, label: host.split("-").pop(), host: host, name: pc.name || host,
                       status: status, line: line,
                       lineTone: status === "danger" ? "danger" : (status === "warn" || status === "entered") ? "warn" : "" })
        }
        out.sort(function (a, b2) { return String(a.host).localeCompare(String(b2.host)) })
        return out
    }
    function needsSomeone(m) { return m.status === "danger" || m.status === "warn" || m.status === "entered" }
}
