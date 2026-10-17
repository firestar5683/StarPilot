# Vendored PulseAudio server (AArch64)

Spotify Soloist plays only through PulseAudio or PipeWire, and AGNOS ships PulseAudio's client library
without a server. This directory is the minimal server needed to carry Soloist's audio to one output:
the `pulseaudio` daemon, its private libraries, and four modules (native protocol, ALSA sink for
BlueALSA, null sink, and the real-time pipe sink used for Android Auto).

- Source: Ubuntu 24.04 (noble) arm64 binary packages, `pulseaudio 1:16.1+dfsg1-2ubuntu10.1` and the
  libraries listed in `PACKAGES.sha512` (SHA-512 of each `.deb` as published by Ubuntu).
- The comma's own `libpulse0`/`libpulsecommon-16.1.so` is byte-identical to that Ubuntu build, which is
  why only these files are needed. Regenerate with `./update.sh`; `SHA256SUMS` lists the extracted files.
- Licenses: PulseAudio and libltdl are LGPL-2.1-or-later, libtdb LGPL-3.0-or-later, libsoxr
  LGPL-2.1-or-later, liborc and speexdsp BSD-style. Full notices are in `licenses/`. Corresponding source is
  available from Ubuntu's archive (`apt-get source pulseaudio=1:16.1+dfsg1-2ubuntu10.1`, and likewise
  for each package above). The libraries are unmodified and dynamically linked.
