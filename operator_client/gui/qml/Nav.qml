pragma Singleton

// WHERE THE CONSOLE IS. The page, the item open on it, the time range, and which level this is: the
// Super User's own, or an Admin's console (an Admin's own, or one a Super User entered). The shell
// draws from this and every page goes somewhere through `go`, so there is one way to move.
import QtQuick

QtObject {
    id: nav

    property string page: "overview"
    property var sub: null
    property string range: "24h"              // 1h | 6h | 24h | 7d, the top bar's, for the pages that read time
    property bool boss: false                  // a Super User at the Super User's own level
    property bool inside: false                // a Super User inside an Admin's console
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
    signal palette()
    // enter an Admin's console (the Super User), landing on [page, sub]; the shell asks block or end first
    signal enterRequested(var admin, var to)
    function enter(admin, to) { enterRequested(admin, to || null) }

    // The Super User's own level never opens an Admin's page (docs/design/su-navigation.md): a machine
    // opens in Registry, an issue on its department's page; working on either goes through traversal.
    function route(p, s) {
        if (!boss) return [p, s]
        if (p === "dept") return ["departments", s]
        if (p === "machines") return ["registry", s]
        if (p === "issues") return ["departments", null]
        if (p === "sessions") return ["access", s]
        return [p, s]
    }
    function go(p, s) {
        var r = route(p, s === undefined ? null : s)
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
    readonly property var adminMenu: [
        ["Core", [["overview", "Overview", "dashboard"], ["messages", "Messages", "message"], ["tasks", "Tasks", "checksquare"],
                  ["restricted", "Restricted", "fileprotect"], ["flows", "Flows", "branches"]]],
        ["Monitor", [["machines", "Machines", "desktop"], ["sessions", "Sessions", "login"], ["issues", "Issues", "alert"]]],
        ["Automate", [["automation", "Automation", "thunderbolt"], ["actions", "Actions", "playcircle"]]],
        ["Govern", [["rollout", "Rollout", "cloudupload"], ["audit", "Audit log", "history"], ["reports", "Reports", "filetext"]]]
    ]
    readonly property var suMenu: [
        ["Core", [["overview", "Overview", "dashboard"], ["messages", "Messages", "message"], ["tasks", "Tasks", "checksquare"],
                  ["restricted", "Restricted", "fileprotect"], ["flows", "Flows", "branches"]]],
        ["Organisation", [["departments", "Departments", "apartment"], ["accountability", "Accountability", "eye"],
                          ["access", "Access", "login"], ["registry", "Registry", "desktop"], ["reports", "Reports", "filetext"]]],
        ["Govern", [["rules", "Rules", "safety"], ["rollout", "Rollout", "cloudupload"], ["audit", "Audit log", "history"]]]
    ]
    readonly property var menu: boss ? suMenu : adminMenu

    function allowed(p) {
        for (var g = 0; g < menu.length; g++)
            for (var i = 0; i < menu[g][1].length; i++) if (menu[g][1][i][0] === p) return true
        return false
    }

    // --- titles: what each page is, in a line --------------------------------------------------------
    readonly property var titles: ({
        messages: ["Messages", "Pings and the conversations they open, one message each way at a time"],
        departments: ["Departments", "The organisation, who runs each part of it, and how each is doing"],
        accountability: ["Accountability", "Where a rule was broken, who it was, and what came of it"],
        access: ["Access", "Who is inside which machine, and who was let in"],
        registry: ["Registry", "Machines and accounts · register, re-key, provision"],
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
    property string deptName: ""                // the department of the Admin's console, for its subtitle
    property int departments: 0                // how many the organisation has, for the sider
    function title(p) { return titles[p] ? titles[p][0] : p }
    function subtitle(p) {
        if (p === "overview") return boss ? "What needs you, and how the organisation is doing"
                                          : (deptName ? deptName + " · as " + me + " sees it" : titles.overview[1])
        if (boss && p === "tasks") return "Work you give departments, and how far each has got"
        if (boss && p === "flows") return "Every flow in the organisation · you can send between any two machines"
        return titles[p] ? titles[p][1] : ""
    }
}
