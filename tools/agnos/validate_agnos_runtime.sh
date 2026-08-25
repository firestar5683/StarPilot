#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="${1:-}"
REPO_ROOT="${2:-/data/openpilot}"
PYTHON_BIN="/usr/local/venv/bin/python3"
SITE_PACKAGES="/usr/local/venv/lib/python3.12/site-packages"

fail() {
  echo "[FAIL] $*" >&2
  exit 1
}

[[ -x "$PYTHON_BIN" ]] || fail "managed Python is missing: $PYTHON_BIN"
[[ -d "$SITE_PACKAGES" ]] || fail "site-packages is missing: $SITE_PACKAGES"

actual_version="$(tr -d '\r\n' </VERSION)"
if [[ -n "$EXPECTED_VERSION" && "$actual_version" != "$EXPECTED_VERSION" ]]; then
  fail "AGNOS version is $actual_version, expected $EXPECTED_VERSION"
fi

site_count="$(find "$SITE_PACKAGES" -mindepth 1 -maxdepth 1 -print | wc -l | tr -d ' ')"
[[ "$site_count" == "253" ]] || fail "managed venv has $site_count site-packages entries, expected upstream 213 plus 40 additive StarPilot dependencies"

echo "[CHECK] AGNOS version: $actual_version"
echo "[CHECK] managed venv entries: $site_count"

"$PYTHON_BIN" -c 'import aiohttp, capnp, crcmod, Crypto, cv2, jsonrpc, kaitaistruct, mapbox_earcut, numpy, onnx, pyaudio, raylib, serial, tqdm, xattr; print("[CHECK] runtime imports: ok")'

[[ "$(readlink /usr/local/lib/libavformat.so.58)" == "libavformat.so.58.29.100" ]]
[[ "$(readlink /usr/local/lib/libavcodec.so.58)" == "libavcodec.so.58.54.100" ]]
[[ "$(readlink /usr/local/lib/libavutil.so.56)" == "libavutil.so.56.31.100" ]]
[[ "$(readlink /usr/local/lib/libswresample.so.3)" == "libswresample.so.3.5.100" ]]
echo "[CHECK] legacy prebuilt runtime links: ok"

"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import zipfile

with zipfile.ZipFile("/usr/comma/setup") as setup:
  for member in ("openpilot/system/ui/mici_setup.py", "openpilot/system/ui/tici_setup.py"):
    source = setup.read(member).decode("utf-8")
    assert 'OPENPILOT_URL = "file:///usr/comma/installer"' in source, member
    assert 'CONNECTIVITY_URL = "https://openpilot.comma.ai"' in source, member
    assert "StarPilot" in source, member
    assert "install_bundled_installer(*bundled_target, self.installer_url)" in source, member
    assert 'self.bundled_installer_target = (("firestar5683", "StarPilot") if url == OPENPILOT_URL else None)' in source, member

installer = Path("/usr/comma/installer").read_bytes()
assert installer.startswith(b"\x7fELF")
assert installer.count(b"https://github.com/firestar5683/openpilot.git?") == 1
assert installer.count(b"StarPilot?") == 1
print("[CHECK] factory StarPilot setup/installer: ok")
PY

if [[ -d "$REPO_ROOT" ]]; then
  (
    cd "$REPO_ROOT"
    "$PYTHON_BIN" -c 'from openpilot.system.manager import manager; print("[CHECK] manager import: ok")'
    if [[ -f openpilot/selfdrive/pandad/pandad_api_impl.so ]]; then
      "$PYTHON_BIN" -c 'import openpilot.selfdrive.pandad.pandad_api_impl; print("[CHECK] legacy prebuilt native import: ok")'
    fi
  )
else
  echo "[CHECK] manager import: deferred until software is installed"
fi

sha256sum --check --strict <<'HASHES'
779db62d2d4c5f8ce504c5d1f2994d34a9f35296d5efb7f3a48cb1e8a0d4778e  /etc/NetworkManager/NetworkManager.conf
45e653e2f709c027fad41f2d86b70e008b72c6bf4d34590b4765ebe8fe3ea948  /etc/NetworkManager/conf.d/10-globally-managed-devices.conf
fb33a80bf8c78b3af004d4b294c47a0139e37742c1d0d5a6a7663c7d1f4a2b48  /lib/systemd/system/NetworkManager.service
9df4edbeb5849de03f9c2d691d04646af84a3ef74c2f33be8e73d9281daebe99  /usr/comma/updater
97ed6413515d0674442c42ae6e20baccf66dd6bb4ec382ee4cf0cc5ebe84e739  /usr/comma/reset
c4416e66b127b31c17d08e6723ad46d12af7683e56626512d66c708b5f347ac9  /usr/comma/magic.py
8f6c84e5799c0025f645997ce8e2cbc99ab0232f4be14ee2d95f609ca90c6e02  /usr/local/lib/libcapnp-1.0.2.so
c548c10b875b8841637017503ac73b1d466a36926df59fc5382221c021738d90  /usr/local/lib/libkj-1.0.2.so
7bf17a186267d1642049929cbda3d34c4c160f727e7d819985b49f5fb07ed05b  /usr/local/lib/libavformat.so.58.29.100
252b85381ab652736dbea984ad2cab158b43f93641b043475834e3fd0bccd697  /usr/local/lib/libavcodec.so.58.54.100
3730dde66fe502d769e06e5faf001a3dc1c30091993d606989f3e077ba2e579a  /usr/local/lib/libavutil.so.56.31.100
41b0a5e7807506779f2163d23d5120949efaeeaf96fb9b69758551c9af7c7c1a  /usr/local/lib/libswresample.so.3.5.100
370d154aaf7e1e9ee433c069348ae885036a9d8cc4c8babfbfae12c8d5b3f2e8  /usr/comma/installer
934f74ab4b2ac06048418c2857be3a041e192ec03c09979987691c23c91353bd  /usr/comma/setup_keys
6565acac9eb8167931f6ad50c62254b64f037d21a7944456bd8ec328c7f4af0b  /usr/comma/setup
bcba2b336cf0ca852786f8a58bbce407e0e9fe952c26fc5d903f6d9a34b44b4f  /usr/comma/comma.sh
HASHES

[[ "$(systemctl is-enabled NetworkManager)" == "enabled" ]] || fail "NetworkManager is not enabled"
[[ "$(systemctl is-active NetworkManager)" == "active" ]] || fail "NetworkManager is not active"

echo "[PASS] AGNOS runtime, manager, recovery payloads, and networking validated"
