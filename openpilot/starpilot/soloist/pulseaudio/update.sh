#!/usr/bin/env bash
# Regenerate this directory from Ubuntu 24.04 (noble) arm64 packages. Requires Docker.
# The comma's own libpulse0/libpulsecommon must be the same PulseAudio build (check SHA256SUMS of
# /usr/lib/aarch64-linux-gnu/pulseaudio/libpulsecommon-16.1.so on a device before bumping).
set -euo pipefail
cd "$(dirname "$0")"
docker run --rm --platform linux/arm64 -v "$PWD:/out" ubuntu:24.04 bash -euc '
  apt-get -qq update >/dev/null
  DEBIAN_FRONTEND=noninteractive apt-get -qq install -y --no-install-recommends libpulse0 libasound2t64 libsndfile1 libwrap0 \
    libx11-xcb1 libgomp1 libasyncns0 libsystemd0 libudev1 libdbus-1-3 >/dev/null
  cd /tmp && apt-get download pulseaudio libltdl7 liborc-0.4-0t64 libsoxr0 libspeexdsp1 libtdb1 >/dev/null
  sha512sum *.deb > /out/PACKAGES.sha512
  for deb in *.deb; do dpkg-deb -x "$deb" root; done
  R=/tmp/root; M=$R/usr/lib/pulse-16.1+dfsg1/modules
  rm -rf /out/bin /out/lib /out/modules /out/licenses && mkdir -p /out/bin /out/lib /out/modules /out/licenses
  cp $R/usr/bin/pulseaudio /out/bin/
  for m in module-native-protocol-unix module-alsa-sink module-null-sink module-pipe-sink; do cp $M/$m.so /out/modules/; done
  export LD_LIBRARY_PATH=$R/usr/lib/aarch64-linux-gnu:$R/usr/lib/aarch64-linux-gnu/pulseaudio:$M
  for f in /out/bin/pulseaudio /out/modules/*.so; do ldd "$f"; done | awk "/=>/{print \$3}" | sort -u | grep "^$R" |
    while read -r lib; do cp -L "$lib" /out/lib/; done
  for p in pulseaudio libltdl7 liborc-0.4-0t64 libsoxr0 libspeexdsp1 libtdb1; do cp $R/usr/share/doc/$p/copyright /out/licenses/$p.copyright; done
  chmod 755 /out/bin/pulseaudio && chmod 644 /out/lib/* /out/modules/* /out/licenses/*
  cd /out && sha256sum bin/* lib/* modules/* > SHA256SUMS'
