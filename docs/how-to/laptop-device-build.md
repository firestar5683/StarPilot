# Laptop and device builds

`./build` uses a Linux/ARM64 container and a matching AGNOS sysroot on a laptop. On an actual AGNOS/aarch64 device it runs SCons natively in that checkout, using the device Python environment and vendored source imports. It does not copy host-built model files into a device build. The container image pins Cap'n Proto 1.0.1 to the generated cereal contract in this tree.

## Prepare the build environment

Install Docker or Podman with Linux/ARM64 support. Run `scripts/laptop_device_build.sh doctor` to see which local prerequisites are missing. The first setup/build can download a container image, Python dependencies, and an AGNOS system image; run it only when you intend that network activity.

To prepare without a physical device, run:

```sh
scripts/laptop_device_build.sh setup
```

To use an explicitly supplied device sysroot instead, run `scripts/laptop_device_build.sh setup-sysroot <device-host> [user] [ssh-port]`, then `scripts/laptop_device_build.sh build-image`. The build does not connect to a device or flash firmware. The compatibility alias `scripts/starpilot_build_flow.sh laptop-setup` invokes the same explicit setup.

If the matching AGNOS ext4 system image is already local, use `scripts/laptop_device_build.sh setup-sysroot-local <system-image-path>` instead. This extracts a separate ignored `.comma_sysroot`; it does not change the image. Verify its `VERSION` against the intended device OS. A sysroot copied from a different AGNOS build does not establish ABI compatibility.

## Build

```sh
./build                 # complete device-target build
./build 8               # complete build with eight SCons jobs
./build --params        # current params shared library only
./build --cereal        # cereal libraries, bridge, and service header
./build --panda         # signed panda_h7 and body_h7 firmware targets only
./build --panda 8       # same H7 targets with eight jobs
./build --mapd          # explicit offline Mapd provider package, separate from SCons
```

`--mapd` cannot be combined with SCons targets or jobs. It builds the pinned
Linux/ARM64 static Mapd binary and manifest in ignored
`openpilot/starpilot/maps/provider/`. It does not download map regions, change
the selected offline snapshot, start Mapd, or run during plain `./build`.

The Mapd shortcut requires Go 1.25.1 and an already populated module cache.
On Linux/ARM64 it uses a local Go executable. On other hosts it uses the
`openpilot-local-mapd-builder:go1.25.1` Linux/ARM64 image, built **explicitly**
from `tools/laptop_device_build/Dockerfile.mapd`:

```sh
docker build --platform linux/arm64 -f tools/laptop_device_build/Dockerfile.mapd \
  -t openpilot-local-mapd-builder:go1.25.1 .
mkdir -p .cache/mapd-go-modules
docker run --rm --platform linux/arm64 \
  --mount "type=bind,src=$PWD/mapd_repo,dst=/work,readonly" \
  --mount "type=bind,src=$PWD/.cache/mapd-go-modules,dst=/gomodcache" \
  -e GOMODCACHE=/gomodcache -w /work \
  openpilot-local-mapd-builder:go1.25.1 go mod download
./build --mapd
```

The image build and module-cache population above are explicit network setup
steps. `./build --mapd` itself uses `--network none`, `--pull never`,
`GOPROXY=off`, and a read-only module cache. An existing offline cache can be
selected with `COMMA_MAPD_MODULE_CACHE`; an existing reviewed ARM64 Go image
can be selected with `COMMA_MAPD_BUILD_IMAGE`. The generated package is checked
for the exact source digest and ARM64/static format by `package_shadow.py`.
It is a build artifact; stage it separately with the source manifest for a
device, rather than treating the source-only checkout as containing it.

The historical wrapper's other Panda variants are not targets in the current `panda/SConscript`; `--panda` does not claim to build them. Shortcut targets use `--no-scrub` and leave `prebuilt` alone. Other SCons arguments pass through the container helper. A full-build invocation with options or explicit targets cannot mark `prebuilt`: clean, question, and dry-run commands do not compile the complete default graph. `scripts/starpilot_build_flow.sh laptop-device [jobs]` is the compatibility alias for a complete `./build`.

The complete build selects the current `comma_arm64` SCons profile in its container, including Ion-backed VisionIPC and QCOM model compilation. It checks the driving model, driver-monitoring model, camera warps, and core runtime libraries before setting `prebuilt`. QCOM model compilation may require device-class hardware even with an ARM64 container; if it cannot complete, the build fails and `prebuilt` remains unset. A local `DEV=METAL` model artifact is not a device build substitute.

`scripts/laptop_device_build.sh verify-artifacts` inspects the outputs without loading pickle files: it requires ARM64 ELF objects, exact current camera warp dimensions, and QCOM captured backends. It does not run inference. The matching sysroot is passed to Clang at both compile and link time. For a cached compatible base image, `COMMA_BASE_IMAGE=<local-image>` overrides the Dockerfile's default base only while building the image; record that override when reporting build provenance.

For a single explicit target, use `scripts/laptop_device_build.sh scons --no-scrub <target>`. Sysroot, cache, and build-venv path overrides must resolve to direct children of this checkout. Relative overrides resolve from the checkout root before Docker bind mounts. The `doctor` command checks availability only; it does not prove the image or sysroot can compile every target.

`scripts/laptop_device_build.sh manager` remains an **explicit** container runtime mode for developers with a complete build. Neither `./build` nor the checks above launch it. It can start ordinary manager processes; review that mode separately before using it with connected hardware.

The legacy alias also supports `verify`, `mac`, and `device`. `mac` checks Python compilation only and does not produce device binaries. `device` requires AGNOS on ARM64 hardware and is never part of laptop validation.
