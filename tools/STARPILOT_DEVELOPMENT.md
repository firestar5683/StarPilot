# StarPilot developer commands

The root commands are a supported developer interface. `./build` produces
device artifacts. `./dev` builds and runs desktop tools in a separate source
cache. The UI remains the custom large and compact Raylib UI.

| Command | Purpose |
| --- | --- |
| `./build [jobs] [SCons arguments]` | Complete Linux ARM64 device build |
| `./build --panda [jobs]` | Build the currently supported signed H7 firmware targets |
| `./build --params [jobs]` | Build the device Params library |
| `./build --cereal [jobs]` | Build the current schema, messaging libraries and bridge |
| `./c3 [jobs]`, `./c4 [jobs]` | Large and compact custom desktop UI |
| `./onroad [jobs] [--c3\|--c4\|--all\|--replay-only] <route>` | Route replay with selected desktop UI(s) |
| `./dev replay [jobs] <replay arguments>` | Native replay and its terminal controls |
| `./dev cabana [jobs] <arguments>` | Native Cabana in an independent cache |
| `./dev plotjuggler [jobs] <arguments>` | Current PlotJuggler helper; `juggle` is an alias |
| `./dev galaxy [jobs] [--live [--no-autoreload]] [--port N]` | Authenticated local Galaxy server; `--live` follows Galaxy edits |
| `./dev python <arguments>` | Python with host native libraries and current source |
| `./dev pytest <arguments>` | pytest, including its xdist and mock plugins |
| `./dev shell` | Shell with host imports and private settings |
| `./dev sync [shared\|cabana]` | Refresh source and dependencies without launching a tool |
| `./test` | Run lint, packaging, startup, control, model, UI and selected vehicle regressions |
| `./test --full` | Run the complete Linux pre-deployment suite, including recorded routes and replay |

`./tool` and `./tools/host` are aliases for `./dev`. The `c3`, `c4`, and
`onroad` commands can also be written as `./dev c3`, etc. Run `./dev help`,
`./c3 --help`, `./c4 --help`, or `./onroad --help` without installing or
building anything. Scripts resolve paths relative to the checkout, so invoking
an absolute launcher path from another directory also works.

## Setup and build separation

Run `./test` before pushing local changes. It checks the current files, including
uncommitted edits, in the existing shared host cache. Native dependencies are
built incrementally there; device binaries and the source checkout are preserved.
Each run prints its report directory, saves individual logs and test results,
and returns a nonzero status on failure. First-time dependency setup takes longer
than subsequent runs. Run `./test --help` without preparing an environment.
The updater shell checks require GNU timeout; on macOS install it with
`brew install coreutils`. Standard Homebrew locations are detected automatically.

The default is a focused regression check, not every CI job. `./test --full`
uses the existing Linux pre-deployment runner for the full host build, unit,
vehicle, native protocol, recorded-route and process-replay checks. It requires
the [CI prerequisites](ci/README.md); `--download` permits pinned route downloads,
and process replay may fetch its own logs. Neither command replaces the device
build or physical vehicle validation. Logs default to a new temporary directory;
use `--output /path/to/new-directory` to choose a persistent location.

Desktop tools require macOS or Linux, Git, uv, and a working native C/C++
compiler. Run `tools/setup_dependencies.sh` in this checkout for prerequisites. The first
desktop command installs the locked Python 3.12 environment and selected
developer dependencies in its own cache. It does not reuse a device venv.
Native bindings are built with the current SCons graph before launching.
Python, pytest and shell also build the generated longitudinal MPC and location
filter libraries. There is no automatic manager launch, firmware flash, or
vehicle connection in these host commands.

Device build setup and sysroot instructions are in
[laptop-device-build.md](../docs/how-to/laptop-device-build.md).
`./build --panda` builds the targets present in this branch: `panda_h7` and
`body_h7`. Other historical firmware variants are not implemented by this
branch's Panda graph; their migration is a separate vehicle/platform obligation.
Compilation alone does not qualify a vehicle port or a road-test candidate.

## Incremental source and state

Host runtime files live under `.host_runtime/<system>-<architecture>/shared/`.
Cabana uses the adjacent `cabana/` bucket, allowing it to run alongside
PlotJuggler or replay. Commands in one bucket wait for the current session to
exit before changing its source or native libraries. The lock is held until
the launched command exits and is released by the OS after a crash.

Each launch copies current tracked source and unignored new files, including
uncommitted edits. Deleted source is removed from the cache; ignored native
build outputs are not copied from the main checkout. Unchanged host build
outputs stay available for incremental builds. The cache has its own Git index
and refs, with read-only access to source objects; it never shares the source
index or runs checkout/reset cleanup against the developer's tree. Cache pushes
are disabled. Make source edits in the main checkout, since the next sync
replaces cached source edits.

The host venv and Params live in the bucket. Messaging uses a stable, unique
checkout-and-bucket prefix. PC runtime support files, including Galaxy's local
credentials, use the corresponding `~/.commastarpilot-dev-<id>/` directory;
ordinary `~/.comma` settings are not reused. Keeping the user's normal HOME
also preserves route authentication. Download caches are separate from Params.
Onroad sessions use disposable Params and a dedicated `replay-...` namespace.

To force a clean desktop rebuild, stop the relevant command and remove only
that bucket under `.host_runtime`. This does not delete the main checkout's
device artifacts. Deleting a bucket removes its private Params; the separately
prefixed home directory holds the local Galaxy credentials described above.

## UI assets and replay compatibility

The preserved bitmap UI requires its exact reviewed font bundle. Set
`STARPILOT_UI_FONT_DIR` to that complete local directory. Inter and Unifont
bitmaps and their notices are bundled; Como Heavy is still externally
provisioned. An incomplete or changed bundle produces an explicit error rather
than silently substituting fonts and changing UI metrics.

`./onroad` forwards current replay options such as `--start`, `--playback`,
`--data_dir`, `--no-loop`, `--no-vipc`, and `--demo`. An explicit UI choice avoids
automatic selection from logged device metadata. `--prefix replay-NAME` selects
a private session name. Playback uses the current native terminal controls.
Route access may require authentication or download the route the developer
requests. This is log playback; it does not run a driving manager or send CAN.

The UI uses the route's recorded device type, registered saved settings and
compatible versioned caches. Message freshness follows recorded time, including
playback speed, pause and seeking; recorded messages are not rewritten. Seeking
clears the previous display observations. A dead replay publisher invalidates
the display clock even while paused. Recorded wheel actions are not executed.
An explicit `--c3`, `--c4` or `--all` overrides the screen format while retaining
the recorded device identity.

Some preferences, including custom layouts, may be absent from the log. Supply
`--params /absolute/path/to/saved/params` to supplement them with a flat saved
Params snapshot. The snapshot is read only; credentials and unqualified binary
caches are excluded. Without that snapshot, missing settings use defaults, so
the preview cannot reproduce unlogged preferences. Displays requiring both
recorded monotonic and boot clocks remain unavailable until a recorded clock
pair establishes their relationship.

`./onroad -alert` previews a synthetic critical visual alert in the private
replay session; it never publishes car control. `./onroad --cem` and `--csc`
show labeled synthetic CEM and curve visuals in that private UI session. They
change presentation only; they do not create driving acknowledgments or qualify
the current control features. The legacy navigation and combined Galaxy replay
demo switches still need adapters for this branch's current services. They fail
explicitly while absent. `./dev galaxy` starts the implemented local Galaxy
server independently; set its local password in the desktop UI first. Galaxy
continues to use its existing authenticated loopback interface. Add `--live` to
release the shared lock after building and follow edits under
`openpilot/starpilot/galaxy`; see its README.

Developer compatibility remains a release requirement. Launcher/parser tests,
native desktop builds, UI/replay smoke checks, complete device builds, and the
existing safety/vehicle suites provide different evidence; none substitutes
for the others. Remaining demo and firmware variants must not be counted as
full compatibility just because the root command exists.
