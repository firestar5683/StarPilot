# Community judging preparation

Agent 3 scope: Mac-only route preparation. This package has no SSH, device, replay,
composer, worker or audio-output control. Final RoadScore generation is deliberately
absent. Do not start it as part of preparation.

## Current handoff

The repository guidance, STATUS.md, README.md and EVENT.md were reviewed. No applicable
AGENTS.md was found in the root or RoadScore tree. The only repository AGENTS.md,
under tinygrad_repo/, was also read: it specifies tinygrad test/typecheck/lint commands
and prohibits commit amendments. No tinygrad changes were made. EVENT.md records the native
prerequisite pass, but subjective listening and community judging remain pending.
The user explicitly authorized community preparation while reserving hardware for
another agent.

The user subsequently identified `ROADSCORE_COMMA_HACK_7_CONTEXT.md` in the integration
checkout. It was read in full; its private appendix supplies the community entries.
The eleven context candidates plus the explicitly reported duplicate reconstruct
twelve submission instances, normalized to eleven distinct candidates, preserving the duplicate's
provenance and the integration owner's existing labels and deterministic seeds.
All live data, mappings, metadata and decisions are in ignored local results/.
Final generation is not authorized and has not been run.

Connect semantics were checked against upstream commit
[`5c7f276`](https://github.com/commaai/connect/blob/5c7f27617371a2503c360ff1d08bf19966d2527c/src/url.js#L27):
URL suffixes are seconds, not segment indices. Its current
[route reducer](https://github.com/commaai/connect/blob/5c7f27617371a2503c360ff1d08bf19966d2527c/src/reducers/globalState.js#L432)
uses the full route when only a start suffix is supplied. The user explicitly chose
that full-route behavior for the ambiguous single-timestamp submission. The explicit
two-timestamp submission retains its exact end-exclusive interval. Private handoff
files record the concrete ranges without exposing them in tracked documentation.

## Input and normalization

Store inputs in an ignored `roadscore/results/community_INPUT/submissions.private.json`.
Use a JSON array of route strings or objects with `route`, optional `submitter`, `note`,
and selection fields. For example (synthetic identifiers only):

```json
[
  {"route":"0000000000000000/2026-01-01--00-00-00", "segments":[2,3]},
  {"route":"0000000000000001|2026-01-01--00-00-00", "start_s":60, "end_s":120}
]
```

Supported inputs: `DONGLE/ROUTE`, `DONGLE|ROUTE`, HTTPS comma/Konik Connect route links. In **bare native identifiers**,
`--N` or `/N` selects one segment and `/START:STOP` an end-exclusive segment slice.
In **Connect URLs**, `/START/END` denotes seconds, and a lone positive `/START`
remains pending intent confirmation because the current web page displays the full route.
Explicit `segments` are sorted and deduplicated. No selection means the full route.
Time bounds are route-relative seconds, with exclusive end. URL queries/fragments,
open native slices, dash ranges, conflicting selections and mixed time/segment selections
block preparation rather than guessing. Convert those using the submitter's intent
and retain the original text/decision in `note`. Never infer a time range from a URL
without checking its semantics.

Exact normalized route+selection duplicates collapse, retaining submission references.
Different selections of the same route remain distinct and require an explicit
`--acknowledge-same-route-selections` decision; the tool does not silently merge them.
Eleven unique selections are required for A–K. A failed attempt writes only its
normalization report; correct the source and use a fresh output directory.

```sh
python3 roadscore/judging/prepare.py prepare \
  --submissions roadscore/results/community_INPUT/submissions.private.json \
  --output roadscore/results/community_BATCH
```

The private manifest preserves source checksum, exact selection and provenance.
Use `--existing-manifest PATH` to preserve a previously issued mapping and seeds.
Otherwise a random permutation is drawn once with SystemRandom and frozen on disk.
Seeds always derive from SHA256 of `roadscore-judging-v1:` plus canonical route,
first four bytes big endian; labels and submission order do not affect seeds. The tool
refuses an existing output directory. The blind batch ID hashes the private mapping;
no identity or submitter is included in the blind folder. Commit only source; all
batch outputs belong under ignored results/. Do not publish recordings or mappings.

## Cache and characterize on the Mac

Local cache sources are read-only. Copies are written under the chosen batch only;
no existing score archives, driver camera, weights or generation assets are copied.

```sh
python3 roadscore/judging/prepare.py cache \
  --manifest roadscore/results/community_BATCH/manifest.private.json \
  --source /Users/dominickthompson/Desktop/RoadScore/routes
```

Missing rlog/front camera and segment holes remain explicit failures. qlog/qcamera
are retained as diagnostic alternatives but do not satisfy the full-data gate.
Each copied file has byte count and SHA-256; corrupt cached copies are repaired from
the source. Local presence cannot prove remote EOF, so extent stays unverified.

For uncached routes, run the following using an existing **Mac** Python environment
with openpilot imports, native API authentication and requests available:

```sh
python3 roadscore/judging/prepare.py metadata \
  --manifest roadscore/results/community_BATCH/manifest.private.json
python3 roadscore/judging/prepare.py fetch --logs-only \
  --manifest roadscore/results/community_BATCH/manifest.private.json
python3 roadscore/judging/analyze.py \
  --manifest roadscore/results/community_BATCH/manifest.private.json
```

Fetch uses the repository's authenticated route API host fallback and HTTPS assets.
It downloads selected full logs and front camera, reuses verified files,
and saves no tokens or signed URLs. Authentication, access and download failures are
reported by exception type without leaking signed URL text. A fetched listing proves
only the available remote extent, not that the owner uploaded every recorded segment.
The default free-space reserve is 8 GiB, checked before and during each download.
Use `--logs-only` for characterization first, `--preview-video` for smaller qcamera
previews, or omit both for full front video when space allows. Missing rlogs fall back
to qlogs for partial characterization; they remain failures of the full-log gate. Metadata/analysis do not declare missing video ready. No hardware access or
score generation follows fetch.

Time-to-segment conversion is nominal 60 seconds. Remote fetch also obtains segment
zero as a log-only clock reference for time selections. Analysis uses original log
timestamps and an end-exclusive cut; the reference segment never contributes to a
later excerpt's statistics. Local-only caches lacking segment zero remain blocked.
Camera decode and timestamp alignment still require later replay validation.

Analysis checks original log hashes, inventories valid message types/rates/gaps,
records timestamp reversals, speed/steering distributions and navigation/blinker
sample coverage. The private reports remain outside the blind folder. These are
technical proxies, not route quality rankings. They must never be imported into the
causal music runtime or used to select a favorable seed. Missing data is not a pass.

## Blind judging and later handoff

Open `blind/index.html` locally and load its adjacent `batch.json`. The page uses no
network requests and supports A–K navigation, explicit local media attachment,
1–5 / not-observable ratings, notes, browser-local save and JSON export tied to the
batch ID and anonymous judging session. Playback never autostarts. Browser storage
may be unavailable on file URLs; export remains available. Reopened recordings must
be reattached and acknowledged as reviewed. Blank scores are not zeros. Only give
judges the blind folder and deliberately anonymized approved recordings; never serve
the parent batch directory. Road footage itself can reveal recognizable locations.

Before the hardware owner later runs final generation, review each private selection,
cache completeness/extent, message coverage and clock ambiguity. Use the same Prism configuration, quality/gesture policy and deterministic route-derived
seed policy consistently across candidates. One official run per candidate is allowed
unless technically invalid; automatic normal quality rerolls remain allowed. Preserve
failed runs; do not choose a winning seed from offline route characterization. Use the
existing event replay audit for timing/causality evidence and collect human ratings
separately. Keep identity reveal and any winner decision deferred until judging ends.

## Validation

```sh
python3 -m unittest discover -s roadscore/judging -p 'test_*.py'
```

Tests cover normalization/deduplication, explicit range semantics, frozen blind mapping,
privacy boundary, missing/corrupt cache data, and technical analysis validity/time cuts.
No real routes, network, device access or music generation are needed for tests.

Nine synthetic preparation/cache/analysis tests pass, including resumable authenticated
fetch mocks and Connect/native range distinctions. Python compilation and JavaScript
syntax checks pass. Interactive browser verification was not completed: the browser
security policy rejected the local file URL. No workaround or audio playback was used.

## Offline integration export

`export_handoff.py` adapts the preserved preparation manifest to the event runner's
`submissions`, `start_seconds`, and `duration_seconds` schema. It preserves the
existing labels, seeds and configuration, and rejects unresolved ranges. Always
choose a fresh ignored output directory; it never overwrites integration manifests
or official-attempt ledgers.

```sh
python3 roadscore/judging/export_handoff.py \
  --manifest roadscore/results/community_BATCH/manifest.private.json \
  --output roadscore/results/community_EXPORT
```

The default verifies cached hashes and writes a private transfer plan, without
copying assets. `--materialize` copies those verified assets to a new portable
`routes/` native layout, retaining an 8 GiB disk reserve (`--reserve-gib`). It does
not access the device or download files. Copy failures preserve originals and
remove partial copies. Local `prepare.py cache` copies enforce the same reserve.
Fetch retries preserve unprocessed inventory even if a download fails midway.

A native `cache_manifest.json` is emitted only for complete selected full logs,
route-zero clock reference, full front camera, verified extent and completed
analysis. Incomplete materialized caches carry `.acquiring` and cannot pass the
normal complete-cache check. qlogs/previews remain diagnostics. Excerpt caches
cover the selected interval and reference only; their manifest does not claim
whole-route completeness.

The export always sets `generation_authorized: false`. Its schema is
`roadscore-judging-handoff-v1`; the runner must reject it unless generation is
explicitly authorized, `preparation_ready` is true, and `preparation_blockers` is
empty. Frozen configuration, hardware handoff, physical/cache transfer and existing
official-attempt reconciliation still belong to the integration owner. Neither
exporting nor cache materialization grants generation permission. Never replace
an existing attempt merely to adopt this schema.
