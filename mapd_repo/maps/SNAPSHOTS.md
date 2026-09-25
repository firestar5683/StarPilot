# Offline Map Snapshots (development admission)

The managed shadow reads only a selected, locally admitted snapshot. The fixed
owned root is `/data/media/0/starpilot/maps/offline`; admission does not create
that root, fetch data, stop or restart the shadow, enable SLC, or launch the full
provider. With no selected generation, the development shadow remains
unavailable. An already running shadow pins its prior generation until its next
normal process start.

The explicit offline `mapd --snapshot-admit` command takes
`--offline-root ABSOLUTE_EXISTING_ROOT`, aligned
`--min-lat/--min-lon/--max-lat/--max-lon`, and exactly one of
`--input-pbf LOCAL.osm.pbf` or `--archive-dir LOCAL_DIRECTORY`.
Use `--overlap` only in [0, 0.25) degrees (default 0.001).
Archive mode requires two-degree-aligned bounds and files named
`<archive-dir>/<lat>/<lon>.tar.gz`, with the checked upstream member layout
`offline/<lat>/<lon>/<0.25-degree-cell-name>`. Input files must be regular,
non-symlink leaves. The command is for explicitly supplied data and does not
make network requests. `--source-url` and `--source-date` are optional
caller claims recorded as **unverified**, never an authenticated upstream
release date. Empty cells in an admitted PBF region are materialized
deliberately; the ordinary `generate` command's flag now actually controls
whether it emits empty cells.

The separate, explicit `mapd --snapshot-fetch` development command requests
only the fixed HTTPS archive origin `https://map-data.pfeifer.dev/offline/`.
It takes the same existing absolute root and two-degree-aligned bounds, plus a
required `--max-bytes` total transfer budget. A single 30-minute deadline
covers every group transfer and admission; each HTTP request is also bounded
to 10 minutes. Redirects must stay on the same HTTPS origin. The complete
group set is derived from the requested bounds, fetched into owned temporary
staging, and passed to the same whole-generation admission checks. A failed,
truncated, canceled or over-budget fetch leaves the prior selector intact.
The command is intended for deliberate, parked developer use; it has no
onroad/offroad guard, manager trigger or UI control. Tests intercept the fixed
origin with a private synthetic HTTP server and never request real archives.
The receipt hashes the bytes actually received but cannot verify their
upstream provenance, acquisition date, licensing or road correctness. The
command logs the selected generation ID and OpenStreetMap attribution notice.

Admission stages the entire aligned region beneath `generations/.stage-*`.
For each expected cell, the existing bounded Cap'n Proto decoder checks
geometry and exact cell bounds; admission also checks overlap, a complete
cell list, no extras, regular files and exact bytes. It records input/archive
SHA-256 and size, source/build strings, settings, tile SHA-256/size/empty flag,
local receipt time and OpenStreetMap attribution. The receipt contains no
self-ID: its **exact canonical JSON bytes** hash to the 64-hex generation
directory name. The SHA-256 identifies observed bytes and this transformation;
it is not an upstream signature, map freshness, or road-truth proof.

After syncing all files/directories, admission publishes the immutable
generation directory and atomically replaces/fsyncs `current.json` containing
`{"version":1,"generation":"<receipt SHA-256>"}`. On an error or cancellation
before that selector change, the previous selection stays active. Previous
generations are never deleted or mutated by admission. If an identical ID
already exists, it is fully revalidated before reselection; a corrupted
existing directory is rejected. As with any local file protocol, root-level
tampering is outside this receipt's security claim. A running process stays
pinned to the directory/receipt it selected on startup. The owner does not
automatically stop it; opting out and back in or a later ordinary restart
selects the new generation.

Startup bounds and validates selector and receipt metadata, independently
recomputes the expected aligned cell names, and binds the cache to the exact
receipt ID. It does **not** read every tile on each drive. The existing loader
opens only the requested cell with no-follow/nonblocking regular-file checks,
hashes the same bounded bytes it decodes, compares them to its pinned receipt,
and clears road evidence if a requested cell is absent, corrupt, changed or
outside the admitted region. This keeps startup independent of total dataset
bytes while keeping newly observed road evidence tied to an admitted tile.

The pinned upstream scripts use an OSM PBF, highway filter, regional extract,
way-node location pass, generator and per-group tar.gz upload. Neither those
scripts nor the tile format provide a signed release manifest, per-archive
upstream hash, extract timestamp or a data-attribution receipt. The software's
MIT license does not license the map data. OpenStreetMap data require
OpenStreetMap/contributor attribution and ODbL notice; any particular
redistributed archive still needs its data provenance and distribution review.
No map dataset is bundled. Snapshot consistency does not qualify a unique
road match or posted-limit applicability; StarPilot map SLC remains UNKNOWN.
