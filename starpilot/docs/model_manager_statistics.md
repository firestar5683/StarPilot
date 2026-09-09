# Model Manager statistics (Dom)

## Scope and measurement contract

This feature adds file sizes, persistent observation-only driving statistics, hardware-only catalogue filtering, history, and revision/mode comparisons to classic Galaxy and Big Dipper. It does not select a model, change an engagement rule, publish controls, or register an engagement-critical managed process.

Per the UI requirement, **Assisted distance means assisted forward distance**, not manual-inclusive mileage. Cards show all-time standalone totals pooled across revisions. Model Lab pairs are separate configurations; pair-only use is labelled rather than attributed twice. Comparison rows separate loaded content, backend, ordered model roles and full/AOL mode. The selected 7/30-day period includes drives whose **start** is within that rolling window; it does not prorate a straddling drive. History uses the same selected period and mode.

- Distance integrates consecutive valid speed samples at most 250 ms apart. Reverse, missing CAN, stale services, missing matched runtime identity and ambiguous model switches create gaps, not invented mileage.
- SteeringPressed, brakePressed and **carState.gasPressed** trigger intervention episodes during assistance. StarPilot cruise-button accelPressed is not used. Overlapping inputs count once with per-input labels; a held input is one episode and release must last 2 s before rearming for new recordings (0.5 s in historical policy v1). A manually begun input is not later reclassified as an intervention.
- A brake takeover can count as one intervention and one disengagement, in distinct statistics. Enabled→disabled or AOL-only→off counts a disengagement. Shutdown/off-road/fallback gaps do not manufacture one.
- Event averages are exposure/count, not averages of completed intervals: intervention exposure excludes held/rearming inputs; disengagement exposure includes the assistance session even while actuators are inactive. Zero events are not infinite/best scores. This policy is disclosed in both comparison views. These are observations, not controlled model safety rankings.

## Runtime and persistence

`modeld` attaches the identity of the **actual loaded instance**, including built-in fallback, after successful modelV2 publication. SHA-256 hashes the bytes consumed by the existing pickle/OOB loader on that same open stream. It is a loaded-content digest, not a manifest-authenticity claim or a whole-file checksum of unused trailing bytes. No model file is reopened to guess loaded identity and no hashing runs during inference. If provenance instrumentation fails, that load retains an explicitly unverified UUID (or unavailable identity), never a fabricated revision.

Galaxy starts a low-priority optional observer child on device startup, independent of page visibility. It has no Params writes or publishers and is absent from managerState/processNotRunning. SQLite writes only occur in that child at `/data/starpilot/model_stats.sqlite`; APIs read it read-only. Stats survive model/route deletion.

Final-checkpoint failures retain cumulative snapshots across off-road and subsequent drives, retrying every 30 s. Retention is capped at **16 snapshots / 4 MiB conservative Python-size estimate**, plus one constant-size coverage-loss marker and the single frozen active reducer. Snapshots for the active drive coalesce. At saturation the observer latches collection off for its remaining lifetime, retains accepted counters and its bounded active reducer for retry, and logs an explicit resource-limit/coverage-loss error. It does not evict old counters and continue recording as if complete. After storage recovers, the loss marker is persisted; API `coverageLoss=true`, `status=degraded`, `trackingStatus=resource_limited` and both card views show **Tracking limited — coverage lost**. Comparisons remain incomplete even across a later observer restart: restarting cannot restore excluded coverage. During an unwritable-disk outage, that durable/UI marker cannot be guaranteed until recovery; the immediate signal is the observer log and stale/inactive database health, not a fabricated successful write.

Socket input remains non-conflated, but bulk draining is prohibited. Each receive pass round-robins all services and stops at **256 messages, 1 MiB raw/projected bytes or a 5 ms cooperative deadline**. One native raw message must be received before its length is knowable; payloads exceeding **64 KiB** are rejected before Cap'n Proto decoding. Decoding has an 8192-word traversal/16-level nesting limit and copies only observation scalars (not the full model payload). Projected object sizes are also checked before heap insertion. Retained reorder work is capped at **2048 events / 4 MiB estimated payload**, and reduction has its own 256-event/5 ms cooperative budget. Cooperative time/message/byte budget exhaustion preserves queued telemetry and yields; actual capacity/size/decode failures discard the reorder window, reset telemetry, and record a gap; pre-break backlog and old events cannot rejoin attribution. Model matching caches are capped at 256 entries each. A drive reducer freezes before reaching 128 metric rows, rather than dropping configurations. These conservative limits need native payload/rate validation and may deliberately exclude coverage under overload.

Repeated snapshots cannot refresh telemetry health. Stream breaks advance a semantic checkpoint revision exactly once, including overflow→off-road/shutdown without another carState, while keeping `lastTime` and SQLite telemetry `updated` unchanged. The missing-carState watchdog uses the same transition. Per-service monotonicity rejects delayed messages before road-state/engagement edge handling. AOL-only→full assistance is not a disengagement, regardless of whether the AOL flag remains set; the separate enabled→disabled policy is unchanged.

**Remaining durability/resource limits:** queued failed writes are in memory. Persistent storage failure followed by observer/process/power loss can lose unsaved counters and the not-yet-persisted loss marker; successful previous checkpoints remain. Normal sudden power loss can lose the interval since the last checkpoint. No claim of zero-loss journaling is made. Byte budgets estimate retained Python payloads, not a hard process RSS limit: interpreter/SQLite/native socket allocations, one oversized raw receive, and a single non-preemptible receive/decode/storage operation remain outside those cooperative deadlines. Storage retries have a bounded snapshot count but no hard wall-clock deadline. Target memory/CPU/storage/transport soak and fault injection remain mandatory.

## Verification and deployment gate

Focused tests use synthetic inputs and temporary databases. They exercise real reducer, telemetry adapter, store, Flask stats endpoint, presentation modules, and AST-extracted exact legacy/OOB loader functions. Browser fixtures are visibly labelled SYNTHETIC and never represented as real vehicle telemetry.

Run focused Python tests with pytest (pycapnp and Flask required), excluding the repository-wide native messaging conftest when using a host-only test environment:

```
python -m pytest --noconftest -o addopts='' starpilot/common/tests/test_model_stats*.py starpilot/system/tests/test_model_stats*.py starpilot/assets/tests/test_model_sizes.py starpilot/system/the_galaxy/tests/test_model_stats_api.py
node starpilot/system/the_galaxy/tests/test_model_metrics.mjs
```

The browser harness `starpilot/system/the_galaxy/tests/test_model_manager_browser.mjs` accepts `REPO`, `EVIDENCE`, `PLAYWRIGHT_MODULE` (module path), and `BROWSER_EXECUTABLE`. It uses network interception, never a running device. It checks classic/Big Dipper at 1200/390 px, hardware/favourite filters, selection unchanged, sorting, history open/pagination/close, 7/30/all comparisons, mode separation, overflow and download scroll preservation.

**Not installation sign-off:** native msgq/modeld/Galaxy startup, full target build, real route replay, runtime startup hashing cost, memory/storage/CPU soak and on-device fallback/publication continuity have not been verified by these host tests. A parent independent safety/integration review remains required before deployment. No device connection, copy, restart, push or PR is part of this work.

Installation is a mixed runtime/schema/backend batch, NOT a static UI hot-copy. With fresh explicit approval and the vehicle safely off-road: back up the exact source and SQLite/WAL closure, preserve unrelated installed work, rebuild changed cereal bindings and affected native dependants on the target architecture, activate coherent modeld/Galaxy/observer versions (normally an approved off-road restart/reboot), then verify matching publication timestamps, actual fallback identity, observer failure isolation, database/API readback and visual assets. Do not restart controls to activate this while driving. Keep rollback source and database backups; never erase the statistics database to hide a migration failure.

Merge overlap is limited to `cereal/custom.capnp`, `selfdrive/modeld/modeld.py`, `starpilot/system/the_galaxy/the_galaxy.py`, classic Model Manager JS/CSS and mobile ModelManager.js/material.css plus new statistics files. No personality, speed-control, Params registry, native settings or process_config edits are included.


## September 9 collector and history repair

The collector keeps its 5 ms / 256-message / 1 MiB pass budgets, reserving room
for one bounded message before receiving. Crossing a deadline after decode keeps
that sample. Real 2048-event / 4 MiB retained capacity, invalid decode, oversize
and 350 ms age exclusions still break continuity. Catch-up passes explicitly
yield the CPU for 1 ms. No publishers, control process changes or background
log replay are added. Diagnostics record fixed counters for each loss/yield
reason and wall/CPU/waiting maxima for receive, reduction and storage, logged
at most once a minute and copied into ordinary checkpoints. They are cumulative
for the observer process, not per-drive incident logs.

Schema remains version 1. New state metadata records logger CurrentRoute when
available (a bounded read at start/checkpoint only). Public route times include
the device timezone. UI association prefers exact route IDs; historical matching
allows at most 2 seconds of boundary skew and still requires one overlapping
route. A separate bounded driveSummaries response includes manual-only coverage;
missing data remains unknown and gaps remain visibly incomplete. Model engagement
maps unique historical display-name slugs to catalogue IDs, preserving explicit
IDs and refusing ambiguous aliases. The engagement percentage remains route time,
not an estimate from recovered assisted distance.

Explicit offline reconstruction uses the same reducer and loaded provenance.
model_stats_recovery.import_routes retains original rows and adds deterministic
recovered route IDs whose state.supersedes excludes partial originals from every
statistics read, including health/history. Supersession travels with recovered
rows through the existing backup format, so restore order cannot revive partial
counts. Imports validate counters/ownership, refuse reducing accepted per-owner
totals, back up SQLite consistently, commit all accepted routes atomically, and
add nothing on a repeated import. This recovery is an operator action, never an
observer or onroad job. Missing provenance/ambiguous fragments require review.

See the workspace stats-fix-20260909 report for actual target measurements,
retained-log recovery results and the remaining next-drive verification boundary.


September 9 evening follow-up: policy v2 requires all three inputs to remain
released continuously for two seconds before a new intervention episode can
start. Further inputs restart that clear interval; held/overlapping inputs remain
one episode. Disengagement transitions are unchanged. New snapshots record
definitionVersion=2 and interventionReleaseSeconds=2.0. History exposes these
fields, treating existing untagged records as v1/0.5 seconds. Historical counters
are preserved; lifetime totals can include records from both grouping policies.
The live API's top-level definitionVersion identifies the current recorder
policy, while each history row identifies the policy used for that recording.
