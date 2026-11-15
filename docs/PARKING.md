# Parking Falcon

Decided by the user, 15 Nov 2026: Falcon is brought to a gentle stop and parked. Work moves to a new product, forked from it, in its own
repository: Detective as the umbrella, with Restricted under it.

Each session working here writes one line below when it reaches a safe stopping point: its current piece finished, tested and committed,
nothing half-done in the working tree, no test run of its own still going. Start nothing new.

The parking itself (a `PARKED.md`, `START-HERE.md` and `PHASES.md` updated, the final tag) happens once every active session has
written its line, and with the user's go.

## Safe to park

| Session | Date | Finished and committed | Left unfinished (and where it is written down) |
|---|---|---|---|
| Engine (seats, pricing and the new product's proposal) | 15 Nov 2026 | Yearly renewal in `docs/STORE-CONTRACT.md` (efd01c9); this note (d97a7b6); one seats warning per kind and end date, a renewal bought ahead seen (e55d468; `tests/test_seats.py` 9 passed, store and issue tests 21 passed) | Nothing in the code. The new product's proposal is the "The new product: Detective, with Restricted under it" doc (claude.ai/artifact/FuDY3bpPRvB6HRxc5Ai9Tj), with its open decisions at the end |
| Core-feature proposals (Windows' places, the machine snapshot, the file lineage) | 15 Nov 2026 | The proposals branch, merged into `main` (1f1f012) and deleted: Windows' own places for Detective (7513c7c), the machine snapshot (aa207a3), one identity for a file through rename, move and edit (d29cffc); suite in 16 batches on `falcon_test_proposals`, all pass but `test_flow_restricted`'s held-while-running test, the known load-only one (its file passes alone, 8/8, twice) | Habits (proposals item 4) and files made from restricted content with clipboard fingerprints (item 1, link 5), with the snapshot's BitLocker, printers, USB devices and healing: designed in full in `docs/design/proposals-core-features.md`, each listed in the new product's proposal under "Discussed, not built yet". Containment ("shrinking space": closing a machine's exits on a serious case) was discussed, not written down |
