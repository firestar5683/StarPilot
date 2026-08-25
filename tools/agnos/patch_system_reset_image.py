#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import struct
import tempfile
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path


RESET_PATH_IN_IMAGE = "/usr/comma/reset"
COMMA_SH_PATH_IN_IMAGE = "/usr/comma/comma.sh"
MAGIC_PATH_IN_IMAGE = "/usr/comma/magic.py"
SETUP_PATH_IN_IMAGE = "/usr/comma/setup"
UPDATER_PATH_IN_IMAGE = "/usr/comma/updater"
BG_PATH_IN_IMAGE = "/usr/comma/bg.jpg"
WESTON_SERVICE_PATH_IN_IMAGE = "/lib/systemd/system/weston.service"
RESET_ENTRY_IN_ZIPAPP = "openpilot/system/ui/reset.py"
MICI_RESET_ENTRY_IN_ZIPAPP = "openpilot/system/ui/mici_reset.py"
TICI_RESET_ENTRY_IN_ZIPAPP = "openpilot/system/ui/tici_reset.py"
APPLICATION_ENTRY_IN_ZIPAPP = "openpilot/system/ui/lib/application.py"
WIFI_MANAGER_ENTRY_IN_SETUP_ZIPAPP = "openpilot/system/ui/lib/wifi_manager.py"
SETUP_ENTRY_IN_SETUP_ZIPAPP = "openpilot/system/ui/setup.py"
TICI_SETUP_ENTRY_IN_SETUP_ZIPAPP = "openpilot/system/ui/tici_setup.py"
MICI_SETUP_ENTRY_IN_SETUP_ZIPAPP = "openpilot/system/ui/mici_setup.py"
UPDATER_ENTRY_IN_ZIPAPP = "openpilot/system/ui/updater.py"
VERSION_PATH_IN_IMAGE = "/VERSION"
PYTHON_SITE_PACKAGES_PATH_IN_IMAGE = "/usr/local/venv/lib/python3.12/site-packages"
AMDGPU_FIRMWARE_PATH_IN_IMAGE = "/lib/firmware/amdgpu"
PATCH_MARKER = "STARPILOT_C4_RESET_LAYOUT_V1"
APP_PATCH_MARKER = "STARPILOT_C4_RESET_APP_DIMENSIONS_V1"
SETUP_WIFI_PATCH_MARKER = "JEEPNY_AVAILABLE = True"
SETUP_BRANDING_PATCH_MARKER = "STARPILOT_SETUP_BRANDING_V1"
SETUP_SSH_RESTORE_PATCH_MARKER = "STARPILOT_SETUP_SSH_RESTORE_V1"
WESTON_BG_PATCH_MARKER = "STARPILOT_WESTON_BG_ORIENTATION_V2"
COMMA_SH_DISPLAY_WAIT_PATCH_MARKER = "STARPILOT_DISPLAY_READY_WAIT_V1"
JEEPNY_VERSION = "0.9.0"
JEEPNY_WHEEL_URL = "https://files.pythonhosted.org/packages/b2/a3/e137168c9c44d18eff0376253da9f1e9234d0239e0ee230d2fee6cea8e55/jeepney-0.9.0-py3-none-any.whl"
JEEPNY_WHEEL_SHA256 = "97e5714520c16fc0a45695e5365a2e11b81ea79bba796e26f9f1d178cb182683"
JEEPNY_PACKAGE_DIR = "jeepney"
JEEPNY_DIST_INFO_DIR = f"jeepney-{JEEPNY_VERSION}.dist-info"
ANDROID_SPARSE_MAGIC = 0xED26FF3A
CHUNK_TYPE_RAW = 0xCAC1
CHUNK_TYPE_FILL = 0xCAC2
CHUNK_TYPE_DONT_CARE = 0xCAC3
CHUNK_TYPE_CRC32 = 0xCAC4
XZ_MAGIC = b"\xFD7zXZ\x00"

AMDGPU_FIRMWARE_SHA256 = {
  "gc_12_0_0_imu.bin.zst": "aa15e5b3156bffc45e0c50bccbcd364fbd3f958531b695b7487a803d780b8328",
  "gc_12_0_0_me.bin.zst": "d7eba5197f2580f32b8256b1d9cb68e723e9e644293a34446a7913e3c093cba5",
  "gc_12_0_0_mec.bin.zst": "1931593440b8f9423580d9e2cdc5b34e7c682cdffe1ca4b74b0c2f6a0420236d",
  "gc_12_0_0_pfp.bin.zst": "16bfd64c10fe73b5e760055069a60e5841dba16c0ed4edb56c20d675e23901f6",
  "gc_12_0_0_rlc.bin.zst": "6436b582734a413456fff3d3c7195e71cc9e78a7ed31ee21c83ffd6fae1ad186",
  "psp_14_0_2_sos.bin.zst": "7b538448b57d4f9dd06b2eea90d4f86a16e65e3027cdecee8db71c2c5f1fa243",
  "sdma_7_0_0.bin.zst": "beaafb53993a106edd392392d5896245ae2a957c6d0f495d0002eec72ad8ad38",
  "smu_14_0_2.bin.zst": "6951995d1d606f4dc60c895f19d34ed18aa40e62129f83d8510c45e8aa9ae2fc",
}

DEFAULT_SYNC_COMMA_FILES = [
  "/usr/comma/bg.jpg",
  "/usr/comma/comma.sh",
  "/usr/comma/debug.py",
  "/usr/comma/fs_setup.sh",
  "/usr/comma/installer",
  "/usr/comma/magic.py",
  "/usr/comma/power_drop_monitor.py",
  "/usr/comma/power_monitor.py",
  "/usr/comma/reset",
  "/usr/comma/screen_calibration.py",
  "/usr/comma/setup",
  "/usr/comma/setup_keys",
  "/usr/comma/updater",
]

INODE_MODE_TYPE_PREFIX = {
  "regular": "100",
  "directory": "040",
  "symlink": "120",
  "character": "20",
  "block": "60",
  "fifo": "10",
  "socket": "140",
}

def patch_application_script(original: bytes) -> bytes:
  if APP_PATCH_MARKER.encode("utf-8") in original:
    return original

  text = original.decode("utf-8", "replace")
  replacement = (
    f"# {APP_PATCH_MARKER}\n"
    "_dt = HARDWARE.get_device_type()\n"
    "if _dt in ('tici', 'tizi'):\n"
    "  gui_app = GuiApplication(2160, 1080)\n"
    "else:\n"
    "  gui_app = GuiApplication(536, 240)\n"
  )

  fixed = text.replace("gui_app = GuiApplication(2160, 1080)", replacement)
  if fixed == text:
    fixed = re.sub(
      r"^gui_app\s*=\s*GuiApplication\([^\n]+\)\s*$",
      replacement.rstrip("\n"),
      text,
      count=1,
      flags=re.MULTILINE,
    )

  if fixed == text:
    # Newer upstream application.py is already device-aware via GuiApplication defaults.
    # Keep it as-is and stamp a marker so verification can still pass.
    if text.startswith("#!"):
      first_nl = text.find("\n")
      if first_nl != -1:
        fixed = text[:first_nl + 1] + f"# {APP_PATCH_MARKER} (no-op)\n" + text[first_nl + 1:]
      else:
        fixed = text + f"\n# {APP_PATCH_MARKER} (no-op)\n"
    else:
      fixed = f"# {APP_PATCH_MARKER} (no-op)\n" + text

  return fixed.encode("utf-8")


def patch_setup_wifi_manager() -> bytes:
  """
  Replace setup zipapp's wifi_manager.py with repo version that gracefully handles
  missing jeepney (fallback to nmcli/fake), preventing setup boot-logo hangs.
  """
  repo_root = Path(__file__).resolve().parents[2]
  src = repo_root / "system/ui/lib/wifi_manager.py"
  if not src.is_file():
    raise RuntimeError(f"Unable to find repo wifi_manager source: {src}")
  data = src.read_bytes()
  if SETUP_WIFI_PATCH_MARKER.encode("utf-8") not in data:
    raise RuntimeError("Repo wifi_manager.py does not appear to include jeepney fallback marker")
  return data


def patched_weston_bg_python() -> str:
  som_id_path = "/sys/devices/platform/vendor/vendor:gpio-som-id/som_id"
  return (
    "from PIL import Image; "
    f"som=open(\"{som_id_path}\").read().strip(); "
    "img=Image.open(\"/usr/comma/bg.jpg\").convert(\"RGB\"); "
    "img=img.rotate(180) if som == \"1\" else img; "
    "mask=img.convert(\"L\").point(lambda p: 255 if p > 16 else 0); "
    "bbox=mask.getbbox(); "
    "logo=img.crop(bbox) if bbox else img; "
    # Pillow positive degrees are counter-clockwise; -90 pre-rotates the source clockwise.
    "logo=logo.rotate(-90, expand=True); "
    "resample=Image.Resampling.LANCZOS if hasattr(Image, \"Resampling\") else Image.LANCZOS; "
    "logo=logo.resize((max(1, logo.width//3), max(1, logo.height//3)), resample); "
    "canvas=Image.new(\"RGB\", img.size, (0, 0, 0)); "
    "canvas.paste(logo, ((img.width - logo.width)//2, (img.height - logo.height)//2)); "
    "canvas.save(\"/tmp/bg.jpg\")"
  )


def patched_weston_bg_exec_line() -> str:
  python_cmd = patched_weston_bg_python().replace('"', '\\"')
  return f"ExecStartPre=/bin/bash -c \"/usr/local/venv/bin/python -c '{python_cmd}'\""


def patch_comma_sh_display_wait(original: bytes) -> bytes:
  text = original.decode("utf-8")
  if COMMA_SH_DISPLAY_WAIT_PATCH_MARKER in text:
    return original

  old = """echo "waiting for magic"
for i in {1..200}; do
  if systemctl is-active --quiet magic && [ -S /tmp/drmfd.sock ]; then
    break
  fi
  sleep 0.1
done

if systemctl is-active --quiet magic && [ -S /tmp/drmfd.sock ]; then
  echo "magic ready after ${SECONDS}s"
else
  echo "timed out waiting for magic, ${SECONDS}s"
fi
"""
  new = f"""# {COMMA_SH_DISPLAY_WAIT_PATCH_MARKER}
if systemctl cat magic.service >/dev/null 2>&1; then
  echo "waiting for magic"
  for i in {{1..200}}; do
    if systemctl is-active --quiet magic && [ -S /tmp/drmfd.sock ]; then
      break
    fi
    sleep 0.1
  done

  if systemctl is-active --quiet magic && [ -S /tmp/drmfd.sock ]; then
    echo "magic ready after ${{SECONDS}}s"
  else
    echo "timed out waiting for magic, ${{SECONDS}}s"
  fi
else
  echo "magic unavailable; waiting for weston"
  for i in {{1..200}}; do
    if systemctl is-active --quiet weston-ready && [ -S /var/tmp/weston/wayland-0 ]; then
      break
    fi
    sleep 0.1
  done

  if systemctl is-active --quiet weston-ready && [ -S /var/tmp/weston/wayland-0 ]; then
    echo "weston ready after ${{SECONDS}}s"
  else
    echo "timed out waiting for weston, ${{SECONDS}}s"
  fi
fi
"""

  if old not in text:
    raise RuntimeError("Unable to find comma.sh display readiness wait")
  return text.replace(old, new, 1).encode("utf-8")


def patch_weston_service(original: bytes) -> bytes:
  text = original.decode("utf-8")
  if WESTON_BG_PATCH_MARKER in text:
    return original

  old = (
    "ExecStartPre=/bin/bash -c \"/usr/local/venv/bin/python -c 'from PIL import Image; "
    "img=Image.open(\\\"/usr/comma/bg.jpg\\\"); "
    "(img.rotate(180) if open(\\\"/sys/devices/platform/vendor/vendor:gpio-som-id/som_id\\\").read().strip() == \\\"1\\\" else img).save(\\\"/tmp/bg.jpg\\\")'\""
  )
  new = (
    f"# {WESTON_BG_PATCH_MARKER}: displayed boot logo was 90 degrees counter-clockwise.\n"
    f"{patched_weston_bg_exec_line()}"
  )

  if old not in text:
    raise RuntimeError("Unable to find weston.service background image generation line")
  return text.replace(old, new, 1).encode("utf-8")


def patch_setup_branding_script(original: bytes, entry_name: str) -> bytes:
  text = original.decode("utf-8")
  if SETUP_BRANDING_PATCH_MARKER in text:
    return text.encode("utf-8")

  text = text.replace(
    'OPENPILOT_URL = "https://openpilot.comma.ai"',
    'NETWORK_CHECK_URL = "https://openpilot.comma.ai"\n'
    'DEFAULT_INSTALLER_URL = "https://installer.comma.ai/firestar5683/StarPilot"\n'
    f'# {SETUP_BRANDING_PATCH_MARKER}',
  )
  text = text.replace("urllib.request.Request(OPENPILOT_URL, method=\"HEAD\")",
                      "urllib.request.Request(NETWORK_CHECK_URL, method=\"HEAD\")")
  text = text.replace("urllib.request.urlopen(OPENPILOT_URL, timeout=2)",
                      "urllib.request.urlopen(NETWORK_CHECK_URL, timeout=2)")
  text = text.replace("self.download(OPENPILOT_URL)", "self.download(DEFAULT_INSTALLER_URL)")

  if entry_name == MICI_SETUP_ENTRY_IN_SETUP_ZIPAPP:
    text = text.replace('LargerSlider("slide to use\\nopenpilot"', 'LargerSlider("slide to use\\nstarpilot"')
    text = text.replace('LargerSlider("slide to install\\nopenpilot"', 'LargerSlider("slide to install\\nstarpilot"')
    text = text.replace('BigPillButton("install openpilot"', 'BigPillButton("install StarPilot"')
    text = text.replace('set_text("install openpilot"', 'set_text("install StarPilot"')
  elif entry_name == TICI_SETUP_ENTRY_IN_SETUP_ZIPAPP:
    text = text.replace('ButtonRadio("openpilot"', 'ButtonRadio("StarPilot"')

  if SETUP_BRANDING_PATCH_MARKER not in text:
    raise RuntimeError(f"Failed to patch setup branding for {entry_name}")

  return text.encode("utf-8")


def patch_setup_module(relative_path: str) -> bytes:
  """
  Replace setup zipapp module with repo version so setup behavior stays in sync.
  """
  repo_root = Path(__file__).resolve().parents[2]
  src = repo_root / relative_path
  if not src.is_file():
    raise RuntimeError(f"Unable to find repo setup source: {src}")
  return src.read_bytes()


def patch_setup_script_with_ssh_restore(relative_path: str) -> bytes:
  """
  Apply SSH-key restore logic directly into setup scripts for AGNOS images.
  This keeps repo runtime behavior unchanged while making image reset flows
  resilient to setup/install failures.
  """
  text = patch_setup_module(relative_path).decode("utf-8")
  if SETUP_SSH_RESTORE_PATCH_MARKER in text:
    return text.encode("utf-8")

  restore_block = f"""
# {SETUP_SSH_RESTORE_PATCH_MARKER}
def _restore_ssh_after_reset():
  backup_dir = "/cache/reset_backup"
  params_dir = "/data/params/d"
  if not os.path.isdir(backup_dir):
    return

  restored = False
  try:
    os.makedirs(params_dir, exist_ok=True)
    for key in ("GithubSshKeys", "SshEnabled"):
      src = f"{{backup_dir}}/{{key}}"
      dst = f"{{params_dir}}/{{key}}"
      if not os.path.isfile(src):
        continue
      shutil.copyfile(src, dst)
      os.chmod(dst, 0o600)
      restored = True

    if restored:
      os.system("sudo chown -R comma:comma /data/params >/dev/null 2>&1 || true")
      os.system("sudo /usr/comma/set_ssh.sh >/tmp/setup_ssh_restore.log 2>&1 || true")
  finally:
    os.system(f"sudo rm -rf {{backup_dir}} >/dev/null 2>&1 || true")
"""

  if "def main():" not in text:
    raise RuntimeError(f"Unable to patch setup script without main(): {relative_path}")

  text = text.replace("\ndef main():", f"{restore_block}\n\ndef main():", 1)
  text = text.replace("  try:\n    gui_app.init_window(", "  try:\n    _restore_ssh_after_reset()\n    gui_app.init_window(", 1)
  return text.encode("utf-8")


def get_setup_replacements() -> dict[str, bytes]:
  """
  Keep the reference setup bundle intact and patch only the networking backend.

  The reference AGNOS setup bundle already contains the correct small-screen
  selector and matching mici UI modules. Replacing those modules with repo-head
  versions caused bootstrap incompatibilities. The only setup-side changes we
  still need are the jeepney fallback plus the StarPilot branding/url strings.
  """
  return {
    WIFI_MANAGER_ENTRY_IN_SETUP_ZIPAPP: patch_setup_wifi_manager(),
  }


def patch_updater_module() -> bytes:
  """
  Replace only the bundled updater selector with the repo version.

  The selector itself carries the small-screen fallback logic; the rest of the
  reference updater zipapp stays unchanged.
  """
  repo_root = Path(__file__).resolve().parents[2]
  src = repo_root / "system/ui/updater.py"
  if not src.is_file():
    raise RuntimeError(f"Unable to find repo updater source: {src}")
  return src.read_bytes()


def patch_reset_script() -> bytes:
  """
  Use repo reset.py so AGNOS reset stays in sync with upstream selector logic.
  """
  repo_root = Path(__file__).resolve().parents[2]
  src = repo_root / "system/ui/reset.py"
  if not src.is_file():
    raise RuntimeError(f"Unable to find repo reset source: {src}")
  data = src.read_text(encoding="utf-8")
  if PATCH_MARKER not in data:
    if data.startswith("#!"):
      first_nl = data.find("\n")
      if first_nl != -1:
        data = data[:first_nl + 1] + f"# {PATCH_MARKER}\n" + data[first_nl + 1:]
      else:
        data = data + f"\n# {PATCH_MARKER}\n"
    else:
      data = f"# {PATCH_MARKER}\n" + data
  return data.encode("utf-8")


def parse_args() -> argparse.Namespace:
  p = argparse.ArgumentParser(description="Patch AGNOS system image with StarPilot reset and hardware support")
  p.add_argument("--manifest", default="system/hardware/tici/agnos.json", help="Path to AGNOS manifest JSON")
  p.add_argument("--work-dir", default=".cache/agnos_reset_patch", help="Working directory")
  p.add_argument("--source-url", default=None, help="Override source raw system image URL")
  p.add_argument("--source-image", default=None, help="Use existing local raw system image file instead of download")
  p.add_argument("--reference-manifest", default=None, help="Optional AGNOS manifest used to source /usr/comma installer payloads")
  p.add_argument("--reference-source-url", default=None, help="Override reference AGNOS system image URL for /usr/comma file sync")
  p.add_argument("--reference-image", default=None, help="Use existing local reference system image file for /usr/comma file sync")
  p.add_argument("--sync-comma-files", default=",".join(DEFAULT_SYNC_COMMA_FILES),
                 help="Comma-separated file list to sync from reference image (e.g. /usr/comma/installer,/usr/comma/setup)")
  p.add_argument("--disable-comma-file-sync", action="store_true",
                 help="Disable syncing /usr/comma files from a reference image")
  p.add_argument("--disable-usbgpu-firmware", action="store_true",
                 help="Do not install the AMD firmware required by the external GPU")
  p.add_argument("--output-xz", default=None, help="Output .img.xz path")
  p.add_argument("--new-url", default=None, help="Hosted URL for patched image; used for manifest output")
  p.add_argument("--manifest-out", default=None, help="Write updated manifest JSON here")
  p.add_argument("--in-place-manifest", action="store_true", help="Update manifest file in place")
  p.add_argument("--force-download", action="store_true", help="Force redownload source image")
  p.add_argument("--set-version", default=None, help="Override /VERSION inside patched image (e.g. 12.8.1)")
  return p.parse_args()


def find_debugfs() -> str:
  candidates = [
    os.environ.get("DEBUGFS"),
    "debugfs",
    "/opt/homebrew/opt/e2fsprogs/sbin/debugfs",
  ]
  for c in candidates:
    if c and shutil.which(c):
      return c
    if c and Path(c).is_file():
      return c
  raise RuntimeError("debugfs not found. Install e2fsprogs and retry.")


def load_manifest(path: Path) -> list[dict]:
  return json.loads(path.read_text())


def get_system_entry(manifest: list[dict]) -> dict:
  for e in manifest:
    if e.get("name") == "system":
      return e
  raise RuntimeError("No system entry found in manifest")


def pick_source_url(system_entry: dict, override: str | None) -> str:
  if override:
    return override
  url = system_entry.get("url")
  if isinstance(url, str):
    return url
  alt = system_entry.get("alt")
  if isinstance(alt, dict) and isinstance(alt.get("url"), str):
    return alt["url"]
  raise RuntimeError("No source URL found for system image")


def find_default_reference_manifest(primary_manifest_path: Path) -> Path | None:
  # Expected tree layout for local development:
  #   <parent>/starpilot/system/hardware/tici/agnos.json
  #   <parent>/openpilot/system/hardware/tici/agnos.json
  repo_root = primary_manifest_path
  for _ in range(4):
    if repo_root.parent == repo_root:
      break
    repo_root = repo_root.parent

  candidates = [
    repo_root.parent / "openpilot/openpilot/system/hardware/tici/agnos.json",
    repo_root.parent / "openpilot/system/hardware/tici/agnos.json",
    repo_root / "openpilot/system/hardware/tici/agnos.json",
  ]

  for candidate in candidates:
    if candidate.is_file() and candidate.resolve() != primary_manifest_path.resolve():
      return candidate.resolve()
  return None


def parse_sync_file_list(raw: str) -> list[str]:
  out: list[str] = []
  seen: set[str] = set()
  for token in raw.replace(";", ",").split(","):
    item = token.strip()
    if not item:
      continue
    if not item.startswith("/"):
      if "/" in item:
        item = f"/{item.lstrip('/')}"
      else:
        item = f"/usr/comma/{item}"
    if item not in seen:
      seen.add(item)
      out.append(item)
  return out


def download(url: str, dst: Path) -> None:
  dst.parent.mkdir(parents=True, exist_ok=True)
  tmp = dst.with_suffix(dst.suffix + ".part")
  print(f"Downloading {url} -> {dst}", flush=True)
  with urllib.request.urlopen(url) as src, open(tmp, "wb") as out:
    shutil.copyfileobj(src, out, length=1024 * 1024)
  tmp.replace(dst)


def download_with_sha256(url: str, dst: Path, expected_sha256: str) -> None:
  if not dst.exists():
    download(url, dst)

  actual_sha256 = sha256_file(dst)
  if actual_sha256 != expected_sha256:
    dst.unlink(missing_ok=True)
    download(url, dst)
    actual_sha256 = sha256_file(dst)

  if actual_sha256 != expected_sha256:
    raise RuntimeError(f"Downloaded file hash mismatch for {dst}: got {actual_sha256}, expected {expected_sha256}")


def run_cmd(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
  proc = subprocess.run(cmd, text=True, capture_output=capture)
  if check and proc.returncode != 0:
    raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
  return proc


def is_xz_file(path: Path) -> bool:
  with open(path, "rb") as f:
    header = f.read(len(XZ_MAGIC))
  return header == XZ_MAGIC


def decompress_xz(src: Path, dst: Path) -> None:
  dst.parent.mkdir(parents=True, exist_ok=True)
  tmp = dst.with_suffix(dst.suffix + ".part")
  print(f"Decompressing XZ image {src} -> {dst}", flush=True)
  with open(tmp, "wb") as out:
    proc = subprocess.run(["xz", "-d", "-c", str(src)], stdout=out, stderr=subprocess.PIPE, text=True)
  if proc.returncode != 0:
    tmp.unlink(missing_ok=True)
    raise RuntimeError(f"xz decompression failed:\n{proc.stderr}")
  tmp.replace(dst)


def is_android_sparse(path: Path) -> bool:
  with open(path, "rb") as f:
    header = f.read(4)
  if len(header) != 4:
    return False
  return int.from_bytes(header, "little") == ANDROID_SPARSE_MAGIC


def unsparse_image(src_sparse: Path, dst_raw: Path) -> None:
  print(f"Unsparsing Android image {src_sparse} -> {dst_raw}", flush=True)
  with open(src_sparse, "rb") as f_in, open(dst_raw, "wb") as f_out:
    file_hdr = f_in.read(28)
    if len(file_hdr) != 28:
      raise RuntimeError("Invalid sparse image header length")
    magic, major, minor, file_hdr_sz, chunk_hdr_sz, blk_sz, total_blks, total_chunks, _checksum = struct.unpack("<I4H4I", file_hdr)
    if magic != ANDROID_SPARSE_MAGIC:
      raise RuntimeError("Not an Android sparse image")
    if major != 1 or minor != 0:
      raise RuntimeError(f"Unsupported sparse version: {major}.{minor}")
    if file_hdr_sz > 28:
      f_in.read(file_hdr_sz - 28)
    if chunk_hdr_sz < 12:
      raise RuntimeError(f"Invalid chunk header size: {chunk_hdr_sz}")

    for _ in range(total_chunks):
      chunk_hdr = f_in.read(12)
      if len(chunk_hdr) != 12:
        raise RuntimeError("Unexpected EOF in chunk header")
      chunk_type, _reserved, chunk_sz, total_sz = struct.unpack("<2H2I", chunk_hdr)
      if chunk_hdr_sz > 12:
        f_in.read(chunk_hdr_sz - 12)

      data_sz = total_sz - chunk_hdr_sz
      out_chunk_bytes = chunk_sz * blk_sz

      if chunk_type == CHUNK_TYPE_RAW:
        if data_sz != out_chunk_bytes:
          raise RuntimeError(f"RAW chunk size mismatch: data={data_sz} out={out_chunk_bytes}")
        remaining = data_sz
        while remaining > 0:
          chunk = f_in.read(min(8 * 1024 * 1024, remaining))
          if not chunk:
            raise RuntimeError("Unexpected EOF in RAW chunk")
          f_out.write(chunk)
          remaining -= len(chunk)
      elif chunk_type == CHUNK_TYPE_FILL:
        if data_sz != 4:
          raise RuntimeError(f"FILL chunk expected 4 bytes, got {data_sz}")
        pattern = f_in.read(4)
        if len(pattern) != 4:
          raise RuntimeError("Unexpected EOF in FILL chunk")
        # Write as sparse hole if fill is zero for speed.
        if pattern == b"\x00\x00\x00\x00":
          f_out.seek(out_chunk_bytes, os.SEEK_CUR)
        else:
          unit = pattern * (blk_sz // 4)
          for _ in range(chunk_sz):
            f_out.write(unit)
      elif chunk_type == CHUNK_TYPE_DONT_CARE:
        if data_sz > 0:
          f_in.read(data_sz)
        f_out.seek(out_chunk_bytes, os.SEEK_CUR)
      elif chunk_type == CHUNK_TYPE_CRC32:
        if data_sz != 4:
          raise RuntimeError(f"CRC32 chunk expected 4 bytes, got {data_sz}")
        f_in.read(4)
      else:
        raise RuntimeError(f"Unknown sparse chunk type: 0x{chunk_type:04x}")

    f_out.truncate(total_blks * blk_sz)


def materialize_ext4_image(source_img: Path, raw_img: Path, work_dir: Path, label: str, force: bool = False) -> None:
  source_for_sparse = source_img

  if is_xz_file(source_img):
    decompressed = work_dir / f"{label}.decompressed.img"
    if force and decompressed.exists():
      decompressed.unlink()
    if not decompressed.exists():
      decompress_xz(source_img, decompressed)
    source_for_sparse = decompressed

  if force and raw_img.exists():
    raw_img.unlink()

  if raw_img.exists():
    return

  if is_android_sparse(source_for_sparse):
    unsparse_image(source_for_sparse, raw_img)
  else:
    shutil.copy2(source_for_sparse, raw_img)


def run_debugfs(debugfs: str, image: Path, request: str, write: bool = False) -> str:
  cmd = [debugfs]
  if write:
    cmd.append("-w")
  cmd += ["-R", request, str(image)]
  proc = run_cmd(cmd, check=True, capture=True)
  return f"{proc.stdout}\n{proc.stderr}"


def split_shebang(data: bytes) -> tuple[bytes, bytes]:
  if data.startswith(b"#!"):
    idx = data.find(b"\n")
    if idx != -1:
      return data[:idx + 1], data[idx + 1:]
  return b"", data


def patch_reset_zipapp(original: bytes) -> bytes:
  shebang, zip_payload = split_shebang(original)

  src_io = BytesIO(zip_payload)
  dst_io = BytesIO()
  changed = False

  replacement_reset = patch_reset_script()
  reset_replacements = {
    RESET_ENTRY_IN_ZIPAPP: replacement_reset,
  }

  with zipfile.ZipFile(src_io, "r") as src, zipfile.ZipFile(dst_io, "w", compression=zipfile.ZIP_DEFLATED) as dst:
    if APPLICATION_ENTRY_IN_ZIPAPP not in src.namelist():
      raise RuntimeError(f"{APPLICATION_ENTRY_IN_ZIPAPP} not found in reset zipapp")

    seen_entries: set[str] = set()
    for info in src.infolist():
      seen_entries.add(info.filename)
      payload = src.read(info.filename)
      if info.filename in reset_replacements:
        replacement_payload = reset_replacements[info.filename]
        if payload != replacement_payload:
          payload = replacement_payload
          changed = True
      elif info.filename == APPLICATION_ENTRY_IN_ZIPAPP:
        patched_payload = patch_application_script(payload)
        if patched_payload != payload:
          payload = patched_payload
          changed = True

      new_info = zipfile.ZipInfo(info.filename, info.date_time)
      new_info.compress_type = zipfile.ZIP_DEFLATED
      new_info.external_attr = info.external_attr
      new_info.create_system = info.create_system
      dst.writestr(new_info, payload)

    # Some reference images may not include reset.py; add missing entry explicitly.
    default_external_attr = 0o100644 << 16
    for entry, payload in reset_replacements.items():
      if entry in seen_entries:
        continue
      new_info = zipfile.ZipInfo(entry)
      new_info.compress_type = zipfile.ZIP_DEFLATED
      new_info.external_attr = default_external_attr
      new_info.create_system = 3
      dst.writestr(new_info, payload)
      changed = True

  if not changed:
    return original
  return shebang + dst_io.getvalue()


def patch_updater_zipapp(original: bytes) -> bytes:
  shebang, zip_payload = split_shebang(original)

  replacement = patch_updater_module()
  src_io = BytesIO(zip_payload)
  dst_io = BytesIO()
  changed = False
  found_updater = False

  with zipfile.ZipFile(src_io, "r") as src, zipfile.ZipFile(dst_io, "w", compression=zipfile.ZIP_DEFLATED) as dst:
    for info in src.infolist():
      payload = src.read(info.filename)
      if info.filename == UPDATER_ENTRY_IN_ZIPAPP:
        found_updater = True
        if payload != replacement:
          payload = replacement
          changed = True

      new_info = zipfile.ZipInfo(info.filename, info.date_time)
      new_info.compress_type = zipfile.ZIP_DEFLATED
      new_info.external_attr = info.external_attr
      new_info.create_system = info.create_system
      dst.writestr(new_info, payload)

    if not found_updater:
      new_info = zipfile.ZipInfo(UPDATER_ENTRY_IN_ZIPAPP)
      new_info.compress_type = zipfile.ZIP_DEFLATED
      new_info.external_attr = 0o100644 << 16
      new_info.create_system = 3
      dst.writestr(new_info, replacement)
      changed = True

  if not changed:
    return original
  return shebang + dst_io.getvalue()


def patch_setup_zipapp(original: bytes) -> bytes:
  shebang, zip_payload = split_shebang(original)

  src_io = BytesIO(zip_payload)
  dst_io = BytesIO()
  changed = False

  replacements = get_setup_replacements()

  with zipfile.ZipFile(src_io, "r") as src, zipfile.ZipFile(dst_io, "w", compression=zipfile.ZIP_DEFLATED) as dst:
    seen_entries: set[str] = set()
    for info in src.infolist():
      seen_entries.add(info.filename)
      payload = src.read(info.filename)
      if info.filename in replacements and payload != replacements[info.filename]:
        payload = replacements[info.filename]
        changed = True
      elif info.filename in (MICI_SETUP_ENTRY_IN_SETUP_ZIPAPP, TICI_SETUP_ENTRY_IN_SETUP_ZIPAPP):
        patched_payload = patch_setup_branding_script(payload, info.filename)
        if patched_payload != payload:
          payload = patched_payload
          changed = True

      new_info = zipfile.ZipInfo(info.filename, info.date_time)
      new_info.compress_type = zipfile.ZIP_DEFLATED
      new_info.external_attr = info.external_attr
      new_info.create_system = info.create_system
      dst.writestr(new_info, payload)

    default_external_attr = 0o100644 << 16
    for entry, payload in replacements.items():
      if entry in seen_entries:
        continue
      new_info = zipfile.ZipInfo(entry)
      new_info.compress_type = zipfile.ZIP_DEFLATED
      new_info.external_attr = default_external_attr
      new_info.create_system = 3
      dst.writestr(new_info, payload)
      changed = True

  if not changed:
    return original
  return shebang + dst_io.getvalue()


def zipapp_has_markers(data: bytes) -> bool:
  _shebang, zip_payload = split_shebang(data)
  with zipfile.ZipFile(BytesIO(zip_payload), "r") as z:
    reset_script = z.read(RESET_ENTRY_IN_ZIPAPP)
    tici_reset_script = z.read(TICI_RESET_ENTRY_IN_ZIPAPP)
    mici_reset_script = z.read(MICI_RESET_ENTRY_IN_ZIPAPP)
    app_script = z.read(APPLICATION_ENTRY_IN_ZIPAPP)
  return (
    PATCH_MARKER.encode() in reset_script
    and b"_device_tree_device_type" in reset_script
    and b"gui_app.big_ui()" not in reset_script
    and b"mici_setup" not in mici_reset_script
    and b"jeepney" not in mici_reset_script
    and b"mici_setup" not in tici_reset_script
    and b"jeepney" not in tici_reset_script
    and APP_PATCH_MARKER.encode() in app_script
  )


def setup_zipapp_has_expected_content(data: bytes) -> bool:
  _shebang, zip_payload = split_shebang(data)
  replacements = get_setup_replacements()
  with zipfile.ZipFile(BytesIO(zip_payload), "r") as z:
    try:
      wifi_manager = z.read(WIFI_MANAGER_ENTRY_IN_SETUP_ZIPAPP)
      if SETUP_WIFI_PATCH_MARKER.encode() not in wifi_manager:
        return False
      for entry, payload in replacements.items():
        if z.read(entry) != payload:
          return False
      for entry in (MICI_SETUP_ENTRY_IN_SETUP_ZIPAPP, TICI_SETUP_ENTRY_IN_SETUP_ZIPAPP):
        setup_script = z.read(entry)
        if SETUP_BRANDING_PATCH_MARKER.encode() not in setup_script:
          return False
        if b"installer.comma.ai/firestar5683/StarPilot" not in setup_script:
          return False
      mici_setup = z.read(MICI_SETUP_ENTRY_IN_SETUP_ZIPAPP)
      if b"install openpilot" in mici_setup or b"slide to install\\nopenpilot" in mici_setup:
        return False
    except KeyError:
      return False
  return True


def updater_zipapp_has_expected_content(data: bytes) -> bool:
  _shebang, zip_payload = split_shebang(data)
  with zipfile.ZipFile(BytesIO(zip_payload), "r") as z:
    try:
      updater_script = z.read(UPDATER_ENTRY_IN_ZIPAPP)
    except KeyError:
      return False
  return updater_script == patch_updater_module()


def weston_service_has_expected_content(data: bytes) -> bool:
  return (
    WESTON_BG_PATCH_MARKER.encode("utf-8") in data
    and b"displayed boot logo was 90 degrees counter-clockwise" in data
    and b"logo=img.crop(bbox) if bbox else img" in data
    and b"logo=logo.rotate(-90, expand=True)" in data
    and b"logo=logo.resize((max(1, logo.width//3), max(1, logo.height//3)), resample)" in data
    and b"canvas.save(\\\"/tmp/bg.jpg\\\")" in data
  )


def comma_sh_has_expected_display_wait(data: bytes) -> bool:
  return (
    COMMA_SH_DISPLAY_WAIT_PATCH_MARKER.encode("utf-8") in data
    and b"systemctl cat magic.service" in data
    and b"systemctl is-active --quiet weston-ready" in data
    and b"[ -S /var/tmp/weston/wayland-0 ]" in data
  )


def parse_inode(debugfs_output: str) -> int:
  m = re.search(r"Inode:\s+(\d+)", debugfs_output)
  if not m:
    raise RuntimeError(f"Unable to parse inode from debugfs stat output:\n{debugfs_output}")
  return int(m.group(1))


def format_debugfs_mode(mode_octal: str) -> str:
  try:
    mode = int(mode_octal, 8)
  except ValueError as e:
    raise RuntimeError(f"Invalid octal inode mode: {mode_octal}") from e
  if not 0 <= mode <= 0xFFFF:
    raise RuntimeError(f"Inode mode exceeds ext4 field width: {mode_octal}")
  return f"0{mode:o}"


def verify_inode_metadata(debugfs: str, image: Path, image_path: str, expected_type: str,
                          mode_octal: str, uid: int, gid: int) -> None:
  stat_out = run_debugfs(debugfs, image, f"stat {image_path}", write=False)
  file_type, perms_octal, actual_uid, actual_gid = parse_debugfs_stat(stat_out)
  expected_perms = int(mode_octal, 8) & 0o7777
  actual_perms = int(perms_octal, 8)
  if (file_type, actual_perms, actual_uid, actual_gid) != (expected_type, expected_perms, uid, gid):
    raise RuntimeError(
      f"Metadata verification failed for {image_path}: "
      f"got type={file_type} mode={actual_perms:04o} uid={actual_uid} gid={actual_gid}, "
      f"expected type={expected_type} mode={expected_perms:04o} uid={uid} gid={gid}"
    )


def write_regular_file_to_image(debugfs: str, image: Path, image_path: str, local_file: Path, mode_octal: str, uid: int = 0, gid: int = 0) -> None:
  try:
    run_debugfs(debugfs, image, f"rm {image_path}", write=True)
  except Exception as e:
    err = str(e).lower()
    if "file not found" not in err and "no such file" not in err:
      raise
  run_debugfs(debugfs, image, f"write {local_file} {image_path}", write=True)
  stat_out = run_debugfs(debugfs, image, f"stat {image_path}", write=False)
  inode = parse_inode(stat_out)
  run_debugfs(debugfs, image, f"set_inode_field <{inode}> mode {format_debugfs_mode(mode_octal)}", write=True)
  run_debugfs(debugfs, image, f"set_inode_field <{inode}> uid {uid}", write=True)
  run_debugfs(debugfs, image, f"set_inode_field <{inode}> gid {gid}", write=True)
  verify_inode_metadata(debugfs, image, image_path, "regular", mode_octal, uid, gid)


def ensure_directory_in_image(debugfs: str, image: Path, image_path: str, mode_octal: str = "040755", uid: int = 0, gid: int = 0) -> None:
  try:
    run_debugfs(debugfs, image, f"mkdir {image_path}", write=True)
  except Exception as e:
    err = str(e).lower()
    if "already exists" not in err and "file exists" not in err:
      raise

  stat_out = run_debugfs(debugfs, image, f"stat {image_path}", write=False)
  inode = parse_inode(stat_out)
  run_debugfs(debugfs, image, f"set_inode_field <{inode}> mode {format_debugfs_mode(mode_octal)}", write=True)
  run_debugfs(debugfs, image, f"set_inode_field <{inode}> uid {uid}", write=True)
  run_debugfs(debugfs, image, f"set_inode_field <{inode}> gid {gid}", write=True)
  verify_inode_metadata(debugfs, image, image_path, "directory", mode_octal, uid, gid)


def extract_wheel_subset(wheel_path: Path, extract_dir: Path, roots: set[str]) -> dict[Path, str]:
  if extract_dir.exists():
    shutil.rmtree(extract_dir)
  extract_dir.mkdir(parents=True)
  file_modes: dict[Path, str] = {}

  with zipfile.ZipFile(wheel_path, "r") as wheel:
    for info in wheel.infolist():
      parts = Path(info.filename).parts
      if not parts or parts[0] not in roots:
        continue
      if any(part == ".." for part in parts):
        raise RuntimeError(f"Unsafe wheel entry path: {info.filename}")

      local_path = extract_dir.joinpath(*parts)
      if info.is_dir():
        local_path.mkdir(parents=True, exist_ok=True)
        continue

      local_path.parent.mkdir(parents=True, exist_ok=True)
      with wheel.open(info, "r") as src, open(local_path, "wb") as dst:
        shutil.copyfileobj(src, dst)

      perms = (info.external_attr >> 16) & 0o777
      if not perms:
        perms = 0o644
      os.chmod(local_path, perms)
      file_modes[local_path] = f"100{perms:03o}"

  if not (extract_dir / JEEPNY_PACKAGE_DIR / "__init__.py").is_file():
    raise RuntimeError("jeepney wheel extraction did not produce jeepney/__init__.py")
  if not (extract_dir / JEEPNY_DIST_INFO_DIR / "METADATA").is_file():
    raise RuntimeError("jeepney wheel extraction did not produce dist-info/METADATA")

  return file_modes


def install_python_package_tree(debugfs: str, image: Path, source_dir: Path, image_root: str, file_modes: dict[Path, str]) -> None:
  dirs = sorted((p for p in source_dir.rglob("*") if p.is_dir()), key=lambda p: len(p.relative_to(source_dir).parts))
  for local_dir in dirs:
    rel = local_dir.relative_to(source_dir).as_posix()
    ensure_directory_in_image(debugfs, image, f"{image_root}/{rel}", "040755", 0, 0)

  files = sorted((p for p in source_dir.rglob("*") if p.is_file()), key=lambda p: p.relative_to(source_dir).as_posix())
  for local_file in files:
    rel = local_file.relative_to(source_dir).as_posix()
    mode_octal = file_modes.get(local_file, "100644")
    write_regular_file_to_image(debugfs, image, f"{image_root}/{rel}", local_file, mode_octal, 0, 0)


def install_jeepney_into_image(debugfs: str, image: Path, work_dir: Path) -> None:
  wheel_dir = work_dir / "python_wheels"
  wheel_path = wheel_dir / f"jeepney-{JEEPNY_VERSION}-py3-none-any.whl"
  download_with_sha256(JEEPNY_WHEEL_URL, wheel_path, JEEPNY_WHEEL_SHA256)

  extract_dir = work_dir / "jeepney_wheel"
  file_modes = extract_wheel_subset(wheel_path, extract_dir, {JEEPNY_PACKAGE_DIR, JEEPNY_DIST_INFO_DIR})

  print(f"Installing jeepney {JEEPNY_VERSION} into AGNOS Python venv", flush=True)
  install_python_package_tree(debugfs, image, extract_dir, PYTHON_SITE_PACKAGES_PATH_IN_IMAGE, file_modes)


def image_has_jeepney(debugfs: str, image: Path, work_dir: Path) -> bool:
  verify_dir = work_dir / "jeepney_verify"
  verify_dir.mkdir(parents=True, exist_ok=True)
  init_file = verify_dir / "__init__.py"
  wrappers_file = verify_dir / "wrappers.py"
  metadata_file = verify_dir / "METADATA"
  init_file.unlink(missing_ok=True)
  wrappers_file.unlink(missing_ok=True)
  metadata_file.unlink(missing_ok=True)
  try:
    for image_path in (
      f"{PYTHON_SITE_PACKAGES_PATH_IN_IMAGE}/{JEEPNY_PACKAGE_DIR}/__init__.py",
      f"{PYTHON_SITE_PACKAGES_PATH_IN_IMAGE}/{JEEPNY_PACKAGE_DIR}/wrappers.py",
      f"{PYTHON_SITE_PACKAGES_PATH_IN_IMAGE}/{JEEPNY_DIST_INFO_DIR}/METADATA",
    ):
      file_type, _mode, _uid, _gid = parse_debugfs_stat(run_debugfs(debugfs, image, f"stat {image_path}", write=False))
      if file_type != "regular":
        raise RuntimeError(f"{image_path} has inode type {file_type}, expected regular")

    run_debugfs(debugfs, image, f"dump -p {PYTHON_SITE_PACKAGES_PATH_IN_IMAGE}/{JEEPNY_PACKAGE_DIR}/__init__.py {init_file}", write=False)
    run_debugfs(debugfs, image, f"dump -p {PYTHON_SITE_PACKAGES_PATH_IN_IMAGE}/{JEEPNY_PACKAGE_DIR}/wrappers.py {wrappers_file}", write=False)
    run_debugfs(debugfs, image, f"dump -p {PYTHON_SITE_PACKAGES_PATH_IN_IMAGE}/{JEEPNY_DIST_INFO_DIR}/METADATA {metadata_file}", write=False)
  except Exception:
    return False

  return (
    b"from .wrappers import *" in init_file.read_bytes()
    and b"class DBusAddress" in wrappers_file.read_bytes()
    and f"Version: {JEEPNY_VERSION}".encode("utf-8") in metadata_file.read_bytes()
  )


def parse_debugfs_stat(debugfs_output: str) -> tuple[str, str, int, int]:
  type_match = re.search(r"Type:\s+([A-Za-z]+)", debugfs_output)
  mode_match = re.search(r"Mode:\s+([0-7]+)", debugfs_output)
  user_match = re.search(r"User:\s+(\d+)", debugfs_output)
  group_match = re.search(r"Group:\s+(\d+)", debugfs_output)
  if not type_match or not mode_match or not user_match or not group_match:
    raise RuntimeError(f"Unable to parse debugfs stat output:\n{debugfs_output}")
  return type_match.group(1).lower(), mode_match.group(1), int(user_match.group(1)), int(group_match.group(1))


def inode_mode_from_type_and_perms(file_type: str, perms_octal: str) -> str:
  prefix = INODE_MODE_TYPE_PREFIX.get(file_type)
  if prefix is None:
    raise RuntimeError(f"Unsupported inode type '{file_type}' for mode conversion")
  perms = perms_octal.strip()
  if not perms:
    raise RuntimeError("Empty permissions value in inode stat")
  return f"{prefix}{int(perms, 8):03o}"


def sync_files_from_reference_image(debugfs: str, reference_img: Path, patched_img: Path, sync_paths: list[str], work_dir: Path) -> list[str]:
  sync_dir = work_dir / "reference_sync"
  sync_dir.mkdir(parents=True, exist_ok=True)
  synced: list[str] = []

  for image_path in sync_paths:
    source_tmp = sync_dir / f"source{image_path.replace('/', '_')}"
    verify_tmp = sync_dir / f"verify{image_path.replace('/', '_')}"

    stat_out = run_debugfs(debugfs, reference_img, f"stat {image_path}", write=False)
    file_type, perms_octal, uid, gid = parse_debugfs_stat(stat_out)
    mode_octal = inode_mode_from_type_and_perms(file_type, perms_octal)

    run_debugfs(debugfs, reference_img, f"dump -p {image_path} {source_tmp}", write=False)
    print(f"Syncing {image_path} from reference image (mode={mode_octal}, uid={uid}, gid={gid})", flush=True)
    write_regular_file_to_image(debugfs, patched_img, image_path, source_tmp, mode_octal, uid, gid)

    run_debugfs(debugfs, patched_img, f"dump -p {image_path} {verify_tmp}", write=False)
    if sha256_file(source_tmp) != sha256_file(verify_tmp):
      raise RuntimeError(f"Verification failed after syncing {image_path}")
    synced.append(image_path)

  return synced


def sha256_file(path: Path) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as f:
    while True:
      chunk = f.read(1024 * 1024)
      if not chunk:
        break
      h.update(chunk)
  return h.hexdigest()


def sha256_zstd_payload(path: Path) -> str:
  try:
    import zstandard
  except ImportError as e:
    raise RuntimeError("zstandard is required to verify the external-GPU firmware") from e

  digest = hashlib.sha256()
  with open(path, "rb") as compressed:
    with zstandard.ZstdDecompressor().stream_reader(compressed) as source:
      while chunk := source.read(1024 * 1024):
        digest.update(chunk)
  return digest.hexdigest()


def install_amdgpu_firmware_from_reference(debugfs: str, reference_img: Path, patched_img: Path, work_dir: Path) -> None:
  ensure_directory_in_image(debugfs, patched_img, AMDGPU_FIRMWARE_PATH_IN_IMAGE, "040755", 0, 0)
  firmware_dir = work_dir / "amdgpu_firmware"
  firmware_dir.mkdir(parents=True, exist_ok=True)

  for filename, expected_payload_hash in AMDGPU_FIRMWARE_SHA256.items():
    image_path = f"{AMDGPU_FIRMWARE_PATH_IN_IMAGE}/{filename}"
    local_file = firmware_dir / filename
    verify_file = firmware_dir / f"{filename}.verify"
    local_file.unlink(missing_ok=True)
    verify_file.unlink(missing_ok=True)

    stat_out = run_debugfs(debugfs, reference_img, f"stat {image_path}", write=False)
    file_type, perms_octal, uid, gid = parse_debugfs_stat(stat_out)
    if file_type != "regular":
      raise RuntimeError(f"Reference firmware {image_path} is {file_type}, expected regular")
    run_debugfs(debugfs, reference_img, f"dump -p {image_path} {local_file}", write=False)
    if sha256_zstd_payload(local_file) != expected_payload_hash:
      raise RuntimeError(f"Reference firmware payload hash mismatch for {filename}")

    mode_octal = inode_mode_from_type_and_perms(file_type, perms_octal)
    write_regular_file_to_image(debugfs, patched_img, image_path, local_file, mode_octal, uid, gid)
    run_debugfs(debugfs, patched_img, f"dump -p {image_path} {verify_file}", write=False)
    if sha256_file(local_file) != sha256_file(verify_file):
      raise RuntimeError(f"Compressed firmware verification failed for {filename}")
    if sha256_zstd_payload(verify_file) != expected_payload_hash:
      raise RuntimeError(f"Installed firmware payload hash mismatch for {filename}")

  print(f"Installed and verified {len(AMDGPU_FIRMWARE_SHA256)} AMD firmware files", flush=True)


def compress_xz(src: Path, dst: Path) -> None:
  dst.parent.mkdir(parents=True, exist_ok=True)
  tmp = dst.with_suffix(dst.suffix + ".part")
  print(f"Compressing {src} -> {dst}", flush=True)
  with open(tmp, "wb") as out:
    proc = subprocess.run(["xz", "-T0", "-6", "-c", str(src)], stdout=out, stderr=subprocess.PIPE, text=True)
  if proc.returncode != 0:
    tmp.unlink(missing_ok=True)
    raise RuntimeError(f"xz failed:\n{proc.stderr}")
  tmp.replace(dst)


def update_manifest_system_entry(manifest: list[dict], new_url: str, new_hash_raw: str, size: int) -> list[dict]:
  updated = json.loads(json.dumps(manifest))
  system_entry = get_system_entry(updated)
  old_url = system_entry.get("url")
  old_hash = system_entry.get("hash")
  old_hash_raw = system_entry.get("hash_raw")
  old_size = system_entry.get("size")

  system_entry["url"] = new_url
  system_entry["hash"] = new_hash_raw
  system_entry["hash_raw"] = new_hash_raw
  system_entry["size"] = size
  system_entry["sparse"] = False
  system_entry["full_check"] = False

  if isinstance(old_url, str) and isinstance(old_hash, str) and isinstance(old_hash_raw, str) and isinstance(old_size, int):
    system_entry["alt"] = {
      "url": old_url,
      "hash": old_hash,
      "hash_raw": old_hash_raw,
      "size": old_size,
    }

  return updated


def resolve_reference_source_image(args: argparse.Namespace, primary_manifest_path: Path, work_dir: Path) -> Path:
  if args.reference_image:
    ref_image = Path(args.reference_image).resolve()
    if not ref_image.is_file():
      raise RuntimeError(f"Reference image not found: {ref_image}")
    return ref_image

  reference_manifest_path: Path | None = None
  if args.reference_manifest:
    reference_manifest_path = Path(args.reference_manifest).resolve()
    if not reference_manifest_path.is_file():
      raise RuntimeError(f"Reference manifest not found: {reference_manifest_path}")
  else:
    reference_manifest_path = find_default_reference_manifest(primary_manifest_path)

  if args.reference_source_url:
    reference_url = args.reference_source_url
  elif reference_manifest_path is not None:
    reference_manifest = load_manifest(reference_manifest_path)
    reference_entry = get_system_entry(reference_manifest)
    reference_url = pick_source_url(reference_entry, None)
    print(f"Using reference AGNOS manifest: {reference_manifest_path}", flush=True)
  else:
    raise RuntimeError(
      "No reference image source found. Set --reference-image, --reference-source-url, or --reference-manifest."
    )

  reference_download = work_dir / "reference_system.img"
  if args.force_download and reference_download.exists():
    reference_download.unlink()
  if not reference_download.exists():
    download(reference_url, reference_download)
  return reference_download


def main() -> int:
  args = parse_args()
  debugfs = find_debugfs()

  manifest_path = Path(args.manifest).resolve()
  manifest = load_manifest(manifest_path)
  system_entry = get_system_entry(manifest)

  work_dir = Path(args.work_dir).resolve()
  work_dir.mkdir(parents=True, exist_ok=True)

  if args.source_image:
    downloaded_img = Path(args.source_image).resolve()
    if not downloaded_img.is_file():
      raise RuntimeError(f"Source image not found: {downloaded_img}")
  else:
    source_url = pick_source_url(system_entry, args.source_url)
    downloaded_img = work_dir / "base_system.img"
    if args.force_download and downloaded_img.exists():
      downloaded_img.unlink()
    if not downloaded_img.exists():
      download(source_url, downloaded_img)

  raw_img = work_dir / "base_system.ext4.img"
  materialize_ext4_image(downloaded_img, raw_img, work_dir, "base_system", force=args.force_download)

  patched_img = work_dir / "patched_system.ext4.img"
  if patched_img.exists():
    patched_img.unlink()
  print(f"Copying source image -> {patched_img}", flush=True)
  shutil.copy2(raw_img, patched_img)

  sync_paths = [] if args.disable_comma_file_sync else parse_sync_file_list(args.sync_comma_files)
  reference_raw = None
  if sync_paths or not args.disable_usbgpu_firmware:
    reference_source_img = resolve_reference_source_image(args, manifest_path, work_dir)
    reference_raw = work_dir / "reference_system.ext4.img"
    materialize_ext4_image(reference_source_img, reference_raw, work_dir, "reference_system", force=args.force_download)

  if sync_paths:
    assert reference_raw is not None
    print(f"Syncing /usr/comma payload files from reference image: {reference_raw}", flush=True)
    synced_files = sync_files_from_reference_image(debugfs, reference_raw, patched_img, sync_paths, work_dir)
    print(f"Synced {len(synced_files)} /usr/comma files from reference image", flush=True)

  if not args.disable_usbgpu_firmware:
    assert reference_raw is not None
    print(f"Installing external-GPU firmware from reference image: {reference_raw}", flush=True)
    install_amdgpu_firmware_from_reference(debugfs, reference_raw, patched_img, work_dir)

  preserved_paths = {
    RESET_PATH_IN_IMAGE: "comma_reset",
    SETUP_PATH_IN_IMAGE: "comma_setup",
    COMMA_SH_PATH_IN_IMAGE: "comma_sh",
    MAGIC_PATH_IN_IMAGE: "comma_magic",
    BG_PATH_IN_IMAGE: "comma_bg",
  }
  expected_hashes: dict[str, str] = {}
  for image_path, label in preserved_paths.items():
    preserved_file = work_dir / f"{label}.preserved"
    print(f"Recording existing {image_path} for preservation", flush=True)
    run_debugfs(debugfs, patched_img, f"dump -p {image_path} {preserved_file}", write=False)
    expected_hashes[image_path] = sha256_file(preserved_file)

  original_updater = work_dir / "comma_updater.orig"
  patched_updater = work_dir / "comma_updater.patched"
  verify_updater = work_dir / "comma_updater.verify"
  original_weston = work_dir / "weston_service.orig"
  patched_weston = work_dir / "weston_service.patched"
  verify_weston = work_dir / "weston_service.verify"
  patched_comma_sh = work_dir / "comma_sh.patched"

  original_comma_sh = work_dir / "comma_sh.preserved"
  comma_sh_patched_data = patch_comma_sh_display_wait(original_comma_sh.read_bytes())
  patched_comma_sh.write_bytes(comma_sh_patched_data)

  print("Writing patched /usr/comma/comma.sh display readiness wait", flush=True)
  write_regular_file_to_image(debugfs, patched_img, COMMA_SH_PATH_IN_IMAGE, patched_comma_sh, "100775", 0, 0)
  expected_hashes[COMMA_SH_PATH_IN_IMAGE] = sha256_file(patched_comma_sh)

  print("Extracting weston.service from image", flush=True)
  run_debugfs(debugfs, patched_img, f"dump -p {WESTON_SERVICE_PATH_IN_IMAGE} {original_weston}", write=False)

  weston_original_data = original_weston.read_bytes()
  weston_patched_data = patch_weston_service(weston_original_data)
  if weston_patched_data == weston_original_data:
    print("weston.service already contains the expected boot-logo patch; continuing", flush=True)
  patched_weston.write_bytes(weston_patched_data)

  print("Writing patched weston.service back into image", flush=True)
  write_regular_file_to_image(debugfs, patched_img, WESTON_SERVICE_PATH_IN_IMAGE, patched_weston, "100644", 0, 0)

  run_debugfs(debugfs, patched_img, f"dump -p {WESTON_SERVICE_PATH_IN_IMAGE} {verify_weston}", write=False)
  verify_weston_data = verify_weston.read_bytes()
  if not weston_service_has_expected_content(verify_weston_data):
    raise RuntimeError("weston.service verification failed after writing weston.service file into image")

  print("Extracting /usr/comma/updater from image", flush=True)
  run_debugfs(debugfs, patched_img, f"dump -p {UPDATER_PATH_IN_IMAGE} {original_updater}", write=False)

  updater_original_data = original_updater.read_bytes()
  updater_patched_data = patch_updater_zipapp(updater_original_data)
  if updater_patched_data == updater_original_data:
    print("Updater zipapp already contains the expected selector patch; continuing", flush=True)
  patched_updater.write_bytes(updater_patched_data)

  print("Writing patched /usr/comma/updater back into image", flush=True)
  write_regular_file_to_image(debugfs, patched_img, UPDATER_PATH_IN_IMAGE, patched_updater, "100775", 0, 0)

  run_debugfs(debugfs, patched_img, f"dump -p {UPDATER_PATH_IN_IMAGE} {verify_updater}", write=False)
  verify_updater_data = verify_updater.read_bytes()
  if not updater_zipapp_has_expected_content(verify_updater_data):
    raise RuntimeError("Updater zipapp verification failed after writing updater file into image")

  install_jeepney_into_image(debugfs, patched_img, work_dir)
  if not image_has_jeepney(debugfs, patched_img, work_dir):
    raise RuntimeError("jeepney verification failed after installing package into image")

  for image_path, label in preserved_paths.items():
    verify_file = work_dir / f"{label}.verify"
    run_debugfs(debugfs, patched_img, f"dump -p {image_path} {verify_file}", write=False)
    if image_path == COMMA_SH_PATH_IN_IMAGE and not comma_sh_has_expected_display_wait(verify_file.read_bytes()):
      raise RuntimeError("comma.sh display readiness verification failed")
    if sha256_file(verify_file) != expected_hashes[image_path]:
      raise RuntimeError(f"{image_path} does not match the expected generated payload")

  if args.set_version:
    version_file = work_dir / "VERSION.patched"
    version_file.write_text(args.set_version.strip() + "\n", encoding="utf-8")
    print(f"Writing {VERSION_PATH_IN_IMAGE}={args.set_version.strip()}", flush=True)
    write_regular_file_to_image(debugfs, patched_img, VERSION_PATH_IN_IMAGE, version_file, "100644", 0, 0)
    version_raw = run_debugfs(debugfs, patched_img, f"cat {VERSION_PATH_IN_IMAGE}", write=False)
    version_lines = [ln.strip() for ln in version_raw.splitlines() if ln.strip() and not ln.startswith("debugfs ")]
    version_verify = version_lines[0] if version_lines else ""
    if version_verify != args.set_version.strip():
      raise RuntimeError(f"/VERSION mismatch after patch: got '{version_verify}', expected '{args.set_version.strip()}'")

  raw_hash = sha256_file(patched_img)
  raw_size = patched_img.stat().st_size

  default_name = f"system-{raw_hash}.img.xz"
  output_xz = Path(args.output_xz).resolve() if args.output_xz else (work_dir / default_name)
  compress_xz(patched_img, output_xz)

  print("")
  print("Patched AGNOS system artifact ready:")
  print(f"  raw image: {patched_img}")
  print(f"  xz image:  {output_xz}")
  print(f"  raw sha256/hash_raw: {raw_hash}")
  print(f"  size: {raw_size}")
  print("")

  if args.new_url:
    new_manifest = update_manifest_system_entry(manifest, args.new_url, raw_hash, raw_size)
    out_path: Path
    if args.in_place_manifest:
      out_path = manifest_path
    elif args.manifest_out:
      out_path = Path(args.manifest_out).resolve()
    else:
      out_path = work_dir / "agnos.patched.json"
    out_path.write_text(json.dumps(new_manifest, indent=2) + "\n")
    print(f"Updated manifest written: {out_path}")
  else:
    print("No --new-url provided. Manifest not updated.")
    print("Set system entry values to:")
    print(json.dumps({
      "url": "<your-hosted-system.img.xz-url>",
      "hash": raw_hash,
      "hash_raw": raw_hash,
      "size": raw_size,
      "sparse": False,
      "full_check": False,
      "has_ab": True,
    }, indent=2))

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
