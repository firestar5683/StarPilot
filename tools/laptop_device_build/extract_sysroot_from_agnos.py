#!/usr/bin/env python3

import argparse
import json
import lzma
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path


REQUIRED_DIRS = [
  ("usr/local/lib", "/usr/local/lib"),
  ("usr/local/include", "/usr/local/include"),
  ("usr/local/venv/lib/python3.12/site-packages/raylib/install", "/usr/local/venv/lib/python3.12/site-packages/raylib/install"),
  ("lib/aarch64-linux-gnu", "/lib/aarch64-linux-gnu"),
  ("usr/lib/aarch64-linux-gnu", "/usr/lib/aarch64-linux-gnu"),
  ("usr/include", "/usr/include"),
]
VENDOR_CANDIDATES = ["/system/vendor/lib64", "/vendor/lib64"]
OPTIONAL_INCLUDE_DIRS: list[str] = []
DEBUGFS_NOT_FOUND_MARKERS = (
  "file not found by ext2_lookup",
  "while trying to resolve filename",
  "couldn't allocate",
  "no such file",
  "not found",
)
ANDROID_SPARSE_MAGIC = 0xED26FF3A


def parse_args() -> argparse.Namespace:
  p = argparse.ArgumentParser(description="Extract TICI sysroot dirs from AGNOS system image")
  p.add_argument("--manifest", default="system/hardware/tici/agnos.json", help="Path to AGNOS manifest JSON")
  p.add_argument("--output-dir", required=True, help="Destination sysroot directory")
  p.add_argument("--cache-dir", default=".cache/agnos", help="Cache directory for downloaded images")
  p.add_argument("--url", default=None, help="Override AGNOS system image URL")
  p.add_argument("--force-download", action="store_true", help="Redownload system image even if cached")
  return p.parse_args()


def get_system_url(manifest_path: Path) -> str:
  data = json.loads(manifest_path.read_text())
  for entry in data:
    if entry.get("name") != "system":
      continue
    if isinstance(entry.get("url"), str):
      return entry["url"]
    alt = entry.get("alt") if isinstance(entry, dict) else None
    if isinstance(alt, dict) and isinstance(alt.get("url"), str):
      return alt["url"]
  raise RuntimeError(f"No system entry in manifest: {manifest_path}")


def download(url: str, dst: Path) -> None:
  dst.parent.mkdir(parents=True, exist_ok=True)
  tmp = dst.with_suffix(dst.suffix + ".part")
  print(f"Downloading {url} -> {dst}", flush=True)
  with urllib.request.urlopen(url) as src, open(tmp, "wb") as out:
    shutil.copyfileobj(src, out, length=1024 * 1024)
  tmp.replace(dst)


def download_and_prepare_image(url: str, cache_dir: Path, force_download: bool) -> Path:
  cache_dir.mkdir(parents=True, exist_ok=True)
  compressed = cache_dir / "agnos_system.img.xz"
  raw_image = cache_dir / "agnos_system.img"
  ext4_image = cache_dir / "agnos_system.ext4.img"

  if force_download:
    compressed.unlink(missing_ok=True)
    raw_image.unlink(missing_ok=True)
    ext4_image.unlink(missing_ok=True)

  # Prefer an already-cached raw image to avoid unnecessary multi-GB downloads.
  if raw_image.exists():
    return raw_image

  parsed_url = urllib.parse.urlparse(url)
  if parsed_url.path.endswith(".xz"):
    if not compressed.exists():
      download(url, compressed)
    if not raw_image.exists():
      print(f"Decompressing {compressed} -> {raw_image}", flush=True)
      with lzma.open(compressed, "rb") as f_in, open(raw_image, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out, length=1024 * 1024)
  else:
    if not raw_image.exists():
      download(url, raw_image)

  return raw_image


def is_android_sparse(image_path: Path) -> bool:
  with open(image_path, "rb") as f:
    header = f.read(4)
  if len(header) != 4:
    return False
  magic = int.from_bytes(header, "little")
  return magic == ANDROID_SPARSE_MAGIC


def ensure_debugfs_readable_image(image_path: Path, cache_dir: Path) -> Path:
  if not is_android_sparse(image_path):
    return image_path

  if shutil.which("simg2img") is None:
    raise RuntimeError(
      f"{image_path} is an Android sparse image, but simg2img is not installed."
    )

  converted = cache_dir / "agnos_system.ext4.img"
  needs_convert = not converted.exists()
  if converted.exists():
    needs_convert = os.path.getmtime(converted) < os.path.getmtime(image_path)

  if needs_convert:
    print(f"Converting sparse image {image_path} -> {converted}", flush=True)
    proc = subprocess.run(["simg2img", str(image_path), str(converted)], capture_output=True, text=True)
    if proc.returncode != 0:
      raise RuntimeError(f"simg2img failed:\n{proc.stdout}\n{proc.stderr}")
  return converted


def _has_content(path: Path) -> bool:
  if not path.exists():
    return False
  if path.is_file():
    return path.stat().st_size > 0
  return any(path.iterdir())


def _pick_extracted_root(tmp_path: Path, src_path: str) -> Path | None:
  rel = Path(src_path.lstrip("/"))
  candidates = [
    tmp_path / rel,
    tmp_path / rel.name,
    tmp_path,
  ]
  for c in candidates:
    if _has_content(c):
      return c
  return None


def run_debugfs(image_path: Path, src_path: str, dst_path: Path) -> None:
  attempts: list[str] = []
  for candidate_src in (src_path, src_path.lstrip("/")):
    if not candidate_src:
      continue
    with tempfile.TemporaryDirectory(prefix="sysroot_extract_") as tmp:
      tmp_path = Path(tmp)
      cmd = ["debugfs", "-R", f"rdump {candidate_src} {tmp_path}", str(image_path)]
      proc = subprocess.run(cmd, capture_output=True, text=True)
      out = f"{proc.stdout}\n{proc.stderr}".lower()
      attempts.append(f"{' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")

      if proc.returncode != 0:
        continue
      if any(marker in out for marker in DEBUGFS_NOT_FOUND_MARKERS):
        continue

      source_to_copy = _pick_extracted_root(tmp_path, candidate_src)
      if source_to_copy is None:
        continue

      if dst_path.exists():
        shutil.rmtree(dst_path)
      dst_path.parent.mkdir(parents=True, exist_ok=True)
      shutil.copytree(source_to_copy, dst_path, symlinks=True, dirs_exist_ok=True)
      return

  joined_attempts = "\n---\n".join(attempts)
  raise RuntimeError(f"debugfs could not extract '{src_path}'. Attempts:\n{joined_attempts}")


def is_non_empty_dir(path: Path) -> bool:
  return path.is_dir() and any(path.iterdir())


def populate_optional_host_includes(output_dir: Path) -> None:
  dst_root = output_dir / "usr/include"
  if not dst_root.exists():
    return

  include_roots = [
    Path("/usr/include/aarch64-linux-gnu"),
    Path("/usr/include"),
    Path("/usr/include/x86_64-linux-gnu"),
  ]

  for include_dir in OPTIONAL_INCLUDE_DIRS:
    dst = dst_root / include_dir
    if dst.exists():
      continue
    for root in include_roots:
      src = root / include_dir
      if not src.is_dir():
        continue
      shutil.copytree(src, dst, symlinks=True)
      break

  openssl_dst = dst_root / "openssl"
  for src_dir in (
    Path("/usr/include/aarch64-linux-gnu/openssl"),
    Path("/usr/include/x86_64-linux-gnu/openssl"),
  ):
    if not src_dir.is_dir():
      continue
    openssl_dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, openssl_dst, symlinks=True, dirs_exist_ok=True)
    break


def main() -> int:
  args = parse_args()
  if shutil.which("debugfs") is None:
    raise RuntimeError("debugfs is required (install e2fsprogs)")

  manifest_path = Path(args.manifest).resolve()
  output_dir = Path(args.output_dir).resolve()
  cache_dir = Path(args.cache_dir).resolve()
  output_dir.mkdir(parents=True, exist_ok=True)

  url = args.url or get_system_url(manifest_path)
  image_path = download_and_prepare_image(url, cache_dir, args.force_download)
  image_path = ensure_debugfs_readable_image(image_path, cache_dir)

  for rel_dst, src_path in REQUIRED_DIRS:
    dst = output_dir / rel_dst
    print(f"Extracting {src_path} -> {dst}", flush=True)
    run_debugfs(image_path, src_path, dst)

  vendor_ok = False
  vendor_dst = output_dir / "system/vendor/lib64"
  for src_path in VENDOR_CANDIDATES:
    try:
      print(f"Extracting {src_path} -> {vendor_dst}", flush=True)
      run_debugfs(image_path, src_path, vendor_dst)
      vendor_ok = True
      break
    except RuntimeError:
      continue

  if not vendor_ok:
    print(
      "WARN: vendor libs not found in AGNOS image at /system/vendor/lib64 or /vendor/lib64; "
      "falling back to usr/lib/aarch64-linux-gnu",
      flush=True,
    )
    if vendor_dst.is_symlink() or vendor_dst.is_file():
      vendor_dst.unlink()
    elif vendor_dst.exists():
      shutil.rmtree(vendor_dst)
    vendor_dst.parent.mkdir(parents=True, exist_ok=True)
    os.symlink("../../usr/lib/aarch64-linux-gnu", vendor_dst, target_is_directory=True)

  populate_optional_host_includes(output_dir)

  missing = []
  for rel in ("usr/local/lib", "usr/local/include", "lib/aarch64-linux-gnu", "usr/lib/aarch64-linux-gnu", "usr/include", "system/vendor/lib64"):
    if not is_non_empty_dir(output_dir / rel):
      missing.append(rel)
  if missing:
    raise RuntimeError(f"Extracted sysroot is incomplete, missing content in: {', '.join(missing)}")

  print(f"Sysroot ready: {output_dir}", flush=True)
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except KeyboardInterrupt:
    raise
  except Exception as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    raise SystemExit(1)
