#!/usr/bin/env bash
# Builds the static Linux ARM64 Google Play resolver (playlink) in Docker.
set -euo pipefail
cd "$(dirname "$0")/.."
scripts/laptop_device_build.sh doctor
image=starpilot-playlink-builder:rust1.93.1
docker build --platform linux/arm64 -f tools/laptop_device_build/Dockerfile.playlink -t "$image" .
mkdir -p .cache/playlink-registry .cache/playlink-target .cache/playlink
docker run --rm --platform linux/arm64 \
  --mount "type=bind,src=$PWD,dst=/work" \
  --mount "type=bind,src=$PWD/.cache/playlink-registry,dst=/opt/playlink-cargo/registry" \
  -e CARGO_TARGET_DIR=/work/.cache/playlink-target \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0=/work \
  "$image" bash -euc '
    test "$(uname -sm)" = "Linux aarch64"
    capnp --version | grep -q "version 1.0.1$"
    cargo build --locked --release --target aarch64-unknown-linux-gnu
    binary=/work/.cache/playlink-target/aarch64-unknown-linux-gnu/release/playlink
    file "$binary"
    readelf -h "$binary" | grep -q AArch64
    if readelf -l "$binary" | grep -q INTERP; then exit 1; fi
    if readelf -d "$binary" | grep -q NEEDED; then exit 1; fi
    install -m 755 "$binary" /work/.cache/playlink/playlink-arm64
  '
printf 'Play resolver: %s/.cache/playlink/playlink-arm64\n' "$PWD"
