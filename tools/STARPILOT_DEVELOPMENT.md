# StarPilot Development

This branch uses a split development flow:

- `./build` keeps producing device-target (`larch64`) artifacts for comma runtime compatibility.
- `./dev`, `./tool`, `./tools/host`, `./c3`, and `./c4` use an isolated host cache under `.host_runtime/` for native macOS/Linux tooling.

The goal is simple: keep the device build intact, keep host tools consistent with runtime behavior, and stop polluting the repo with host-only `.so`, `.o`, and desktop UI artifacts.

## Prerequisites

- On Ubuntu/Linux, run `tools/install_ubuntu_dependencies.sh`
  - `tools/ubuntu_setup.sh` runs both the Ubuntu and Python dependency installers
- Run `tools/install_python_dependencies.sh`
- Have `uv` available in your shell
- For device-target builds, install Docker Desktop or Podman with Linux/aarch64 support

## One-time device build setup

Fast path:

```bash
scripts/laptop_device_build.sh setup
```

Equivalent wrapper:

```bash
scripts/starpilot_build_flow.sh laptop-setup
```

If you need the manual sysroot flow instead:

```bash
scripts/laptop_device_build.sh build-image
scripts/laptop_device_build.sh setup-sysroot-agnos
```

Or from a physical comma:

```bash
scripts/laptop_device_build.sh setup-sysroot <device-ip> comma 22
scripts/laptop_device_build.sh build-image
```

## Device-target build flow

This stays the same:

```bash
./build
```

Equivalent long form:

```bash
scripts/laptop_device_build.sh build
```

This is the path you use for the actual comma/device-compatible build. It writes the normal device artifacts and does not depend on `.host_runtime`.

## Host tooling flow

Use the shorthand launchers for host-native tools:

```bash
./dev <command> [args...]
./tool <command> [args...]
./tools/host <command> [args...]
```

All three entrypoints do the same thing. `./dev` is the shortest general-purpose form.

### Available host commands

- `./dev replay [args...]`
- `./onroad [jobs] (--c3 | --c4 | --all | --replay-only) [--galaxy] <route-or-replay-args...>`
- `./dev galaxy [--live [port]]`
- `./dev cabana [args...]`
- `./dev plotjuggler [args...]`
- `./dev juggle [args...]`
- `./dev sync`
- `./dev shell`

`./onroad` replays a route into a desktop UI to watch live. To record one to an mp4 instead of
watching it in real time, use `tools/clip/run.py` (see [tools/clip/README.md](clip/README.md)).

`./dev galaxy` serves the Galaxy web UI in your browser, so you can check layout changes on
your desktop before pushing to a device. Add `--live` to serve your working tree with reload
enabled -- it builds the host runtime on first run, then hands off to `scripts/galaxy_live.sh`.
See [the Galaxy README](../starpilot/system/the_galaxy/README.md) for the full workflow.

### Desktop UI shorthands

- `./c3 [jobs] [args...]`
- `./c4 [jobs] [args...]`

These are wrappers around the same isolated host runner used by `./dev`.

Examples:

```bash
./dev replay
./onroad --c3 f08912a233c1584f/2022-08-11--18-02-41/1
./onroad --c4 f08912a233c1584f/2022-08-11--18-02-41/1 --start 30
./onroad --all f08912a233c1584f/2022-08-11--18-02-41/1
./dev plotjuggler --help
./dev cabana
./c3 8
./c4 8
./dev shell
```

## What gets isolated

Host-native artifacts live under:

```bash
.host_runtime/<platform>/
```

That host area contains:

- `worktree/` and `venv/` for the shared bucket used by UI, replay, and PlotJuggler
- `cabana/worktree/` and `cabana/venv/` for Cabana
- host-built binaries, static libs, objects, and Python extensions for each bucket

Because `.host_runtime/` is git-ignored, running host tools no longer churns tracked files in the main repo.

## Build and rebuild behavior

Expected behavior:

- First run builds whatever the host tool needs
- Later runs reuse the cached host artifacts
- Source changes or branch changes trigger a resync into `.host_runtime/.../worktree`
- SCons rebuilds only the host artifacts that are out of date
- Deleting `.host_runtime/` forces a clean rebuild of the host cache

In other words, the host-side shorthand commands should not fully recompile every time unless something actually changed.

## Concurrency rule

Host shorthand commands are isolated by bucket.

That means:

- `./dev cabana` and `./dev plotjuggler` can run at the same time
- `./build` is separate from all host buckets and can run at the same time as host tools
- commands that share the same bucket still wait on that bucket's lock
- long-running UI sessions hold the shared bucket lock until they exit

Current bucket split:

- shared bucket: `./c3`, `./c4`, `./dev replay`, `./dev galaxy`, `./dev plotjuggler`, `./dev juggle`, `./dev shell`
- cabana bucket: `./dev cabana`

`./dev galaxy --live` is the exception to the "long-running sessions hold the lock" rule: it
takes the shared lock only while building the host runtime, then releases it before serving.
A live Galaxy session and `./c3` can run side by side. Only one live Galaxy session runs at a
time; `sync_worktree` preserves the live symlink only while that session's pidfile is alive, so
a finished session leaves no stale link behind. The snapshot `./dev galaxy` refuses to start
while one is live, since it would otherwise serve the live working tree instead of a snapshot.

This prevents one command from syncing or rebuilding over another live host session while still allowing the common Cabana + PlotJuggler pairing.

## Choosing the right command

Use `./build` when:

- you want device-target artifacts
- you care about matching the comma runtime build path
- you are preparing binaries for deployment/runtime validation

Use `./dev ...` when:

- you want host-native tools like replay, cabana, or PlotJuggler
- you want host-native `.so` files separated from the main repo
- you do not want AI tools or git status confused by temporary build churn

Use `./onroad ...` when:

- you want a recorded route to drive the desktop UI(s) on PC
- you need replay and UI to share the same isolated host runtime and messaging prefix
- you want the default side-by-side desktop UI launch without running separate replay/UI commands

Use `./c3` or `./c4` when:

- you want the desktop UI variants
- you want them to build/run from the isolated host cache instead of touching tracked files

Use `./dev galaxy` when:

- you want to preview the Galaxy web UI in a browser on your desktop
- use `--live` for layout work, so edits under `starpilot/system/the_galaxy/` appear on refresh
- use it bare for a stable snapshot that ignores whatever you are currently editing
- use `./onroad --galaxy <route>` when the panels you are working on need replayed data

## Troubleshooting

If a shorthand command fails immediately:

- make sure `.venv` exists
- run `tools/install_python_dependencies.sh`
- confirm `uv` is installed

If device builds fail:

- run `scripts/laptop_device_build.sh doctor`
- finish the sysroot/container setup before retrying `./build`

If you want to reset the host cache:

```bash
rm -rf .host_runtime
```

Then rerun the shorthand command you need.

To refresh all buckets without deleting them:

```bash
./dev sync
```

To refresh one bucket only:

```bash
./dev sync cabana
./dev sync shared
```

## Recommended day-to-day workflow

1. Use `./build` when you need the real device-target build.
2. Use `./dev replay`, `./dev cabana`, or `./dev plotjuggler` for host-side tooling.
3. Use `./c3` or `./c4` for desktop UI work.
4. Let `.host_runtime` keep host artifacts out of the repo.
