#!/usr/bin/env python3
"""Build StarPilot AGNOS from the exact upstream system image.

The output starts with comma's pinned AGNOS system partition, adds the Python
packages required by StarPilot's older runtime and C3 support, and customizes
only the stock setup/installer pair needed for StarPilot's factory install.
Reset, updater, Magic, NetworkManager, and every existing upstream Python
package remain byte-identical to the pinned image.
"""

import argparse
import hashlib
import json
import lzma
import os
import re
import shutil
import struct
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path


VERSION_PATH_IN_IMAGE = "/VERSION"
SITE_PACKAGES_PATH_IN_IMAGE = "/usr/local/venv/lib/python3.12/site-packages"
LEGACY_RUNTIME_LIBRARY_DIR = "/usr/local/lib"
SETUP_PATH_IN_IMAGE = "/usr/comma/setup"
INSTALLER_PATH_IN_IMAGE = "/usr/comma/installer"
STAR_PILOT_GIT_URL = "https://github.com/firestar5683/openpilot.git"
STAR_PILOT_BRANCH = "StarPilot"
STAR_PILOT_DEPENDENCY_NAMES = (
  # C3/runtime compatibility
  "crcmod", "crcmod-1.7.dist-info", "serial", "pyserial-3.5.dist-info",
  "kaitaistruct.py", "kaitaistruct-0.11.dist-info",
  # StarPilot always-on/default features
  "cv2", "opencv_python_headless-4.11.0.86.dist-info", "opencv_python_headless.libs",
  "mapbox_earcut.cpython-312-aarch64-linux-gnu.so", "mapbox_earcut-1.0.3.dist-info",
  "jsonrpc", "json_rpc-1.15.0.dist-info", "xattr", "xattr-1.2.0.dist-info",
  "onnx", "onnx-1.18.0.dist-info", "google", "protobuf-7.35.1.dist-info",
  "typing_extensions.py", "typing_extensions-4.16.0.dist-info",
  # Existing body/web tools still use aiohttp and PyAudio. The aiortc stack is
  # deliberately not copied; WebRTC uses upstream's libdatachannel backend.
  "aiohappyeyeballs", "aiohappyeyeballs-2.7.1.dist-info",
  "aiohttp", "aiohttp-3.12.15.dist-info",
  "aiosignal", "aiosignal-1.4.0.dist-info",
  "attr", "attrs", "attrs-26.1.0.dist-info",
  "frozenlist", "frozenlist-1.8.0.dist-info",
  "multidict", "multidict-6.7.1.dist-info",
  "propcache", "propcache-0.5.2.dist-info",
  "yarl", "yarl-1.24.5.dist-info",
  "pyaudio", "pyaudio-0.2.14.dist-info",
)
STAR_PILOT_DEPENDENCY_PATHS = tuple(
  f"{SITE_PACKAGES_PATH_IN_IMAGE}/{name}" for name in STAR_PILOT_DEPENDENCY_NAMES
)
C3_DEPENDENCY_PATHS = tuple(
  f"{SITE_PACKAGES_PATH_IN_IMAGE}/{name}"
  for name in ("crcmod", "crcmod-1.7.dist-info", "serial", "pyserial-3.5.dist-info", "kaitaistruct.py", "kaitaistruct-0.11.dist-info")
)
LEGACY_RUNTIME_LIBRARY_NAMES = (
  # Existing StarPilot prebuilts use these legacy SONAMEs. Keep only their
  # runtime closure; current source builds use upstream's managed packages.
  "libcapnp-1.0.2.so", "libkj-1.0.2.so",
  "libavformat.so.58", "libavformat.so.58.29.100",
  "libavcodec.so.58", "libavcodec.so.58.54.100",
  "libavutil.so.56", "libavutil.so.56.31.100",
  "libswresample.so.3", "libswresample.so.3.5.100",
)
LEGACY_RUNTIME_LIBRARY_PATHS = tuple(
  f"{LEGACY_RUNTIME_LIBRARY_DIR}/{name}" for name in LEGACY_RUNTIME_LIBRARY_NAMES
)
FACTORY_INSTALL_PATHS = frozenset({SETUP_PATH_IN_IMAGE, INSTALLER_PATH_IN_IMAGE})
ALLOWED_IMAGE_MUTATIONS = frozenset({
  VERSION_PATH_IN_IMAGE,
  *STAR_PILOT_DEPENDENCY_PATHS,
  *LEGACY_RUNTIME_LIBRARY_PATHS,
  *FACTORY_INSTALL_PATHS,
})

# Exact system partition pinned by ~/openpilot as of the 19.6 AGNOS release.
UPSTREAM_VERSION = "19.6"
UPSTREAM_SYSTEM_URL = (
  "https://commadist.azureedge.net/agnosupdate/"
  "system-5b6ce7965904a157fd3a134ccfcb854f9ca5c1cc2a26b7cb80a4fa4e1cc4aaa3.img.xz"
)
UPSTREAM_RAW_SHA256 = "5b6ce7965904a157fd3a134ccfcb854f9ca5c1cc2a26b7cb80a4fa4e1cc4aaa3"
UPSTREAM_RAW_SIZE = 4_718_592_000
UPSTREAM_SITE_PACKAGES_COUNT = 213

# Compatibility packages are copied from StarPilot's exact, previously
# deployed and field-tested 19.6.2 image. Existing upstream paths are never
# overwritten.
C3_DEPENDENCY_SOURCE_URL = (
  "https://www.dropbox.com/scl/fi/pewhzpqzi3aewuiaffc6m/system10.img.xz"
  "?rlkey=olzrzulhs93zzghnjrskmdwxt&st=exnfk2oz&dl=1"
)
C3_DEPENDENCY_SOURCE_RAW_SHA256 = "ab395d4c963a908ab86709f1a6580a62dd24cb34ee71cf5fd5ec29d7d48d0e10"
C3_DEPENDENCY_SOURCE_RAW_SIZE = 4_718_592_000
CANDIDATE_SITE_PACKAGES_COUNT = UPSTREAM_SITE_PACKAGES_COUNT + len(STAR_PILOT_DEPENDENCY_PATHS)

# Hashes from that exact upstream image. Equality keeps all recovery plumbing
# stock except the explicitly customized setup/installer pair.
PROTECTED_PAYLOAD_HASHES = {
  "/etc/NetworkManager/NetworkManager.conf": "779db62d2d4c5f8ce504c5d1f2994d34a9f35296d5efb7f3a48cb1e8a0d4778e",
  "/etc/NetworkManager/conf.d/10-globally-managed-devices.conf": "45e653e2f709c027fad41f2d86b70e008b72c6bf4d34590b4765ebe8fe3ea948",
  "/lib/systemd/system/NetworkManager.service": "fb33a80bf8c78b3af004d4b294c47a0139e37742c1d0d5a6a7663c7d1f4a2b48",
  "/usr/comma/updater": "9df4edbeb5849de03f9c2d691d04646af84a3ef74c2f33be8e73d9281daebe99",
  "/usr/comma/reset": "97ed6413515d0674442c42ae6e20baccf66dd6bb4ec382ee4cf0cc5ebe84e739",
  "/usr/comma/magic.py": "c4416e66b127b31c17d08e6723ad46d12af7683e56626512d66c708b5f347ac9",
  "/usr/comma/setup_keys": "934f74ab4b2ac06048418c2857be3a041e192ec03c09979987691c23c91353bd",
  "/usr/comma/comma.sh": "bcba2b336cf0ca852786f8a58bbce407e0e9fe952c26fc5d903f6d9a34b44b4f",
}
UPSTREAM_FACTORY_INSTALL_HASHES = {
  INSTALLER_PATH_IN_IMAGE: "85f6d9e54286a3842920d6967b187478b4e43d6171c331d72d3fb3102106e101",
  SETUP_PATH_IN_IMAGE: "c382ce266653bad781c25e403ddea4af508aa6f3ea2eef3f568d964982fad9d6",
}
UPSTREAM_PAYLOAD_HASHES = {**PROTECTED_PAYLOAD_HASHES, **UPSTREAM_FACTORY_INSTALL_HASHES}

SETUP_SOURCE_MEMBERS = (
  "openpilot/system/ui/mici_setup.py",
  "openpilot/system/ui/tici_setup.py",
)

UPSTREAM_REQUIRED_VENV_PATHS = {
  "capnp": f"{SITE_PACKAGES_PATH_IN_IMAGE}/capnp",
  "numpy": f"{SITE_PACKAGES_PATH_IN_IMAGE}/numpy",
  "Crypto": f"{SITE_PACKAGES_PATH_IN_IMAGE}/Crypto",
  "tqdm": f"{SITE_PACKAGES_PATH_IN_IMAGE}/tqdm",
  "raylib": f"{SITE_PACKAGES_PATH_IN_IMAGE}/raylib",
}
REQUIRED_VENV_PATHS = {
  **UPSTREAM_REQUIRED_VENV_PATHS,
  "crcmod": f"{SITE_PACKAGES_PATH_IN_IMAGE}/crcmod",
  "serial": f"{SITE_PACKAGES_PATH_IN_IMAGE}/serial",
  "kaitaistruct": f"{SITE_PACKAGES_PATH_IN_IMAGE}/kaitaistruct.py",
  "cv2": f"{SITE_PACKAGES_PATH_IN_IMAGE}/cv2",
  "mapbox_earcut": f"{SITE_PACKAGES_PATH_IN_IMAGE}/mapbox_earcut.cpython-312-aarch64-linux-gnu.so",
  "jsonrpc": f"{SITE_PACKAGES_PATH_IN_IMAGE}/jsonrpc",
  "xattr": f"{SITE_PACKAGES_PATH_IN_IMAGE}/xattr",
  "onnx": f"{SITE_PACKAGES_PATH_IN_IMAGE}/onnx",
  "aiohttp": f"{SITE_PACKAGES_PATH_IN_IMAGE}/aiohttp",
  "pyaudio": f"{SITE_PACKAGES_PATH_IN_IMAGE}/pyaudio",
}

ANDROID_SPARSE_MAGIC = 0xED26FF3A
CHUNK_TYPE_RAW = 0xCAC1
CHUNK_TYPE_FILL = 0xCAC2
CHUNK_TYPE_DONT_CARE = 0xCAC3
CHUNK_TYPE_CRC32 = 0xCAC4
XZ_MAGIC = b"\xFD7zXZ\x00"


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Build an upstream-based StarPilot AGNOS system image")
  parser.add_argument("--manifest", default="system/hardware/tici/agnos.json",
                      help="Manifest to copy when writing an optional candidate manifest")
  parser.add_argument("--source-url", default=UPSTREAM_SYSTEM_URL, help="Exact upstream system image URL")
  parser.add_argument("--source-image", help="Use a local exact upstream raw, sparse, or .xz image")
  parser.add_argument("--c3-deps-url", default=C3_DEPENDENCY_SOURCE_URL,
                      help="Exact prior StarPilot image containing the compatibility packages")
  parser.add_argument("--c3-deps-image", help="Use a local exact StarPilot dependency source image")
  parser.add_argument("--set-version", required=True, help="StarPilot revision, for example 19.6.5")
  parser.add_argument("--work-dir", default=".cache/agnos_upstream_system")
  parser.add_argument("--output-xz", help="Output .img.xz path")
  parser.add_argument("--new-url", help="Hosted output URL for an optional candidate manifest")
  parser.add_argument("--manifest-out", help="Candidate manifest output path; never overwrites the checked-in manifest")
  parser.add_argument("--force-download", action="store_true")
  return parser.parse_args()


def find_tool(name: str, extra_candidates: tuple[str, ...] = ()) -> str:
  for candidate in (os.environ.get(name.upper()), name, *extra_candidates):
    if candidate and (shutil.which(candidate) or Path(candidate).is_file()):
      return candidate
  raise RuntimeError(f"{name} not found")


def find_debugfs() -> str:
  return find_tool("debugfs", ("/opt/homebrew/opt/e2fsprogs/sbin/debugfs",))


def find_e2fsck() -> str:
  return find_tool("e2fsck", ("/opt/homebrew/opt/e2fsprogs/sbin/e2fsck",))


def run_cmd(command: list[str], *, allowed_returncodes: frozenset[int] = frozenset({0})) -> subprocess.CompletedProcess[str]:
  result = subprocess.run(command, check=False, capture_output=True, text=True)
  if result.returncode not in allowed_returncodes:
    raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}\n{result.stderr}")
  return result


def sha256_file(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as stream:
    while chunk := stream.read(8 * 1024 * 1024):
      digest.update(chunk)
  return digest.hexdigest()


def replace_exactly(text: str, old: str, new: str, expected_count: int = 1) -> str:
  count = text.count(old)
  if count != expected_count:
    raise RuntimeError(f"Expected {expected_count} occurrences of {old!r}, found {count}")
  return text.replace(old, new)


def patch_setup_source(member: str, source: str) -> str:
  bundled_installer_helper = r'''

def patch_bundled_installer(path: str, owner: str, branch: str) -> None:
  data = bytearray(open(path, "rb").read())

  def patch_slot(old_value: bytes, new_value: bytes) -> None:
    old_marker = old_value + b"?"
    start = data.find(old_marker)
    if start < 0 or data.find(old_marker, start + 1) >= 0:
      raise RuntimeError(f"Expected exactly one installer slot for {old_value!r}")
    end = data.find(b"\0", start)
    if end < 0:
      raise RuntimeError(f"Installer slot for {old_value!r} is not NUL terminated")
    new_marker = new_value + b"?"
    if len(new_marker) > end - start:
      raise RuntimeError(f"Installer value {new_value!r} exceeds its slot")
    data[start:end] = new_marker + b" " * (end - start - len(new_marker))

  patch_slot(b"https://github.com/firestar5683/openpilot.git", f"https://github.com/{owner}/openpilot.git".encode("ascii"))
  patch_slot(b"StarPilot", branch.encode("ascii"))
  with open(path, "wb") as installer:
    installer.write(data)


def install_bundled_installer(owner: str, branch: str, installer_url: str) -> None:
  import tempfile

  fd, tmpfile = tempfile.mkstemp(prefix="installer_")
  try:
    with os.fdopen(fd, "wb") as destination, open("/usr/comma/installer", "rb") as source:
      destination.write(source.read())
    patch_bundled_installer(tmpfile, owner, branch)
    os.chmod(tmpfile, 0o755)
    with open(INSTALLER_URL_PATH, "w") as installer_url_file:
      installer_url_file.write(installer_url)
    os.replace(tmpfile, INSTALLER_DESTINATION_PATH)
  except Exception:
    try:
      os.close(fd)
    except OSError:
      pass
    try:
      os.unlink(tmpfile)
    except FileNotFoundError:
      pass
    raise
'''
  source = replace_exactly(
    source,
    'OPENPILOT_URL = "https://openpilot.comma.ai"',
    'CONNECTIVITY_URL = "https://openpilot.comma.ai"\nOPENPILOT_URL = "file:///usr/comma/installer"' + bundled_installer_helper,
  )

  source = replace_exactly(
    source,
    '''    # autocomplete incomplete URLs
    if re.match("^([^/.]+)/([^/]+)$", url):
      url = f"https://installer.comma.ai/{url}"

    parsed = urlparse(url, scheme='https')
    self.download_url = (urlparse(f"https://{url}") if not parsed.netloc else parsed).geturl()''',
    '''    # owner/branch installs use the bundled COMMA/GBM installer. The
    # installer.comma.ai binary targets Wayland and cannot run in this AGNOS.
    self.installer_url = ("https://installer.comma.ai/firestar5683/StarPilot" if url == OPENPILOT_URL else url)
    self.bundled_installer_target = (("firestar5683", "StarPilot") if url == OPENPILOT_URL else None)
    match = re.fullmatch(r"(?:https://installer\\.comma\\.ai/)?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", url)
    if match:
      self.bundled_installer_target = match.groups()
      self.installer_url = f"https://installer.comma.ai/{'/'.join(self.bundled_installer_target)}"
      url = OPENPILOT_URL

    parsed = urlparse(url, scheme='https')
    self.download_url = (urlparse(f"https://{url}") if not parsed.netloc else parsed).geturl()''',
  )

  source = replace_exactly(
    source,
    '''    try:
      import tempfile
''',
    '''    try:
      bundled_target = self.bundled_installer_target
      if bundled_target is not None:
        install_bundled_installer(*bundled_target, self.installer_url)
        time.sleep(0.1)
        gui_app.request_close()
        return

      import tempfile
''',
  )

  source = replace_exactly(
    source,
    '''      req = urllib.request.Request(self.download_url, headers=headers)

      with open(tmpfile, 'wb') as f, urllib.request.urlopen(req, timeout=30) as response:
        total_size = int(response.headers.get('content-length', 0))''',
    '''      response = (open("/usr/comma/installer", "rb") if self.download_url == OPENPILOT_URL else
                  urllib.request.urlopen(urllib.request.Request(self.download_url, headers=headers), timeout=30))

      with open(tmpfile, 'wb') as f, response:
        total_size = (os.path.getsize("/usr/comma/installer") if self.download_url == OPENPILOT_URL else
                      int(response.headers.get('content-length', 0)))''',
  )

  source = replace_exactly(
    source,
    '''      if not is_elf:
''',
    '''      if is_elf and self.bundled_installer_target is not None:
        patch_bundled_installer(tmpfile, *self.bundled_installer_target)

      if not is_elf:
''',
  )

  source = replace_exactly(source, "f.write(self.download_url)", "f.write(self.installer_url)")

  if member.endswith("mici_setup.py"):
    source = replace_exactly(source, "urllib.request.Request(OPENPILOT_URL, method=\"HEAD\")",
                             "urllib.request.Request(CONNECTIVITY_URL, method=\"HEAD\")")
    source = replace_exactly(source, 'LargerSlider("slide to install\\nopenpilot", use_openpilot_callback)',
                             'LargerSlider("slide to install\\nStarPilot", use_openpilot_callback)')
    source = replace_exactly(source, 'BigPillButton("install openpilot", green=True)',
                             'BigPillButton("install StarPilot", green=True)')
    source = replace_exactly(source, 'set_text("install openpilot" if not custom_software else "choose software")',
                             'set_text("install StarPilot" if not custom_software else "choose software")')
    source = replace_exactly(source, '"No custom software found at this URL: " + self.download_url.replace',
                             '"No custom software found at this URL: " + self.installer_url.replace')
    source = replace_exactly(
      source,
      '''    except Exception:
      self._download_failed_reason = "Invalid URL: " + self.download_url.replace("https://", "", 1)''',
      '''    except Exception:
      import traceback
      traceback.print_exc()
      self._download_failed_reason = "Invalid URL: " + self.installer_url.replace("https://", "", 1)''',
    )
  elif member.endswith("tici_setup.py"):
    source = replace_exactly(source, "urllib.request.urlopen(OPENPILOT_URL, timeout=2.0)",
                             "urllib.request.urlopen(CONNECTIVITY_URL, timeout=2.0)")
    source = replace_exactly(source, 'ButtonRadio("openpilot", self.checkmark',
                             'ButtonRadio("StarPilot", self.checkmark')
    source = replace_exactly(source, "self.download_failed(self.download_url,", "self.download_failed(self.installer_url,", expected_count=3)
    source = replace_exactly(
      source,
      '''    except Exception:
      error_msg = "Ensure the entered URL is valid, and the device's internet connection is good."''',
      '''    except Exception:
      import traceback
      traceback.print_exc()
      error_msg = "Ensure the entered URL is valid, and the device's internet connection is good."''',
    )
  else:
    raise RuntimeError(f"Unexpected setup source member: {member}")
  return source


def is_setup_cache_member(member: str) -> bool:
  return any(
    member.startswith(str(Path(source_member).parent / "__pycache__" / Path(source_member).stem)) and member.endswith(".pyc")
    for source_member in SETUP_SOURCE_MEMBERS
  )


def patch_setup_zipapp(source: Path, destination: Path) -> None:
  raw = source.read_bytes()
  zip_offset = raw.find(b"PK\x03\x04")
  if zip_offset < 0:
    raise RuntimeError("Setup payload is not an executable zip application")
  prefix = raw[:zip_offset]

  destination.parent.mkdir(parents=True, exist_ok=True)
  destination.write_bytes(prefix)
  with zipfile.ZipFile(source, "r") as input_zip, zipfile.ZipFile(destination, "a") as output_zip:
    names = set(input_zip.namelist())
    missing = set(SETUP_SOURCE_MEMBERS) - names
    if missing:
      raise RuntimeError(f"Setup payload is missing source members: {sorted(missing)}")
    for info in input_zip.infolist():
      if is_setup_cache_member(info.filename):
        continue
      data = input_zip.read(info.filename)
      if info.filename in SETUP_SOURCE_MEMBERS:
        data = patch_setup_source(info.filename, data.decode("utf-8")).encode("utf-8")
      output_zip.writestr(info, data)

  destination.chmod(source.stat().st_mode & 0o7777)
  with zipfile.ZipFile(destination, "r") as patched_zip:
    if patched_zip.testzip() is not None:
      raise RuntimeError("Patched setup zip application failed CRC validation")
    for member in SETUP_SOURCE_MEMBERS:
      patched = patched_zip.read(member).decode("utf-8")
      if 'OPENPILOT_URL = "file:///usr/comma/installer"' not in patched:
        raise RuntimeError(f"Patched setup member does not use the bundled installer: {member}")


def patch_padded_binary_slot(data: bytearray, old_value: bytes, new_value: bytes) -> None:
  old_marker = old_value + b"?"
  start = data.find(old_marker)
  if start < 0 or data.find(old_marker, start + 1) >= 0:
    raise RuntimeError(f"Expected exactly one installer slot for {old_value!r}")
  end = data.find(0, start)
  if end < 0:
    raise RuntimeError(f"Installer slot for {old_value!r} is not NUL terminated")
  slot_length = end - start
  new_marker = new_value + b"?"
  if len(new_marker) > slot_length:
    raise RuntimeError(f"Installer value {new_value!r} exceeds its {slot_length}-byte slot")
  data[start:end] = new_marker + b" " * (slot_length - len(new_marker))


def patch_installer_binary(source: Path, destination: Path) -> None:
  data = bytearray(source.read_bytes())
  if not data.startswith(b"\x7fELF"):
    raise RuntimeError("Bundled installer is not an ELF executable")
  original_size = len(data)
  patch_padded_binary_slot(data, b"https://github.com/commaai/openpilot.git", STAR_PILOT_GIT_URL.encode())
  patch_padded_binary_slot(data, b"release3", STAR_PILOT_BRANCH.encode())
  if len(data) != original_size:
    raise RuntimeError("Installer patch changed the executable size")
  destination.parent.mkdir(parents=True, exist_ok=True)
  destination.write_bytes(data)
  destination.chmod(source.stat().st_mode & 0o7777)


def validate_factory_install_payloads(setup: Path, installer: Path) -> None:
  with zipfile.ZipFile(setup, "r") as setup_zip:
    for member in SETUP_SOURCE_MEMBERS:
      source = setup_zip.read(member).decode("utf-8")
      if "StarPilot" not in source or 'OPENPILOT_URL = "file:///usr/comma/installer"' not in source:
        raise RuntimeError(f"StarPilot setup customization is missing from {member}")
      if "CONNECTIVITY_URL = \"https://openpilot.comma.ai\"" not in source:
        raise RuntimeError(f"Connectivity check changed unexpectedly in {member}")
      for expected in (
        "patch_bundled_installer(tmpfile, *self.bundled_installer_target)",
        "install_bundled_installer(*bundled_target, self.installer_url)",
        'self.bundled_installer_target = (("firestar5683", "StarPilot") if url == OPENPILOT_URL else None)',
        "self.bundled_installer_target = match.groups()",
        "f.write(self.installer_url)",
      ):
        if expected not in source:
          raise RuntimeError(f"Bundled custom-branch installer flow is missing from {member}: {expected}")

  installer_data = installer.read_bytes()
  for expected in (STAR_PILOT_GIT_URL.encode() + b"?", STAR_PILOT_BRANCH.encode() + b"?"):
    if installer_data.count(expected) != 1:
      raise RuntimeError(f"Bundled installer is missing {expected!r}")


def validate_target_version(version: str) -> str:
  clean = version.strip()
  if not re.fullmatch(r"19\.6\.\d+", clean):
    raise RuntimeError("Target version must be a 19.6.x StarPilot revision")
  if int(clean.rsplit(".", 1)[1]) < 1:
    raise RuntimeError("Target version must be newer than upstream 19.6")
  return clean


def download(url: str, destination: Path) -> None:
  destination.parent.mkdir(parents=True, exist_ok=True)
  partial = destination.with_suffix(destination.suffix + ".part")
  print(f"Downloading exact upstream AGNOS: {url}", flush=True)
  with urllib.request.urlopen(url) as source, partial.open("wb") as output:
    shutil.copyfileobj(source, output, length=8 * 1024 * 1024)
  partial.replace(destination)


def is_xz_file(path: Path) -> bool:
  with path.open("rb") as stream:
    return stream.read(len(XZ_MAGIC)) == XZ_MAGIC


def decompress_xz(source: Path, destination: Path) -> None:
  partial = destination.with_suffix(destination.suffix + ".part")
  print(f"Decompressing {source}", flush=True)
  with lzma.open(source, "rb") as compressed, partial.open("wb") as output:
    shutil.copyfileobj(compressed, output, length=8 * 1024 * 1024)
  partial.replace(destination)


def is_android_sparse(path: Path) -> bool:
  with path.open("rb") as stream:
    raw = stream.read(4)
  return len(raw) == 4 and struct.unpack("<I", raw)[0] == ANDROID_SPARSE_MAGIC


def unsparse_image(source: Path, destination: Path) -> None:
  print(f"Expanding Android sparse image {source}", flush=True)
  with source.open("rb") as source_file, destination.open("wb") as output:
    header = source_file.read(28)
    if len(header) != 28:
      raise RuntimeError("Sparse image header is truncated")
    magic, major, _minor, file_header_size, chunk_header_size, block_size, total_blocks, total_chunks, _checksum = struct.unpack(
      "<I4H4I", header,
    )
    if magic != ANDROID_SPARSE_MAGIC or major != 1:
      raise RuntimeError("Unsupported Android sparse image")
    source_file.seek(file_header_size)
    for _ in range(total_chunks):
      chunk_header = source_file.read(chunk_header_size)
      if len(chunk_header) != chunk_header_size:
        raise RuntimeError("Sparse chunk header is truncated")
      chunk_type, _reserved, chunk_blocks, total_size = struct.unpack("<2H2I", chunk_header[:12])
      payload_size = total_size - chunk_header_size
      output_size = chunk_blocks * block_size
      if chunk_type == CHUNK_TYPE_RAW:
        if payload_size != output_size:
          raise RuntimeError("Sparse RAW chunk size mismatch")
        remaining = payload_size
        while remaining:
          data = source_file.read(min(8 * 1024 * 1024, remaining))
          if not data:
            raise RuntimeError("Sparse RAW chunk is truncated")
          output.write(data)
          remaining -= len(data)
      elif chunk_type == CHUNK_TYPE_FILL:
        if payload_size != 4:
          raise RuntimeError("Sparse FILL chunk has invalid size")
        pattern = source_file.read(4)
        if pattern == b"\0\0\0\0":
          output.seek(output_size, os.SEEK_CUR)
        else:
          block = pattern * (block_size // 4)
          for _ in range(chunk_blocks):
            output.write(block)
      elif chunk_type == CHUNK_TYPE_DONT_CARE:
        source_file.seek(payload_size, os.SEEK_CUR)
        output.seek(output_size, os.SEEK_CUR)
      elif chunk_type == CHUNK_TYPE_CRC32:
        source_file.seek(payload_size, os.SEEK_CUR)
      else:
        raise RuntimeError(f"Unknown sparse chunk type: 0x{chunk_type:04x}")
    output.truncate(total_blocks * block_size)


def materialize_upstream_image(source: Path, destination: Path, work_dir: Path) -> None:
  candidate = source
  if is_xz_file(source):
    decompressed = work_dir / "upstream_system.decompressed.img"
    if not decompressed.exists():
      decompress_xz(source, decompressed)
    candidate = decompressed
  if destination.exists():
    return
  if is_android_sparse(candidate):
    unsparse_image(candidate, destination)
  else:
    shutil.copy2(candidate, destination)


def run_debugfs(debugfs: str, image: Path, request: str, *, write: bool = False) -> str:
  command = [debugfs]
  if write:
    command.append("-w")
  command += ["-R", request, str(image)]
  result = run_cmd(command)
  return f"{result.stdout}\n{result.stderr}"


def parse_inode(output: str) -> int:
  match = re.search(r"Inode:\s+(\d+)", output)
  if not match:
    raise RuntimeError(f"Unable to parse inode:\n{output}")
  return int(match.group(1))


def write_version(debugfs: str, image: Path, local_file: Path) -> None:
  expected_mutations = frozenset({
    VERSION_PATH_IN_IMAGE,
    *STAR_PILOT_DEPENDENCY_PATHS,
    *LEGACY_RUNTIME_LIBRARY_PATHS,
    *FACTORY_INSTALL_PATHS,
  })
  if ALLOWED_IMAGE_MUTATIONS != expected_mutations:
    raise RuntimeError("AGNOS mutation allowlist contains an unexpected path")
  run_debugfs(debugfs, image, f"rm {VERSION_PATH_IN_IMAGE}", write=True)
  run_debugfs(debugfs, image, f"write {local_file} {VERSION_PATH_IN_IMAGE}", write=True)
  inode = parse_inode(run_debugfs(debugfs, image, f"stat {VERSION_PATH_IN_IMAGE}"))
  for field, value in (("mode", "0100644"), ("uid", "0"), ("gid", "0")):
    run_debugfs(debugfs, image, f"set_inode_field <{inode}> {field} {value}", write=True)


def read_image_text(debugfs: str, image: Path, image_path: str) -> str:
  output = run_debugfs(debugfs, image, f"cat {image_path}")
  lines = [line.strip() for line in output.splitlines() if line.strip() and not line.startswith("debugfs ")]
  return lines[0] if lines else ""


def image_path_exists(debugfs: str, image: Path, image_path: str) -> bool:
  output = run_debugfs(debugfs, image, f"stat {image_path}")
  return re.search(r"Inode:\s+\d+", output) is not None


def list_image_directory(debugfs: str, image: Path, image_path: str) -> set[str]:
  output = run_debugfs(debugfs, image, f"ls -p {image_path}")
  entries: set[str] = set()
  for line in output.splitlines():
    if line.startswith("/"):
      fields = line.split("/")
      if len(fields) >= 6 and fields[5] not in ("", ".", ".."):
        entries.add(fields[5])
  return entries


def validate_venv_layout(debugfs: str, image: Path, *, expected_count: int,
                         required_paths: dict[str, str]) -> dict[str, object]:
  entries = list_image_directory(debugfs, image, SITE_PACKAGES_PATH_IN_IMAGE)
  if len(entries) != expected_count:
    raise RuntimeError(f"Managed venv has {len(entries)} entries; expected {expected_count}")
  missing = [name for name, path in required_paths.items() if not image_path_exists(debugfs, image, path)]
  if missing:
    raise RuntimeError(f"Managed venv is missing required imports: {', '.join(missing)}")
  return {"site_packages_count": len(entries), "required_imports": sorted(required_paths)}


def image_path_is_directory(debugfs: str, image: Path, image_path: str) -> bool:
  output = run_debugfs(debugfs, image, f"stat {image_path}")
  if not re.search(r"Inode:\s+\d+", output):
    raise RuntimeError(f"Image path does not exist: {image_path}")
  return "Type: directory" in output


def extract_starpilot_dependencies(debugfs: str, dependency_image: Path, destination: Path) -> None:
  destination.mkdir(parents=True, exist_ok=True)
  for image_path in STAR_PILOT_DEPENDENCY_PATHS:
    if not image_path_exists(debugfs, dependency_image, image_path):
      raise RuntimeError(f"StarPilot dependency source is missing {image_path}")
    if image_path_is_directory(debugfs, dependency_image, image_path):
      run_debugfs(debugfs, dependency_image, f"rdump {image_path} {destination}")
    else:
      run_debugfs(debugfs, dependency_image, f"dump -p {image_path} {destination / Path(image_path).name}")
  extracted = {path.name for path in destination.iterdir()}
  expected = set(STAR_PILOT_DEPENDENCY_NAMES)
  if extracted != expected:
    raise RuntimeError(f"Unexpected StarPilot dependency extraction: {sorted(extracted)}")


def extract_legacy_runtime_libraries(debugfs: str, dependency_image: Path, destination: Path) -> None:
  destination.mkdir(parents=True, exist_ok=True)
  for name, image_path in zip(LEGACY_RUNTIME_LIBRARY_NAMES, LEGACY_RUNTIME_LIBRARY_PATHS, strict=True):
    stat = run_debugfs(debugfs, dependency_image, f"stat {image_path}")
    if not re.search(r"Inode:\s+\d+", stat):
      raise RuntimeError(f"Legacy runtime source is missing {image_path}")
    local_path = destination / name
    if "Type: symlink" in stat:
      match = re.search(r'Fast link dest: "([^"]+)"', stat)
      if match is None:
        raise RuntimeError(f"Unable to resolve legacy runtime symlink {image_path}")
      local_path.symlink_to(match.group(1))
    else:
      run_debugfs(debugfs, dependency_image, f"dump -p {image_path} {local_path}")

  extracted = {path.name for path in destination.iterdir()}
  if extracted != set(LEGACY_RUNTIME_LIBRARY_NAMES):
    raise RuntimeError(f"Unexpected legacy runtime library extraction: {sorted(extracted)}")
  for path in destination.iterdir():
    if path.is_symlink() and not path.resolve().is_file():
      raise RuntimeError(f"Legacy runtime symlink target is missing: {path}")


def ensure_image_directory(debugfs: str, image: Path, image_path: str) -> None:
  if image_path_exists(debugfs, image, image_path):
    return
  parent = str(Path(image_path).parent)
  if parent not in ("", ".", "/"):
    ensure_image_directory(debugfs, image, parent)
  run_debugfs(debugfs, image, f"mkdir {image_path}", write=True)
  if not image_path_exists(debugfs, image, image_path):
    raise RuntimeError(f"Failed to create image directory {image_path}")
  inode = parse_inode(run_debugfs(debugfs, image, f"stat {image_path}"))
  for field, value in (("mode", "040755"), ("uid", "0"), ("gid", "0")):
    run_debugfs(debugfs, image, f"set_inode_field <{inode}> {field} {value}", write=True)


def add_tree_to_image(debugfs: str, image: Path, source: Path, destination: str) -> None:
  if image_path_exists(debugfs, image, destination):
    raise RuntimeError(f"Refusing to overwrite upstream image path {destination}")
  commands: list[str] = []
  created_directories: set[str] = set()

  def create_directory(image_path: str) -> None:
    if image_path in created_directories or image_path == SITE_PACKAGES_PATH_IN_IMAGE:
      return
    parent = str(Path(image_path).parent)
    if parent not in ("", ".", "/"):
      create_directory(parent)
    commands.extend((
      f"mkdir {image_path}",
      f"set_inode_field {image_path} mode 040755",
      f"set_inode_field {image_path} uid 0",
      f"set_inode_field {image_path} gid 0",
    ))
    created_directories.add(image_path)

  create_directory(destination)
  for local_path in sorted(source.rglob("*")):
    if "__pycache__" in local_path.parts:
      continue
    relative = local_path.relative_to(source)
    image_path = str(Path(destination) / relative)
    if local_path.is_dir():
      create_directory(image_path)
      continue
    create_directory(str(Path(image_path).parent))
    mode = "0100755" if local_path.stat().st_mode & 0o111 else "0100644"
    commands.extend((
      f"write {local_path} {image_path}",
      f"set_inode_field {image_path} mode {mode}",
      f"set_inode_field {image_path} uid 0",
      f"set_inode_field {image_path} gid 0",
    ))

  with tempfile.NamedTemporaryFile("w", encoding="utf-8") as command_file:
    command_file.write("\n".join(commands) + "\n")
    command_file.flush()
    result = run_cmd([debugfs, "-w", "-f", command_file.name, str(image)])
  output = f"{result.stdout}\n{result.stderr}"
  if "File not found" in output or "Ext2 file already exists" in output:
    raise RuntimeError(f"Failed to add StarPilot dependency tree {destination}:\n{output[-4000:]}")
  if not image_path_exists(debugfs, image, destination):
    raise RuntimeError(f"Failed to add StarPilot dependency tree {destination}")


def add_path_to_image(debugfs: str, image: Path, source: Path, destination: str) -> None:
  if image_path_exists(debugfs, image, destination):
    raise RuntimeError(f"Refusing to overwrite upstream image path {destination}")
  if source.is_symlink():
    ensure_image_directory(debugfs, image, str(Path(destination).parent))
    target = os.readlink(source)
    if "/" in target or target in ("", ".", ".."):
      raise RuntimeError(f"Unsafe compatibility-library symlink target: {target!r}")
    run_debugfs(debugfs, image, f"symlink {destination} {target}", write=True)
    stat = run_debugfs(debugfs, image, f"stat {destination}")
    if "Type: symlink" not in stat or f'Fast link dest: "{target}"' not in stat:
      raise RuntimeError(f"Failed to add StarPilot dependency symlink {destination}")
    return
  if source.is_dir():
    add_tree_to_image(debugfs, image, source, destination)
    return
  if not source.is_file():
    raise RuntimeError(f"Extracted dependency path is missing: {source}")
  ensure_image_directory(debugfs, image, str(Path(destination).parent))
  run_debugfs(debugfs, image, f"write {source} {destination}", write=True)
  if not image_path_exists(debugfs, image, destination):
    raise RuntimeError(f"Failed to add StarPilot dependency file {destination}")
  inode = parse_inode(run_debugfs(debugfs, image, f"stat {destination}"))
  mode = "0100755" if source.stat().st_mode & 0o111 else "0100644"
  for field, value in (("mode", mode), ("uid", "0"), ("gid", "0")):
    run_debugfs(debugfs, image, f"set_inode_field <{inode}> {field} {value}", write=True)


def replace_image_file(debugfs: str, image: Path, source: Path, destination: str) -> None:
  if destination not in FACTORY_INSTALL_PATHS:
    raise RuntimeError(f"Refusing to replace non-factory-install path {destination}")
  if not image_path_exists(debugfs, image, destination):
    raise RuntimeError(f"Factory-install path is missing from upstream image: {destination}")
  if not source.is_file():
    raise RuntimeError(f"Replacement payload is missing: {source}")
  run_debugfs(debugfs, image, f"rm {destination}", write=True)
  run_debugfs(debugfs, image, f"write {source} {destination}", write=True)
  inode = parse_inode(run_debugfs(debugfs, image, f"stat {destination}"))
  for field, value in (("mode", "0100755"), ("uid", "0"), ("gid", "0")):
    run_debugfs(debugfs, image, f"set_inode_field <{inode}> {field} {value}", write=True)


def fingerprint_image_paths(debugfs: str, image: Path, paths: tuple[str, ...], work_dir: Path,
                            label: str) -> dict[str, str]:
  output_dir = work_dir / f"fingerprints_{label}"
  output_dir.mkdir(parents=True, exist_ok=True)
  fingerprints: dict[str, str] = {}
  for image_path in paths:
    local_path = output_dir / image_path.strip("/").replace("/", "_")
    run_debugfs(debugfs, image, f"dump -p {image_path} {local_path}")
    fingerprints[image_path] = sha256_file(local_path)
  return fingerprints


def validate_protected_payloads(actual: dict[str, str]) -> None:
  differences = {
    path: {"actual": actual.get(path), "expected": expected}
    for path, expected in PROTECTED_PAYLOAD_HASHES.items()
    if actual.get(path) != expected
  }
  if differences:
    raise RuntimeError(f"Image is not exact upstream AGNOS: {json.dumps(differences, sort_keys=True)}")


def validate_ext4(e2fsck: str, image: Path) -> None:
  result = run_cmd([e2fsck, "-fn", str(image)], allowed_returncodes=frozenset({0, 1, 2}))
  output = f"{result.stdout}\n{result.stderr}"
  if "UNEXPECTED INCONSISTENCY" in output or "Filesystem still has errors" in output:
    raise RuntimeError(f"ext4 validation failed:\n{output}")


def compress_xz(source: Path, destination: Path) -> None:
  destination.parent.mkdir(parents=True, exist_ok=True)
  partial = destination.with_suffix(destination.suffix + ".part")
  print(f"Compressing {source} -> {destination}", flush=True)
  with partial.open("wb") as output:
    result = subprocess.run(["xz", "-T0", "-6", "-c", str(source)], stdout=output, stderr=subprocess.PIPE)
  if result.returncode != 0:
    partial.unlink(missing_ok=True)
    raise RuntimeError(result.stderr.decode("utf-8", "replace"))
  partial.replace(destination)


def get_system_entry(manifest: list[dict]) -> dict:
  return next(entry for entry in manifest if entry.get("name") == "system")


def update_manifest_system_entry(manifest: list[dict], new_url: str, raw_hash: str, size: int) -> list[dict]:
  updated = json.loads(json.dumps(manifest))
  entry = get_system_entry(updated)
  entry.update({
    "url": new_url,
    "hash": raw_hash,
    "hash_raw": raw_hash,
    "size": size,
    "sparse": False,
    "full_check": False,
    "has_ab": True,
    "ondevice_hash": raw_hash,
  })
  entry.pop("alt", None)
  entry.pop("casync_caibx", None)
  entry.pop("casync_store", None)
  return updated


def main() -> int:
  args = parse_args()
  target_version = validate_target_version(args.set_version)
  debugfs, e2fsck = find_debugfs(), find_e2fsck()
  work_dir = Path(args.work_dir).resolve()
  work_dir.mkdir(parents=True, exist_ok=True)

  if args.source_image:
    source = Path(args.source_image).resolve()
  else:
    source = work_dir / "upstream_system.img.xz"
    if args.force_download:
      source.unlink(missing_ok=True)
    if not source.exists():
      download(args.source_url, source)
  if not source.is_file():
    raise RuntimeError(f"Source image not found: {source}")

  upstream_raw = work_dir / "upstream_system.ext4.img"
  materialize_upstream_image(source, upstream_raw, work_dir)
  if upstream_raw.stat().st_size != UPSTREAM_RAW_SIZE:
    raise RuntimeError(f"Upstream raw size mismatch: {upstream_raw.stat().st_size}")
  upstream_hash = sha256_file(upstream_raw)
  if upstream_hash != UPSTREAM_RAW_SHA256:
    raise RuntimeError(f"Upstream raw hash mismatch: {upstream_hash}")
  validate_ext4(e2fsck, upstream_raw)
  if read_image_text(debugfs, upstream_raw, VERSION_PATH_IN_IMAGE) != UPSTREAM_VERSION:
    raise RuntimeError("Source image does not contain upstream /VERSION=19.6")
  upstream_venv = validate_venv_layout(
    debugfs, upstream_raw,
    expected_count=UPSTREAM_SITE_PACKAGES_COUNT,
    required_paths=UPSTREAM_REQUIRED_VENV_PATHS,
  )
  additive_dependency_paths = (*STAR_PILOT_DEPENDENCY_PATHS, *LEGACY_RUNTIME_LIBRARY_PATHS)
  unexpected_dependency_paths = [
    path for path in additive_dependency_paths if image_path_exists(debugfs, upstream_raw, path)
  ]
  if unexpected_dependency_paths:
    raise RuntimeError(f"Dependency allowlist overlaps upstream AGNOS: {unexpected_dependency_paths}")
  upstream_payloads = fingerprint_image_paths(debugfs, upstream_raw, tuple(UPSTREAM_PAYLOAD_HASHES), work_dir, "upstream")
  upstream_differences = {
    path: {"actual": upstream_payloads.get(path), "expected": expected}
    for path, expected in UPSTREAM_PAYLOAD_HASHES.items()
    if upstream_payloads.get(path) != expected
  }
  if upstream_differences:
    raise RuntimeError(f"Source image is not exact upstream AGNOS: {json.dumps(upstream_differences, sort_keys=True)}")

  upstream_fingerprint_dir = work_dir / "fingerprints_upstream"
  customized_payload_dir = work_dir / "starpilot_factory_install"
  if customized_payload_dir.exists():
    shutil.rmtree(customized_payload_dir)
  customized_payload_dir.mkdir(parents=True)
  customized_setup = customized_payload_dir / "setup"
  customized_installer = customized_payload_dir / "installer"
  patch_setup_zipapp(upstream_fingerprint_dir / "usr_comma_setup", customized_setup)
  patch_installer_binary(upstream_fingerprint_dir / "usr_comma_installer", customized_installer)
  validate_factory_install_payloads(customized_setup, customized_installer)

  c3_work_dir = work_dir / "c3_dependency_source"
  c3_work_dir.mkdir(parents=True, exist_ok=True)
  if args.c3_deps_image:
    c3_source = Path(args.c3_deps_image).resolve()
  else:
    c3_source = c3_work_dir / "system.img.xz"
    if args.force_download:
      c3_source.unlink(missing_ok=True)
    if not c3_source.exists():
      download(args.c3_deps_url, c3_source)
  if not c3_source.is_file():
    raise RuntimeError(f"C3 dependency source image not found: {c3_source}")
  c3_raw = c3_work_dir / "system.ext4.img"
  materialize_upstream_image(c3_source, c3_raw, c3_work_dir)
  if c3_raw.stat().st_size != C3_DEPENDENCY_SOURCE_RAW_SIZE:
    raise RuntimeError(f"C3 dependency source size mismatch: {c3_raw.stat().st_size}")
  c3_source_hash = sha256_file(c3_raw)
  if c3_source_hash != C3_DEPENDENCY_SOURCE_RAW_SHA256:
    raise RuntimeError(f"C3 dependency source hash mismatch: {c3_source_hash}")
  dependency_packages_dir = work_dir / "starpilot_dependency_packages"
  if dependency_packages_dir.exists():
    shutil.rmtree(dependency_packages_dir)
  extract_starpilot_dependencies(debugfs, c3_raw, dependency_packages_dir)
  legacy_runtime_dir = work_dir / "starpilot_legacy_runtime_libraries"
  if legacy_runtime_dir.exists():
    shutil.rmtree(legacy_runtime_dir)
  extract_legacy_runtime_libraries(debugfs, c3_raw, legacy_runtime_dir)

  candidate_raw = work_dir / f"starpilot_system_{target_version}.ext4.img"
  candidate_raw.unlink(missing_ok=True)
  shutil.copy2(upstream_raw, candidate_raw)
  version_file = work_dir / "VERSION.starpilot"
  version_file.write_text(target_version + "\n", encoding="utf-8")
  write_version(debugfs, candidate_raw, version_file)
  for image_path in STAR_PILOT_DEPENDENCY_PATHS:
    add_path_to_image(debugfs, candidate_raw, dependency_packages_dir / Path(image_path).name, image_path)
  for image_path in LEGACY_RUNTIME_LIBRARY_PATHS:
    add_path_to_image(debugfs, candidate_raw, legacy_runtime_dir / Path(image_path).name, image_path)
  replace_image_file(debugfs, candidate_raw, customized_setup, SETUP_PATH_IN_IMAGE)
  replace_image_file(debugfs, candidate_raw, customized_installer, INSTALLER_PATH_IN_IMAGE)

  if read_image_text(debugfs, candidate_raw, VERSION_PATH_IN_IMAGE) != target_version:
    raise RuntimeError("Failed to write the StarPilot AGNOS version marker")
  candidate_venv = validate_venv_layout(
    debugfs, candidate_raw,
    expected_count=CANDIDATE_SITE_PACKAGES_COUNT,
    required_paths=REQUIRED_VENV_PATHS,
  )
  missing_legacy_runtime = [
    path for path in LEGACY_RUNTIME_LIBRARY_PATHS if not image_path_exists(debugfs, candidate_raw, path)
  ]
  if missing_legacy_runtime:
    raise RuntimeError(f"Candidate image is missing legacy runtime libraries: {missing_legacy_runtime}")
  candidate_payloads = fingerprint_image_paths(debugfs, candidate_raw, tuple(PROTECTED_PAYLOAD_HASHES), work_dir, "candidate")
  validate_protected_payloads(candidate_payloads)
  upstream_protected_payloads = {path: upstream_payloads[path] for path in PROTECTED_PAYLOAD_HASHES}
  if candidate_payloads != upstream_protected_payloads:
    raise RuntimeError("Protected upstream payloads changed")
  candidate_factory_payloads = fingerprint_image_paths(
    debugfs, candidate_raw, tuple(UPSTREAM_FACTORY_INSTALL_HASHES), work_dir, "candidate_factory_install",
  )
  expected_factory_payloads = {
    SETUP_PATH_IN_IMAGE: sha256_file(customized_setup),
    INSTALLER_PATH_IN_IMAGE: sha256_file(customized_installer),
  }
  if candidate_factory_payloads != expected_factory_payloads:
    raise RuntimeError("Factory-install payloads do not match the validated StarPilot replacements")
  candidate_factory_dir = work_dir / "fingerprints_candidate_factory_install"
  validate_factory_install_payloads(
    candidate_factory_dir / "usr_comma_setup",
    candidate_factory_dir / "usr_comma_installer",
  )
  validate_ext4(e2fsck, candidate_raw)

  raw_hash = sha256_file(candidate_raw)
  output_xz = Path(args.output_xz).resolve() if args.output_xz else work_dir / f"system-{raw_hash}.img.xz"
  compress_xz(candidate_raw, output_xz)
  metadata = {
    "base_version": UPSTREAM_VERSION,
    "base_raw_sha256": UPSTREAM_RAW_SHA256,
    "target_version": target_version,
    "allowed_image_mutations": sorted(ALLOWED_IMAGE_MUTATIONS),
    "raw_sha256": raw_hash,
    "raw_size": candidate_raw.stat().st_size,
    "xz_sha256": sha256_file(output_xz),
    "xz_size": output_xz.stat().st_size,
    "upstream_venv_validation": upstream_venv,
    "candidate_venv_validation": candidate_venv,
    "c3_dependency_source_raw_sha256": c3_source_hash,
    "starpilot_dependency_paths": list(STAR_PILOT_DEPENDENCY_PATHS),
    "c3_dependency_paths": list(C3_DEPENDENCY_PATHS),
    "legacy_runtime_library_paths": list(LEGACY_RUNTIME_LIBRARY_PATHS),
    "protected_payloads": candidate_payloads,
    "factory_install_payloads": candidate_factory_payloads,
    "factory_reset_stack": (
      "upstream reset/network/updater/Magic unchanged; setup uses the bundled stock COMMA/GBM installer "
      "for both the default StarPilot install and custom GitHub owner/branch installs"
    ),
    "device_validation_required": True,
  }
  metadata_path = Path(str(output_xz) + ".metadata.json")
  metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

  print("Validated upstream-based StarPilot AGNOS artifact:")
  print(f"  target version: {target_version}")
  print(f"  raw image:      {candidate_raw}")
  print(f"  xz image:       {output_xz}")
  print(f"  raw sha256:     {raw_hash}")
  print(f"  xz sha256:      {metadata['xz_sha256']}")
  print(f"  metadata:       {metadata_path}")
  print("  only mutations: /VERSION, additive StarPilot runtime/C3 compatibility, and factory setup/installer branding")

  if args.new_url:
    manifest_path = Path(args.manifest).resolve()
    output_manifest = Path(args.manifest_out).resolve() if args.manifest_out else work_dir / "agnos.candidate.json"
    if output_manifest == manifest_path:
      raise RuntimeError("Refusing to overwrite the checked-in manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_manifest.write_text(
      json.dumps(update_manifest_system_entry(manifest, args.new_url, raw_hash, candidate_raw.stat().st_size), indent=2) + "\n",
      encoding="utf-8",
    )
    print(f"  candidate manifest: {output_manifest}")
  elif args.manifest_out:
    raise RuntimeError("--manifest-out requires --new-url")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
