# Development Mapd shadow lifecycle

`MapdShadowEnabled` is an optional, persistent, nonlogged Boolean with default
false. The manager reads its exact raw `1` byte only onroad in a real car;
missing, malformed, symlinked, oversized or special-file values remain off.
The registered native child launches only the fixed packaged `mapd --shadow
--offline-root /data/media/0/starpilot/maps/offline` command. It uses the
ordinary manager SIGINT/SIGKILL stop path and reaps a failed child with a
bounded 1–60 second retry. The offline root must already exist under the new
StarPilot-owned storage tree. A named `OPENPILOT_PREFIX` uses its separate
`starpilot-<prefix>/maps/offline` store, shared with that instance's downloader. No legacy Mapd directory is moved, read as a
fallback, downloaded or repaired by this owner.

The package is **generated**, never committed. On a Linux ARM64 build host
with Go 1.25.1, cached pinned modules, C compiler and zlib, run
`python -m openpilot.starpilot.maps.package_shadow --go /absolute/pinned/go`
from the checkout. The recipe uses read-only modules and disabled Go network,
stamps the current provider source digest and pinned upstream revision, checks
the actual ELF ARM64/static headers and writes `provider/mapd` plus a bounded
manifest. Launch preflight checks the fixed files, executable permission,
binary hash, embedded stamps, current source digest/pin and an owned, non-symlink
offline root. A changed provider source or binary leaves the feature unavailable
until a matching package is rebuilt.

The root also requires an admitted `current.json` snapshot selector and a
bounded receipt whose exact bytes hash to the selected generation name.
Python preflight checks the selector/receipt identity; the Go shadow checks
aligned coverage metadata at startup and hashes/decodes each requested tile
against that pinned receipt. Admission is available through explicit offline
commands and the separate parked map-operation owner. Neither restarts an already running shadow, and prior
generations remain in place. See
`mapd_repo/maps/SNAPSHOTS.md` for format and import limitations.

`tools/release/release_files.py` copies **tracked files only**, so this generated
package is **not** in a release by default. A reviewed release assembly would
run the same packaging command with
`--output <staging>/openpilot/starpilot/maps/provider` **after** tracked source
copy and **before** image finalization. The disposable staging fixture test
checks this insertion path; it does not install anything or make an image.
There is no manager default shadow activation, `mapdIn` publisher,
plannerd subscription, or SLC numeric authority. Authenticated Galaxy can
request a bounded region download through the parked owner described in
`MAP_OPERATIONS.md`. Existing Galaxy observations remain diagnostic and `MapTracker` continues to return UNKNOWN
for control.

`TestShadowExecutableHostGpsIPC` explicitly requires a host Python and an
environment gate. It builds a temporary executable from the current pinned
toolchain, admits a tiny synthetic PBF with `--snapshot-admit`, then runs
**only** `--shadow` with private IPC/Params and the selected generated tile.
It verifies actual host GPS events through the Go subscriber,
MapdOut and Python status, including invalid/old GPS, fallback, stale loss,
restart and ignored non-GPS inputs. The fixture proves transport/lifecycle,
not map correctness, real offline data licensing, Linux device timing or a
qualified road speed limit. The full-provider path remains inactive; its
separate `mapdOut` queue-size mismatch and ungated car/model/selfdrive inputs
must be resolved before any future full mode.
