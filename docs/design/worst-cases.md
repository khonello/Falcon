# Worst cases, clamped (the owner, 18 Oct 2026: "always consider worse case scenarios in all cases for all features so we can clamp things")

Every feature is built for the day somebody points it at the biggest thing it can be pointed at. A clamp is never silent: it says what the limit is, what was asked, and what to do instead.
This is the list of what has a clamp, where, and what it costs. Add to it when something new is built; a feature without a line here has not had its worst case thought about.

## Hot and cold (indexing and the system's own background work)
`common/heat.py`. Anything that happens to a file, a program or a machine marks it **hot** (fully warm for ten to fifteen minutes, then cooling by itself), and work that is waiting
goes to the hot things first. Cold things are not skipped, only later: heat decides the order and never who is left out.

| Work | What is hot | Effect |
|---|---|---|
| Worker idle sweep, and the catch-up after a gap (`worker_client/watcher.py`) | a file that had any event, or was opened (the file trace), and every folder above it | the walk goes to hot folders and files first, so the file in use is reached before the other million; a hot file is sent at once, not left to fill a batch |
| the same sweep | a file whose size and modified time are unchanged since the Engine took it | its hash is reused, not read again: a sweep of a big folder does not read every cold byte to find nothing changed |
| Worker inventory (`worker_client/inventory.py`) | a program that just started | it leads every list sent; a program the installed list has never heard of brings the installed-programs read forward from six hours to about ninety seconds |
| Engine flow healing and catch-up (`engine/flow/sync.py`) | a machine that spoke or was asked about, a file that had an event | flows on hot machines are healed first; a catch-up sends the files being worked on first |
| Engine mark healing (`engine/console/marks.py`) | the machines in use | hot machines' marks are checked first |

## Limits
| Where | Limit | What happens past it |
|---|---|---|
| Marking a folder restricted | 20,000 files tracked by content per mark; 100,000 per machine; more than 2,000 needs confirming | `marks.assess` says how many files, how many are generated (node_modules, .git, venv, build, dist ... are covered by the mark but never tracked one by one), a pessimistic time (20 ms a file), the heaviest sub-folders, and a verdict; `marks.create` refuses the too large with that reason (nothing is half done) and asks for `confirm_large` for the large |
| Healing marks | 4,000 content hashes a pass, rotating | a huge mark is covered over several passes, hot machines first, instead of one pass taking for ever |
| A flow's catch-up listing | 200,000 entries; 2,000 taken from one message | the rest is caught up by the next healing pass (hot first) |
| One sweep message | 2,000 entries | the rest is ignored (a Worker sends a few hundred) |
| Worker running programs / processes / installed programs | 500 / 80 / 3,000 per report | hot programs lead, so the clamp drops the coldest |
| Worker offline journal | 20,000 events | the reconcile after it finds the rest by the file's own time |
| Heat itself | 50,000 keys on a Worker, 100,000 on the Engine | the coldest are forgotten first |
| Detective memory | 6 hours of detail, 30 days / 4,000 stages on the board, 60,000 events replayed at a restart | oldest first |
| Idle-time ETW | 5,000 opened files, 20,000 "last touched" per Worker | oldest first |
| A restricted flow | (not a clamp) | a flow never touches a restricted file, checked every step |

## Not yet looked at (to do when each is next touched)
Reports and the audit trail listings (page sizes), the file search results, the Task proposal queue for a long run of tasks, and the console's own lists. Each should get a line here
with its limit, and a message that says it was cut.
