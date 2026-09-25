# Map provider source

This ordinary source folder starts from Jacob Pfeifer's mapd v2.3.1. The exact
commit, pristine tree and import exclusions are recorded in `../upstream-sync.json`.
The upstream MIT notice is retained in `LICENSE`. Map datasets have separate
attribution and distribution requirements; no map dataset is bundled here.

The tile loader validates the known reachable tile graph before caching it,
including road/node structure, geometry, text and speed values. Packed and decoded
sizes are bounded, historical tiles remain supported, and replaced or changed
files invalidate cached road evidence. Tests preserve valid empty coverage and a
synthetic road's identity, speed and geometry. This does not establish dataset
provenance or correct-road applicability; see `maps/OFFLINE_VALIDATION.md`.

Bearing alignment is a nonnegative undirected-axis penalty. The original angle
wrapping could give a negative penalty to a crossing road, increasing its score;
the regression covers cardinal and diagonal segments with wrapped headings.
This mathematical correction does not qualify the road-selection heuristic.

Downloads use an owned staging directory and validate the complete tar/gzip
archive before replacing installed files. Members are restricted to the requested
map group; links, escaping paths, duplicates and corrupt/truncated streams are
rejected. Failed downloads preserve prior files, shorter replacements have no
old suffix, and only successful installations count toward progress. Cancellation
and progress snapshots are tested with synthetic HTTP responses and temporary
directories. Each file replacement is atomic; a failure during installation can
still leave a group containing different dataset versions. Whole-group versioning,
install-time tile-content validation and authenticated dataset provenance remain
separate work; the loader checks content before using an installed tile.

From the repository root, with Go 1.25.1, a C compiler, pkg-config and zlib:

```sh
python3 tools/ci/run_map_tests.py --output /tmp/map-provider-check
```

The output directory must be new. The command records every Go test outcome,
vet/build results, source hashes, compiler build information and the binary hash.
Dependency resolution is read-only against go.mod/go.sum. The build explicitly
embeds the parent revision, pinned provider revision and actual source digest;
the provider logs those identifiers on startup. This avoids relying on automatic
VCS detection for the nested module. The evidence also records individual source
hashes, including local uncommitted changes. It builds for the current host and never starts the provider or downloads
maps. A Linux ARM64/device build remains a separate gate.

For a local development binary, `make -C mapd_repo build` uses the checked-in Go
bindings and a read-only module graph. It does not regenerate schemas, upgrade
dependencies, or download another Go toolchain. Install the pinned Go version
first. On Linux, `make -C mapd_repo build-static` additionally selects the pure-Go
network/user implementations and static linking. Both accept `BUILD_OUTPUT` to
choose the output file. These convenience binaries have unrecorded source stamps;
use the evidence runner above for a source-stamped test/build record.

Schema generation is a separate, deliberate operation. `capnp-deps` installs the
pinned Go plugin and its matching module-cache includes without creating a sibling
Git checkout. The container recipe supplies Go 1.25.1 explicitly and selects the
Linux static target; its existing entrypoint remains the map-data generation tool,
not a managed device-provider launcher.

The producer now reads both GPS sources and falls back from external to internal
GPS when needed. Python GPS Events carry MONOTONIC timestamps while Mapd output
uses BOOTTIME. V2 samples both clocks, rejects queued pre-start/resume fixes,
clears source evidence on a suspend offset step, and retains the accepted fix's
original observation time converted to BOOTTIME. The executable host fixture
uses the Python publisher's ordinary timestamp instead of overriding it.
External fixes expire
after 500 ms and internal fixes after 2 s, matching their different source rates.
The 50 m horizontal-accuracy ceiling is an input sanity bound, not proof that a
particular nearby road is correct. Invalid fixes and bearing values are rejected.
Boot-time timestamps use the same Linux clock as the host, with the same Apple
fallback. The publisher sends each queued sample once without refreshing its age.

Road computation runs before publication. Source changes, lost GPS, missing tiles
and failed road matches clear the old road, speed-limit and upcoming state. A
matched road without a posted limit has a distinct status and zero posted speed;
it does not inherit the previous road's accepted limit. The v1 output carries
original GPS time, computation time, source generation and a process session.
Historical fields and type IDs are retained. Messages without the v1 fields have
unknown sample evidence. A shared actual Go wire fixture is decoded by the host
Python tests; the compiled contract also retains historical field meanings.

The host has a compatible `MapdOut` schema and service registration. An
opt-in managed shadow and explicit local whole-generation snapshot admission
are implemented; see `maps/SNAPSHOTS.md`. In particular,
wrong-road/parallel-road/junction selection, heading accuracy and independent
source-age evidence still need
qualification. The provider's valid flag records its computed sample status; it
does not establish correct-road or installed-vehicle behavior. Host SLC must check
source and computation age, session/generation, numeric validity and match quality
before using a posted limit. No SLC control consumer is connected by this batch.

The existing SLC decision policy remains the control owner. Provider car/model
inputs do not yet have independent freshness gates, so suggested-speed and vision
curve outputs can retain stale input. Those outputs must not become SLC authority.
The manager entry remains default-off and launches only a packaged diagnostic
shadow with an admitted snapshot; no automatic download or control activation
is added. The host also restores the historical map input and extended
status reservations, with append-compatible fields from this provider. Original
helper type IDs, field meanings and input enum ordinals are retained inside the
reserved custom roots. Go and Python share synthetic status/input wire fixtures,
including a host-created input decoded by the provider. This defines the transport;
no settings command or download action is wired to it yet.

Schema updates use Cap'n Proto 1.0.1 and `capnpc-go` v3.1.0-alpha.2, matching the
Go dependency pin. Generate only the changed provider binding, then run the shared
Go/Python wire fixtures and compiled-layout tests before accepting the change.
