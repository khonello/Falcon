pragma Singleton

// WHERE THE CONSOLE IS. The page, the item open on it and the time range. The shell draws from this
// and every page goes somewhere through `go`, so there is one way to move.
import QtQuick

QtObject {
    id: nav

    property string page: "overview"
    property var sub: null
    property string range: "24h"              // 1h | 6h | 24h | 7d, the top bar's, for the pages that read time
    property string me: ""                      // the person at this console, by name
    property string myName: ""                  // the signed-in Admin's own name, from the tree
    property var counts: ({})                  // page -> {n, hot, pulse}, drawn on the menu
    property int ver: 0                        // bumped when something every page shows changed

    // what a page was opened with, read once by the page it was meant for
    property var preset: null
    function take(page) {
        if (!preset || preset.page !== page) return null
        var p = preset; preset = null; return p
    }

    signal went(string page, var sub)
    // A button that opens another page asks first, then arrives: the page it opens picks the thing and pulses it (the user,
    // 1 Nov 2026). The person can stop the asking; the menu, the crumb and search never ask.
    property bool askFirst: true
    property var arrive: null                  // {page, target}: what the page being opened should pick
    signal asking(var req)
    function goAsk(p, s, what, target) {
        var req = { page: p, sub: s === undefined ? null : s, what: what || "", target: target === undefined ? null : target }
        if (askFirst) asking(req); else arriveAt(req)
    }
    function arriveAt(req) {
        arrive = req.target === null ? null : { page: req.page, target: req.target }
        go(req.page, req.sub)
    }
    function takeArrive(p) {
        if (!arrive || arrive.page !== p) return null
        var a = arrive.target; arrive = null; return a
    }
    signal palette()
    // Pages that were pruned (docs/design/pruning.md): whoever still points at one lands on the page that took over its job.
    readonly property var gone: ({ access: 1, accountability: 1, rules: 1, rollout: 1, reports: 1, sessions: 1 })
    function remap(p, s) {
        if (p === "messages" && s === "announcements") return ["announcements", null]      // the calendar still links here (ENGINE-GAPS 25)
        if (!(p in gone)) return [p, s]
        return [p === "sessions" || p === "rollout" ? "machines" : p === "reports" ? "issues" : "overview", null]
    }
    // A tab of a page is a page of its own that the menu does not list: it lights up its parent's entry.
    function parentOf(p) { return "" }
    function go(p, s) {
        var r = remap(p, s === undefined ? null : s)
        page = r[0]
        sub = r[1] === undefined ? null : r[1]
        went(page, sub)
    }
    function count(p, n, hot, pulse) {
        var c = Object.assign({}, counts)
        c[p] = { n: n || 0, hot: !!hot, pulse: !!pulse }
        counts = c
    }

    // --- the menus ----------------------------------------------------------------------------------
    // Three groups (19 Oct 2026): Home, Core (the four features), Manage.
    readonly property var menu: [
        ["Home", [["overview", "Overview", "dashboard"], ["messages", "Messages", "message"], ["announcements", "Announcements", "notification"], ["calendar", "Calendar", "calendar"]]],
        ["Core", [["tasks", "Tasks", "checksquare"], ["flows", "Flows", "branches"], ["restricted", "Restricted", "fileprotect"], ["detective", "Detective", "filesearch"]]],
        ["Manage", [["machines", "Machines", "desktop"], ["departments", "Departments", "apartment"], ["actions", "Actions", "playcircle"], ["automation", "Automation", "thunderbolt"],
                    ["issues", "Issues", "alert"], ["audit", "Audit log", "history"]]]
    ]

    function allowed(p) {
        if (parentOf(p) !== "") return allowed(parentOf(p))
        for (var g = 0; g < menu.length; g++)
            for (var i = 0; i < menu[g][1].length; i++) if (menu[g][1][i][0] === p) return true
        return false
    }

    // --- titles: what each page is, in a line --------------------------------------------------------
    readonly property var titles: ({
        announcements: ["Announcements", "What is said to many people at once"],
        calendar: ["Calendar", "What is coming · task deadlines, your to-dos and scheduled automation"],
        messages: ["Messages", "Conversations with the people you look after, one at a time or as a group"],
        detective: ["Detective", "What people seem to be trying to do · several small things read together, with the evidence"],
        accountability: ["Accountability", "Where a rule was broken, who it was, and what came of it"],
        access: ["Access", "Who is inside which machine, and who was let in"],
        departments: ["Departments", "Labels that group machines and the people at them"],
        rules: ["Rules", "The standard the organisation is measured against"],
        actions: ["Actions", "Everything a rule can do, and what you can run by hand"],
        overview: ["Overview", "All departments · live"],
        machines: ["Machines", "Every registered client PC"],
        sessions: ["Sessions", "Who is on which machine, and who entered whose"],
        issues: ["Issues", "Violations, deviations and anything waiting on someone"],
        tasks: ["Tasks", "Assigned work and the evidence for it"],
        restricted: ["Restricted", "Files marked to stay where they are · a copy anywhere else is caught"],
        flows: ["Flows", "One-way file pipelines between machines"],
        automation: ["Automation", "Rules, conditions and every run"],
        rollout: ["Rollout", "Versions and the gate to the next one"],
        audit: ["Audit log", "Everything that happened, and who did it"],
        reports: ["Reports", "What the system wrote down, and where it went"]
    })
    property string deptName: ""                // the only department there is, when there is one, for the subtitle
    property int departments: 0                // how many the organisation has, for the sider
    function title(p) { return titles[p] ? titles[p][0] : p }
    function subtitle(p) {
        if (p === "overview") return deptName ? deptName + " · as " + me + " sees it" : titles.overview[1]
        return titles[p] ? titles[p][1] : ""
    }
}
