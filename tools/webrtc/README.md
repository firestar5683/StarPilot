# WebRTC ICE compatibility

The August 24, 2026 AGNOS update (`05140149fb`) replaced the aiortc backend
with libdatachannel. `libdatachannel-py==2026.1.0.dev2` embeds libdatachannel
v0.24.0 and libjuice revision `5948a4162d37bc213d6051b67ee2876ccc5a99a6`.

That libjuice revision uses a zero ICE tie-breaker to mean "role attribute
absent". A present `ICE-CONTROLLING` attribute containing zero is consequently
rejected with STUN `400 Bad Request`. This was captured on the device during
Connect attempts: its outgoing checks succeed, but it rejects the browser's
nominating checks. It remains at ICE Connected, never completes DTLS, and
Connect eventually reports that no direct peer-to-peer routes were found.

The patch records attribute presence separately from the 64-bit value. It does
not change credentials, integrity checks, DTLS, camera handling, Sentry, media
codecs, or data-channel behavior. It also continues to reject missing roles and
rejects requests containing both role attributes.

## Build and verify

On the target architecture, with git, uv, a C/C++ compiler and Python 3.12:

```sh
bash tools/webrtc/build_libdatachannel.sh /absolute/path/to/wheels /usr/bin/python3.12
```

This builds `2026.1.0.dev2+starpilot.ice1` in an isolated temporary environment
and runs real loopback UDP checks. Source and build directories are retained
for inspection. It does not install into the device's runtime environment.

To test an installed runtime independently:

```sh
/usr/local/venv/bin/python tools/webrtc/check_ice.py
```

The original wheel fails the zero-tie-breaker case; a corrected wheel must pass
all cases, including invalid-authentication rejection. A successful loopback
check is not proof that a Connect video session works; verify that separately.

## Deployment

The correction is in a compiled dependency, not just openpilot Python source.
A git pull alone does not replace the affected AGNOS library. Install the
validated, architecture-matching wheel into the image's managed Python
environment and run the check above when building a release image. Existing
devices need that runtime update too. Back up the original package and its
distribution metadata before a temporary device-side installation; a later
AGNOS image or dependency sync can otherwise overwrite the hotfix.

AGNOS normally mounts the OS read-only. For a reversible live test, the
corrected extension can be bind-mounted read-only over the original extension
file. This leaves the OS partition unchanged, but the test hotfix is lost on
reboot. Do not confuse that with deploying a corrected release image.

Upstream sources: [Python bindings](https://github.com/shiguredo/libdatachannel-py/tree/989d29a32968046a002b5b9deb7a00f5012c530c),
[libjuice](https://github.com/paullouisageneau/libjuice/tree/5948a4162d37bc213d6051b67ee2876ccc5a99a6).
The libjuice source modification is covered by its MPL-2.0 license.
