"""Fixed, opt-in manager ownership for the diagnostic Mapd shadow process."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

from opendbc.car.structs import car
from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.system.manager.process import NativeProcess
from openpilot.starpilot.maps.artifact import elf_arm64_static_file, source_digest
from openpilot.starpilot.maps.storage import STORAGE_ANCHOR, offline_root as map_offline_root


PROVIDER_DIR = Path(BASEDIR) / 'openpilot/starpilot/maps/provider'
PROVIDER_BINARY = PROVIDER_DIR / 'mapd'
PROVIDER_MANIFEST = PROVIDER_DIR / 'manifest.json'
OFFLINE_ROOT = map_offline_root()
OPT_IN_KEY = 'MapdShadowEnabled'
MAX_MANIFEST_BYTES = 4096
MAX_SELECTOR_BYTES = 256
MAX_RECEIPT_BYTES = 16 << 20


def _open_regular(path: Path, *, max_bytes: int | None = None, executable: bool = False):
  descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
  try:
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or (max_bytes is not None and info.st_size > max_bytes) or (executable and not info.st_mode & 0o111):
      raise ValueError('not an acceptable regular file')
    return os.fdopen(descriptor, 'rb')
  except Exception:
    os.close(descriptor)
    raise


def _owned_package(binary: Path, manifest: Path, package_dir: Path, checkout_root: Path) -> bool:
  if binary != package_dir / 'mapd' or manifest != package_dir / 'manifest.json':
    return False
  try:
    relative = package_dir.relative_to(checkout_root)
  except ValueError:
    return False
  current = checkout_root
  for part in ('.', *relative.parts):
    if part != '.':
      current = current / part
    try:
      if not stat.S_ISDIR(current.lstat().st_mode):
        return False
    except OSError:
      return False
  return True


def _owned_root(root: Path, anchor: Path) -> bool:
  if root != map_offline_root(anchor):
    return False
  for path in (anchor, root.parent.parent, root.parent, root):
    try:
      if not stat.S_ISDIR(path.lstat().st_mode):
        return False
    except OSError:
      return False
  return True


def _unique_object(pairs):
  result = {}
  for name, value in pairs:
    if name in result:
      raise ValueError('duplicate snapshot JSON field')
    result[name] = value
  return result


def _invalid_json_constant(_value):
  raise ValueError('nonfinite snapshot JSON number')


def _selected_snapshot(root: Path) -> bool:
  """Check bounded receipt identity; Go checks each requested tile lazily."""
  try:
    with _open_regular(root / 'current.json', max_bytes=MAX_SELECTOR_BYTES) as file:
      selector = json.loads(file.read(MAX_SELECTOR_BYTES + 1), object_pairs_hook=_unique_object,
                            parse_constant=_invalid_json_constant)
    if (type(selector) is not dict or set(selector) != {'version', 'generation'} or
        type(selector['version']) is not int or selector['version'] != 1 or
        type(selector['generation']) is not str or re.fullmatch(r'[0-9a-f]{64}', selector['generation']) is None):
      return False
    generations = root / 'generations'
    generation = generations / selector['generation']
    if not stat.S_ISDIR(generations.lstat().st_mode) or not stat.S_ISDIR(generation.lstat().st_mode):
      return False
    with _open_regular(generation / 'receipt.json', max_bytes=MAX_RECEIPT_BYTES) as file:
      raw = file.read(MAX_RECEIPT_BYTES + 1)
    if hashlib.sha256(raw).hexdigest() != selector['generation']:
      return False
    receipt = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_invalid_json_constant)
    if (type(receipt) is not dict or receipt.get('version') != 1 or type(receipt.get('version')) is not int or
        receipt.get('tileSchema') != 'offline.capnp:0xda3a0d9284ca402f' or
        receipt.get('attribution') != '© OpenStreetMap contributors; https://www.openstreetmap.org/copyright (ODbL)' or
        receipt.get('sourceVerified') is not False or
        receipt.get('sourceKind') not in ('local-pbf', 'provided-group-archives') or
        type(receipt.get('tiles')) is not list or not 0 < len(receipt['tiles']) <= 65536 or
        type(receipt.get('inputs')) is not list or not receipt['inputs']):
      return False
    return True
  except (OSError, ValueError, TypeError, OverflowError, RecursionError):
    return False


def preflight(binary: Path = PROVIDER_BINARY, manifest_path: Path = PROVIDER_MANIFEST,
              offline_root: Path = OFFLINE_ROOT, source: Path | None = None,
              storage_anchor: Path = STORAGE_ANCHOR, package_dir: Path = PROVIDER_DIR,
              checkout_root: Path = Path(BASEDIR)) -> bool:
  """Verify the fixed packaged artifact and an existing, non-legacy tile root."""
  source = source or Path(BASEDIR) / 'mapd_repo'
  try:
    if (not _owned_root(offline_root, storage_anchor) or not _selected_snapshot(offline_root) or
        not _owned_package(binary, manifest_path, package_dir, checkout_root)):
      return False
    with _open_regular(manifest_path, max_bytes=MAX_MANIFEST_BYTES) as file:
      manifest = json.loads(file.read(MAX_MANIFEST_BYTES + 1))
    if (not isinstance(manifest, dict) or type(manifest.get('schemaVersion')) is not int or manifest['schemaVersion'] != 1 or
        manifest.get('goVersion') != 'go1.25.1' or manifest.get('target') != 'linux-arm64-static'):
      return False
    for name, pattern in (('sourceRevision', r'[0-9a-f]{40}'), ('upstreamRevision', r'[0-9a-f]{40}'),
                          ('sourceDigest', r'[0-9a-f]{64}'), ('binarySha256', r'[0-9a-f]{64}')):
      value = manifest.get(name)
      if type(value) is not str or re.fullmatch(pattern, value) is None:
        return False
    if manifest.get('sourceDigest') != source_digest(source):
      return False
    pinned = json.loads((Path(BASEDIR) / 'upstream-sync.json').read_text())
    revision = next(item['commit'] for item in pinned['dependencies'] if item['path'] == 'mapd_repo')
    if manifest.get('upstreamRevision') != revision:
      return False
    digest = hashlib.sha256()
    stamps = {manifest['sourceDigest'].encode(), revision.encode(), manifest['sourceRevision'].encode()}
    seen = set()
    carry = b''
    with _open_regular(binary, executable=True) as file:
      if not elf_arm64_static_file(file):
        return False
      file.seek(0)
      for chunk in iter(lambda: file.read(1024 * 1024), b''):
        digest.update(chunk)
        window = carry + chunk
        seen.update(stamp for stamp in stamps if stamp in window)
        carry = window[-128:]
    return digest.hexdigest() == manifest.get('binarySha256') and stamps == seen
  except (OSError, ValueError, KeyError, StopIteration, TypeError, OverflowError, RecursionError):
    return False


def enabled(started: bool, params: Params, CP: car.CarParams) -> bool:
  if not started or CP.notCar:
    return False
  try:
    with _open_regular(Path(params.get_param_path(OPT_IN_KEY)), max_bytes=1) as file:
      return file.read(2) == b'1'
  except (OSError, ValueError):
    return False


class MapdShadowProcess(NativeProcess):
  """NativeProcess with bounded retry for an exited or unavailable shadow."""

  def __init__(self, clock=time.monotonic):
    super().__init__('mapd_shadow', str(PROVIDER_DIR.relative_to(BASEDIR)),
                     [str(PROVIDER_BINARY), '--shadow', '--offline-root', str(OFFLINE_ROOT)], enabled)
    self._clock = clock
    self._failures = 0
    self._retry_at = 0.0
    self._started_at = 0.0

  def _delay_retry(self, now: float) -> None:
    self._failures += 1
    self._retry_at = now + min(2 ** min(self._failures - 1, 6), 60)

  def start(self) -> None:
    now = self._clock()
    if self.shutting_down:
      NativeProcess.stop(self)
      if self.proc is not None:
        return
    if self.proc is not None:
      if self.proc.exitcode is None:
        if now - self._started_at >= 60:
          self._failures = 0
        return
      NativeProcess.stop(self, block=False)  # reap a failed direct child
      self._delay_retry(now)
      return
    if now < self._retry_at:
      return
    if not preflight():
      cloudlog.warning('mapd shadow package or offline root unavailable')
      self._delay_retry(now)
      return
    NativeProcess.start(self)
    self._started_at = now

  def stop(self, retry: bool = True, block: bool = True, sig=None):
    result = NativeProcess.stop(self, retry=retry, block=block, sig=sig)
    self._failures = 0
    self._retry_at = 0.0
    return result
