# Model statistics recorder

The optional Galaxy-owned observer records assisted forward distance, interventions and disengagements against the model instance that produced successful output. Model identity includes ordered lateral/longitudinal roles, backend and a SHA-256 digest of bytes consumed by the existing loader. Instrumentation failure produces an unverified load UUID or unavailable coverage. No model hashing occurs during inference.

Policy v2 combines held/overlapping steering, brake and gas inputs into an episode, then requires two continuous clear seconds before rearming. Intervention exposure excludes held/rearming inputs; disengagement exposure includes the assistance session, including temporarily inactive actuators. Rates are exposure divided by event count; zero events have no event rate. Distance excludes manual driving, reverse, missing CAN, stale services, ambiguous model switches and gaps over 250 ms. Full engagement and AOL remain distinct modes. Shutdown or missing telemetry cannot manufacture a disengagement.

Historical records retain their definition version. Untagged records use historical policy v1 (0.5-second release). Mixed/unknown definitions retain counters and distance but cannot produce comparable pooled event rates. Standalone model totals and paired configurations remain separate.

## Runtime and storage

Galaxy starts a supervised low-priority observer only on device startup, never in response to a page request. It is absent from managerState and publishes no messages or Params. Seven non-conflated subscribers preserve intervention edges. SQLite checkpoints run only in that child at `/data/starpilot/model_stats.sqlite`, with a single-writer lock, WAL and FULL synchronization. Galaxy's read-only API uses a coherent SQLite read transaction. Successful checkpoints persist across model and route deletion; sudden power loss can lose the most recent uncheckpointed interval.

Each receive pass yields at 256 messages, 1 MiB or a cooperative 5 ms deadline. Raw events above 64 KiB are rejected before bounded Cap'n Proto decoding. Pending data is limited to 2048 events / 4 MiB estimated payload; reduction has its own 256-event/5 ms budget. Capacity loss creates explicit gaps; ordinary cooperative yields preserve data. Model caches hold at most 256 entries; a drive freezes before 128 metric rows. Failed checkpoints retain at most 16 snapshots / 4 MiB plus bounded active/loss state, then suspend recording and preserve coverage-loss metadata rather than silently discard accepted counters. Diagnostics record fixed loss/yield and timing counters.

These are cooperative bounds, not hard RSS or wall-clock limits. Native receive allocation, a single decode, interpreter/SQLite overhead and storage latency remain outside the timing budget. Storage/power loss may erase unsaved data and an unpersisted coverage marker.

## Vehicle snapshot

StarPilot's existing carState reader writes an atomic JSON snapshot into tmpfs. Galaxy parked authorization and cruise/steering/CAN diagnostics use it without opening additional carState readers. The original source monotonic timestamp expires after 100 ms; missing, malformed, invalid, future or stale snapshots fail closed. Rewriting a cached message cannot renew freshness. Snapshot write failures return without terminating StarPilot.

## Read API and recovery

`GET /api/models/stats` supports `model`, `mode=all|full|aol`, `period=all|7|30`, `limit=1..200` and `offset=0..9223372036854775807`. Period selection uses drive start. Unknown filters are rejected. `ModelStatsAPI.summary()` caches a defensive copy for two seconds; `annotate(models)` attaches statistics to catalogue dictionaries containing `value`. Presentation and file sizes are separate features.

Explicit offline `model_stats_recovery.import_routes` accepts reviewed reconstructed routes. The caller must establish off-road state and exclude concurrent collection/restore. Recovery checks provenance, policy and counters, refuses reductions or ambiguous fragment assignment, backs up the database consistently, then commits accepted routes atomically. Original rows remain; superseded fragments are excluded from all read totals and health queries. Repeated identical imports add nothing. Recovery is never a background or driving-time job.

## Validation boundary

Focused tests cover reducer behavior, identity loaders, schema serialization, storage/restart integrity, recovery, measurement cohorts, bounded overload, API filtering and snapshot freshness/faults. Host-native synthetic probes validate isolated transport and measure local overhead only. Matching target schema/native builds, actual onroad reader occupancy, drive-time capture continuity, target resource soak, power-loss behavior and hardware/fallback integration remain unverified for this split.
