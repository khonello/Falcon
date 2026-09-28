import QtQuick
import QtQuick.Layouts
import "."

// Out of place, opened (board K06). The fourth subject, and the plainest shape: three full-width
// bands, stacked, going from shape to words as you read DOWN rather than across.
//
// Its subject is small -- a file or two, a deviation or two -- so it wants no hero at all. What it
// wants is the ledger: every tier, every moment, and then what it adds up to.
Item {
    id: page
    objectName: "openedOutOfPlace"
    property var view: null

    readonly property var deviationMarks: {
        var out = []
        for (var i = 0; i < page.view.deviations.length; i++) {
            var d = page.view.deviations[i]
            var at = page.view.hoursOf(d.detected_at)
            if (isNaN(at)) continue
            var words = String(d.expectation).replace(/_/g, " ")
            out.push({ at: at, what: words.charAt(0).toUpperCase() + words.slice(1),
                       addressed: !!d.resolved_at })
        }
        return out.sort(function (a, b) { return a.at - b.at })
    }
    // the tier rows, with the file that broke the rule named on the line it broke
    readonly property var tierNotes: {
        var out = ({})
        for (var i = 0; i < page.view.violations.length; i++) {
            var v = page.view.violations[i]
            // the notes are keyed the way the rows are labelled, "/restricted/" and not "restricted"
            var key = page.view.tierLabels[v.resource_tag] || v.resource_tag
            if (out[key]) continue
            out[key] = v.filename + " on " + v.hostname
                       + (v.path ? ", sitting in " + String(v.path).replace(/.*\/([^/]+)\/[^/]*$/, "/$1/") : "")
        }
        return out
    }

    readonly property var filesSays: falcon.narrate("violations", { violations: page.view.violations })
    readonly property var devSays: falcon.narrate("deviations", { deviations: page.view.deviations })
    readonly property var sumSays: falcon.narrate("out_of_place", {
        violations: page.view.violations, deviations: page.view.deviations })

    ColumnLayout {
        anchors.fill: parent
        spacing: 20

        // --- every tier, always all four: a zero is a result and keeps its row
        GridCell {
            objectName: "placeTiers"
            Layout.fillWidth: true
            Layout.fillHeight: false
            // sized by what it holds, not by a fraction of the window: a band that is a few
            // pixels short clips a row, and a tier row must never be the one that goes missing.
            // 77 is the cell's own furniture -- its title line and its padding.
            Layout.preferredHeight: 77 + tiers.implicitHeight
            title: "Files against their tier"
            narration: page.filesSays

            TierBars {
                id: tiers
                width: parent.width
                barHeight: 17
                rowGap: 26
                rows: page.view.tierRows
                notes: page.tierNotes
            }
        }

        // --- the same day the sessions were drawn on, with a mark per deviation
        GridCell {
            objectName: "placeDeviations"
            Layout.fillWidth: true
            // the one band that stretches: a day with more marks on it can use the room, and the
            // two bands either side of it are the size of what they hold
            Layout.fillHeight: true
            Layout.minimumHeight: 77 + strip.implicitHeight + 34 + devSentence.implicitHeight
            title: "Deviations today"
            narration: page.devSays

            DevStrip {
                id: strip
                width: parent.width
                marks: page.deviationMarks
                fromHour: page.view.windowStart
                toHour: page.view.windowEnd
            }
            // an axis is never left bare (PATTERNS 0): the legend names what the two marks mean
            Legend {
                items: [{ label: "Logged, still open", color: Theme.warn, round: true },
                        { label: "Addressed", color: Theme.dim, round: true }]
                note: page.deviationMarks.length === 0 ? "nothing logged today" : ""
            }
            Sentence {
                id: devSentence
                width: parent.width
                text: page.devSays.sentence
            }
        }

        // --- and what the two records add up to. The words keep the body's width; a fact row
        //     stretched across the whole frame stops being a line and becomes a table.
        GridCell {
            objectName: "placeReading"
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 77 + reading.implicitHeight
            title: "What it adds up to"
            topAlign: true
            narration: page.sumSays

            ReadingBody {
                id: reading
                width: Math.min(620, parent.width)
                narration: page.sumSays
                maxFacts: 3
                onActionTriggered: shell.notify(narration.action + " — not wired yet", false)
            }
        }
    }
}
