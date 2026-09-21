import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Reports (written once, routed additively), routing configuration, alerts, updates rollout,
// the audit trail + deviations, and account/department administration.
Item {
    id: view
    property var reports: []
    property var routing: ({categories: [], routing: []})
    property var addressed: []
    property var alerts: []
    property var health: null
    property var audit: []
    property var deviations: []
    property var departments: []

    function refresh() {
        falcon.call("reports.list", {}, function(ok, r) { if (ok) view.reports = r.reports })
        falcon.call("alerts.list", {}, function(ok, r) { if (ok) view.alerts = r.alerts })
        falcon.call("updates.rollout_health", {}, function(ok, r) { if (ok) view.health = r })
        falcon.call("hierarchy.departments", {}, function(ok, r) { if (ok) view.departments = r.departments })
        if (falcon.role === "super_user") {
            falcon.call("reports.routing_get", {}, function(ok, r) { if (ok) view.routing = r })
            falcon.call("reports.addressed_view", {}, function(ok, r) { if (ok) view.addressed = r.addressed })
            falcon.call("audit.deviations", {}, function(ok, r) { if (ok) view.deviations = r.deviations })
        }
        refreshAudit()
    }
    function refreshAudit() {
        falcon.call("audit.recent", {limit: 100, actor_account_id: auditActor.text ? parseInt(auditActor.text) : null, prefix: auditPrefix.text || null},
                    function(ok, r) { if (ok) view.audit = r.entries; else root.notify(r.message, true) })
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Connections {
        target: falcon
        function onConnected() { view.refresh() }
        function onPushReceived(type, p) { if (type.indexOf("report.") === 0 || type.indexOf("alert.") === 0 || type.indexOf("update.") === 0) view.refresh() }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8
        RowLayout {
            Label { text: "Reports & Administration"; font.pixelSize: Theme.fontLarge; color: Theme.text }
            SegmentedControl { id: tabs; segments: [{text: "Reports"}, {text: "Alerts"}, {text: "Updates"}, {text: "Audit"}, {text: "Accounts"}] }
            Btn { text: "Refresh"; onClicked: view.refresh() }
        }

        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            // --- reports + routing
            RowLayout {
                spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    DataTable { id: reportTable; Layout.fillWidth: true; Layout.fillHeight: true; rows: view.reports
                                columns: ["id", "category", "source_table", "source_id", "generated_at", "addressed_at"]
                                widths: ({id: 50, category: 160, source_table: 150, source_id: 70, generated_at: 130, addressed_at: 130}); emptyText: "(no reports)" }
                    RowLayout {
                        Btn { text: "Mark addressed"; enabled: reportTable.selectedIndex >= 0
                                 onClicked: falcon.call("reports.mark", {report_id: view.reports[reportTable.selectedIndex].id}, function(ok, r) { root.notify(ok ? "addressed (view row " + r.view_id + ")" : r.message, !ok); view.refresh() }) }
                    }
                    Eyebrow { label: "addressed views (Super User only)"; visible: falcon.role === "super_user" }
                    DataTable { Layout.fillWidth: true; Layout.preferredHeight: 120; visible: falcon.role === "super_user"; rows: view.addressed
                                columns: ["report_id", "category", "addressed_by_account_id", "addressed_by_department_id", "addressed_at"]
                                widths: ({report_id: 70, category: 160, addressed_by_account_id: 90, addressed_by_department_id: 90, addressed_at: 130}); emptyText: "(none)" }
                }
                Rectangle {
                    Layout.preferredWidth: 380; Layout.fillHeight: true; color: Theme.surface; radius: Theme.radius; border.width: 1; border.color: Theme.border; visible: falcon.role === "super_user"
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 6
                        Label { text: "Report routing (additive to Super User)"; color: Theme.text; font.bold: true }
                        DataTable { Layout.fillWidth: true; Layout.fillHeight: true; rows: view.routing.routing
                                    columns: ["category", "department_name", "routed_department_id", "configured_at"]
                                    widths: ({category: 130, department_name: 100, routed_department_id: 50, configured_at: 110}); emptyText: "(nothing routed — Super User only)" }
                        Picker { id: routeCat; Layout.fillWidth: true; model: view.routing.categories }
                        RowLayout {
                            Field { id: routeDepts; Layout.fillWidth: true; placeholderText: "department ids 1,2 (blank = none)" }
                            Btn { text: "Set"; enabled: routeCat.currentText.length > 0
                                     onClicked: falcon.call("reports.routing_set", {category: routeCat.currentText, department_ids: view.ints(routeDepts.text)},
                                                            function(ok, r) { root.notify(ok ? r.category + " -> " + (r.department_ids.length ? r.department_ids.join(", ") : "Super User only") : r.message, !ok); view.refresh() }) }
                        }
                    }
                }
            }

            // --- alerts
            RowLayout {
                spacing: 10
                DataTable { Layout.fillWidth: true; Layout.fillHeight: true; rows: view.alerts
                            columns: ["id", "alert_type", "audience", "body", "action_link", "deliver_at"]
                            widths: ({id: 50, alert_type: 100, audience: 110, body: 360, action_link: 160, deliver_at: 130}); emptyText: "(no alerts)" }
                Rectangle {
                    Layout.preferredWidth: 380; Layout.fillHeight: true; color: Theme.surface; radius: Theme.radius; border.width: 1; border.color: Theme.border
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 6
                        Label { text: "New alert"; color: Theme.text; font.bold: true }
                        RowLayout {
                            Picker { id: aType; model: ["emergency", "warning", "announcement", "routine"]; Layout.fillWidth: true }
                            Picker { id: aAud; model: ["admin_only", "department", "all_users", "specific_users"]; Layout.fillWidth: true }
                        }
                        TextArea { id: aBody; Layout.fillWidth: true; Layout.preferredHeight: 80; placeholderText: "body"; wrapMode: TextEdit.Wrap }
                        Field { id: aDept; Layout.fillWidth: true; placeholderText: "department id (for 'department')"; visible: aAud.currentText === "department" }
                        Field { id: aTo; Layout.fillWidth: true; placeholderText: "account ids 1,2 (for 'specific_users')"; visible: aAud.currentText === "specific_users" }
                        Field { id: aAt; Layout.fillWidth: true; placeholderText: "deliver at (ISO or phrase, blank = now)" }
                        Field { id: aLink; Layout.fillWidth: true; placeholderText: "action link (optional)" }
                        Btn { text: "Send"; enabled: aBody.text.length > 0; Layout.alignment: Qt.AlignRight
                                 onClicked: { var at = aAt.text ? (falcon.resolveDeadline(aAt.text) || aAt.text) : null
                                              falcon.call("alerts.create", {type: aType.currentText, audience: aAud.currentText, body: aBody.text, department_id: aDept.text ? parseInt(aDept.text) : null,
                                                                            account_ids: aTo.text ? view.ints(aTo.text) : null, deliver_at: at, action_link: aLink.text || null},
                                                          function(ok, r) { root.notify(ok ? "alert " + r.alert_id + (r.deliver_at ? " scheduled for " + r.deliver_at : " delivered") : r.message, !ok); if (ok) aBody.text = ""; view.refresh() }) } }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            // --- updates
            ColumnLayout {
                Label { color: Theme.text; font.bold: true; text: "current version: " + (view.health && view.health.version ? view.health.version.version_string : "(none approved)") }
                DataTable { Layout.fillWidth: true; Layout.preferredHeight: 160; rows: view.health ? view.health.departments : []
                            columns: ["department_name", "pcs", "current", "pending", "escalated"]; widths: ({department_name: 160, pcs: 60, current: 60, pending: 60, escalated: 70}) }
                Eyebrow { label: "PCs behind"; visible: !!(view.health && view.health.pcs_behind) }
                DataTable { Layout.fillWidth: true; Layout.fillHeight: true; visible: !!(view.health && view.health.pcs_behind); rows: view.health && view.health.pcs_behind ? view.health.pcs_behind : []
                            columns: ["pc_id", "hostname", "current_version_id"]; widths: ({pc_id: 60, hostname: 160, current_version_id: 100}) }
                RowLayout { visible: falcon.role === "super_user"
                    Field { id: newVersion; Layout.preferredWidth: 100; placeholderText: "version" }
                    Btn { text: "Approve"; enabled: newVersion.text.length > 0
                             onClicked: falcon.call("updates.approve", {version: newVersion.text}, function(ok, r) { root.notify(ok ? "version " + r.version + " approved" : r.message, !ok); view.refresh() }) }
                    Field { id: rollDept; Layout.preferredWidth: 70; placeholderText: "dept" }
                    Btn { text: "Roll out"; onClicked: falcon.call("updates.rollout_department", {department_id: rollDept.text ? parseInt(rollDept.text) : null},
                                                                     function(ok, r) { root.notify(ok ? (r.targeted.length ? "targeted " + r.targeted.length + " pc(s) for " + r.version : "everything is already on " + r.version) : r.message, !ok); view.refresh() }) }
                    Field { id: promptMsg; Layout.fillWidth: true; placeholderText: "message to that department's Admins" }
                    Btn { text: "Prompt Admins"; enabled: rollDept.text.length > 0
                             onClicked: falcon.call("updates.prompt_admin", {department_id: parseInt(rollDept.text), message: promptMsg.text || null}, function(ok, r) { root.notify(ok ? "department " + r.department_id + " prompted" : r.message, !ok) }) }
                }
            }

            // --- audit
            ColumnLayout {
                RowLayout {
                    Field { id: auditActor; Layout.preferredWidth: 80; placeholderText: "actor id"; onAccepted: view.refreshAudit() }
                    Field { id: auditPrefix; Layout.preferredWidth: 160; placeholderText: "action prefix e.g. session."; onAccepted: view.refreshAudit() }
                    Btn { text: "Filter"; onClicked: view.refreshAudit() }
                    Item { Layout.fillWidth: true }
                }
                DataTable { Layout.fillWidth: true; Layout.fillHeight: true; rows: view.audit
                            columns: ["occurred_at", "actor_name", "action_type", "target_type", "target_id", "detail"]
                            widths: ({occurred_at: 130, actor_name: 130, action_type: 180, target_type: 120, target_id: 70, detail: 500}); emptyText: "(no entries)" }
                Eyebrow { label: "deviations (identity expectations not met)"; visible: falcon.role === "super_user" }
                DataTable { Layout.fillWidth: true; Layout.preferredHeight: 120; visible: falcon.role === "super_user"; rows: view.deviations
                            columns: ["id", "expectation", "observed_account_id", "observed_pc_id", "detail", "detected_at"]
                            widths: ({id: 50, expectation: 160, observed_account_id: 90, observed_pc_id: 90, detail: 400, detected_at: 130}); emptyText: "(none)" }
            }

            // --- accounts / departments
            RowLayout {
                spacing: 10
                ColumnLayout {
                    Layout.preferredWidth: 360; Layout.fillHeight: true
                    Eyebrow { label: "departments" }
                    DataTable { Layout.fillWidth: true; Layout.fillHeight: true; rows: view.departments; columns: ["id", "name", "created_at"]; widths: ({id: 50, name: 160, created_at: 130}) }
                    RowLayout { visible: falcon.role === "super_user"
                        Field { id: deptName; Layout.fillWidth: true; placeholderText: "new department name" }
                        Btn { text: "Create"; enabled: deptName.text.length > 0
                                 onClicked: falcon.call("hierarchy.department_create", {name: deptName.text}, function(ok, r) { root.notify(ok ? "department " + r.department_id + " '" + r.name + "' created" : r.message, !ok); if (ok) deptName.text = ""; view.refresh() }) }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: Theme.surface; radius: Theme.radius; border.width: 1; border.color: Theme.border
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 6
                        Label { text: "Provision an account (+ its PC)"; color: Theme.text; font.bold: true }
                        RowLayout {
                            Picker { id: newRole; model: falcon.role === "super_user" ? ["admin", "worker"] : ["worker"]; Layout.preferredWidth: 110 }
                            Field { id: newHost; Layout.fillWidth: true; placeholderText: "hostname" }
                            Field { id: newDept; Layout.preferredWidth: 70; placeholderText: "dept id"; visible: falcon.role === "super_user" }
                            Btn { text: "Create"; enabled: newHost.text.length > 0
                                     onClicked: falcon.call("hierarchy.account_create", {role: newRole.currentText, hostname: newHost.text, department_id: newDept.text ? parseInt(newDept.text) : null},
                                                            function(ok, r) { if (!ok) { root.notify(r.message, true); return }
                                                                              issued.text = "account " + r.account_id + " (" + r.role + ") on pc " + r.pc_id + "\nclient_id: " + r.client_id + "\n(give this to the client install; it is not shown again)"
                                                                              root.notify("account " + r.account_id + " created — client_id shown in the Accounts tab", false); newHost.text = "" }) }
                        }
                        TextArea { id: issued; Layout.fillWidth: true; Layout.preferredHeight: 80; readOnly: true; font.family: Theme.mono; color: Theme.ok; selectByMouse: true }
                        RowLayout {
                            Field { id: offId; Layout.preferredWidth: 80; placeholderText: "account id" }
                            Btn { text: "Offboard"; enabled: offId.text.length > 0
                                     onClicked: falcon.call("hierarchy.account_offboard", {account_id: parseInt(offId.text)}, function(ok, r) { root.notify(ok ? "account " + r.account_id + " " + r.status : r.message, !ok) }) }
                            Btn { text: "Show"; enabled: offId.text.length > 0
                                     onClicked: falcon.call("hierarchy.account_get", {account_id: parseInt(offId.text)}, function(ok, r) { root.notify(ok ? r.name + ": " + falcon.pretty(r.account) : r.message, !ok) }) }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }
    }

    function ints(text) { return text.split(",").map(function(s) { return parseInt(s.trim()) }).filter(function(n) { return !isNaN(n) }) }
}
