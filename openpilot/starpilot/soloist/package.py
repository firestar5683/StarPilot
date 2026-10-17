"""Bounded import of the user's own Soloist download.

The archive becomes executable code, so it is installed only when it is byte-identical to the build
Spotify's CDN currently serves (its ETag is the archive's MD5), or to a build this comma verified
that way before. Nothing is extracted blindly and nothing from the archive runs before that check.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
import threading
import urllib.error
import urllib.request
import zlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from openpilot.starpilot.soloist.paths import Layout, private_dir

DOWNLOAD_PAGE = 'https://developer.spotify.com/documentation/soloist/reference/downloads-and-updates'
OFFICIAL_URL = 'https://soloist-builds.spotifycdn.com/soloist_release_arm64.tar.gz'
ARCHIVE_NAME = 'soloist_release_arm64.tar.gz'

MAX_UPLOAD_BYTES = 64 * 1024 * 1024
MAX_UNPACKED_BYTES = 128 * 1024 * 1024
MAX_EXECUTABLE_BYTES = 96 * 1024 * 1024
MAX_ENTRIES = 16
KEPT_FILES = ('soloist', 'CHANGELOG.md', 'THIRD_PARTY_LICENSES.txt')
LIFETIME = timedelta(days=90)
INTERPRETER = b'/lib/ld-linux-aarch64.so.1'
EM_AARCH64 = 183
VERSION = re.compile(r'^soloist (\d+(?:\.\d+){1,3}) build (\d{9,11})\b')
GLIBC = re.compile(rb'GLIBC_2\.(\d{1,3})\b')


class ImportFailed(RuntimeError):
  def __init__(self, message: str, code: str = 'FAILED'):
    super().__init__(message)
    self.code = code


def _now() -> datetime:
  return datetime.now(UTC)


class _Bounded:
  """Count decompressed bytes so a small gzip cannot expand without limit."""

  def __init__(self, raw, limit: int):
    self.raw, self.limit, self.read_bytes = raw, limit, 0

  def read(self, size: int = -1) -> bytes:
    data = self.raw.read(size)
    self.read_bytes += len(data)
    if self.read_bytes > self.limit:
      raise ImportFailed('The archive unpacks to more data than a Soloist release', 'TOO_LARGE')
    return data


def _kept_name(name: str) -> str | None:
  parts = [part for part in name.split('/') if part not in ('', '.')]
  if any(part == '..' for part in parts) or name.startswith('/'):
    raise ImportFailed('The archive contains an unsafe path', 'UNSAFE')
  if len(parts) > 2:  # bare files, or one top-level folder around them
    return None
  return parts[-1] if parts and parts[-1] in KEPT_FILES else None


def read_archive(path: Path, *, max_unpacked: int = MAX_UNPACKED_BYTES) -> dict[str, bytes]:
  """Return the kept regular files. Links, devices, duplicates and oversized members are refused."""
  with path.open('rb') as handle:
    if handle.read(2) != b'\x1f\x8b':
      raise ImportFailed('Not a .tar.gz archive', 'NOT_ARCHIVE')
  files: dict[str, bytes] = {}
  seen: set[str] = set()
  entries = 0
  try:
    with gzip.open(path, 'rb') as raw:
      stream = _Bounded(raw, max_unpacked + 1024 * 1024)  # tar headers and padding
      with tarfile.open(fileobj=stream, mode='r|') as archive:
        for member in archive:
          entries += 1
          if entries > MAX_ENTRIES:
            raise ImportFailed('The archive has too many entries for a Soloist release', 'UNSAFE')
          normalized = '/'.join(part for part in member.name.split('/') if part not in ('', '.'))
          if normalized in seen:
            raise ImportFailed('The archive repeats a file', 'UNSAFE')
          seen.add(normalized)
          if member.isdir():
            _kept_name(member.name + '/x')
            continue
          if not member.isreg() or member.issparse():
            raise ImportFailed('The archive contains links or special files', 'UNSAFE')
          name = _kept_name(member.name)
          limit = MAX_EXECUTABLE_BYTES if name == 'soloist' else 4 * 1024 * 1024
          if member.size > (limit if name else max_unpacked):
            raise ImportFailed('A file in the archive is too large', 'TOO_LARGE')
          source = archive.extractfile(member)
          data = source.read(member.size + 1) if source is not None else b''
          if len(data) != member.size:
            raise ImportFailed('The archive is incomplete', 'CORRUPT')
          if name is not None:
            if name in files:
              raise ImportFailed('The archive repeats a file', 'UNSAFE')
            files[name] = data
  except (tarfile.TarError, EOFError, zlib.error, gzip.BadGzipFile) as error:
    raise ImportFailed(f'The archive is damaged: {error}', 'CORRUPT') from error
  if 'soloist' not in files:
    raise ImportFailed('No soloist player was found in this archive', 'NO_PLAYER')
  return files


def check_executable(data: bytes, *, max_glibc_minor: int | None = None) -> None:
  """Static ELF checks: 64-bit little-endian AArch64 with the expected dynamic loader."""
  if len(data) < 64 or data[:4] != b'\x7fELF':
    raise ImportFailed('The soloist file is not a Linux program', 'NO_PLAYER')
  if data[4] != 2 or data[5] != 1:
    raise ImportFailed('This is not the 64-bit ARM (AArch64) download', 'WRONG_ARCH')
  e_type, e_machine = struct.unpack_from('<HH', data, 16)
  if e_machine != EM_AARCH64:
    raise ImportFailed('This is not the ARMv8/AArch64 Linux download', 'WRONG_ARCH')
  if e_type not in (2, 3):
    raise ImportFailed('The soloist file is not a program', 'NO_PLAYER')
  phoff, = struct.unpack_from('<Q', data, 32)
  phentsize, phnum = struct.unpack_from('<HH', data, 54)
  interpreter = None
  if phentsize < 56 or phnum > 64 or phoff + phentsize * phnum > len(data):
    raise ImportFailed('The soloist program is damaged', 'CORRUPT')
  for index in range(phnum):
    p_type, _, p_offset, _, _, p_filesz = struct.unpack_from('<IIQQQQ', data, phoff + index * phentsize)
    if p_type == 3:  # PT_INTERP
      if p_offset + p_filesz > len(data):
        raise ImportFailed('The soloist program is damaged', 'CORRUPT')
      interpreter = data[p_offset:p_offset + p_filesz].rstrip(b'\x00')
  if interpreter != INTERPRETER:
    raise ImportFailed('The soloist program expects a different Linux system', 'INCOMPATIBLE')
  if max_glibc_minor is not None:
    needed = max((int(minor) for minor in GLIBC.findall(data)), default=0)
    if needed > max_glibc_minor:
      raise ImportFailed(f'This Soloist build needs glibc 2.{needed}; this comma has 2.{max_glibc_minor}', 'INCOMPATIBLE')


def system_glibc_minor() -> int | None:
  try:
    match = re.fullmatch(r'glibc 2\.(\d+)', os.confstr('CS_GNU_LIBC_VERSION') or '')
  except (ValueError, OSError):
    return None
  return int(match.group(1)) if match else None


def official_digest(url: str = OFFICIAL_URL, timeout: float = 15.0) -> tuple[str, int]:
  """Spotify's CDN publishes the current archive's MD5 as its ETag; read it with a HEAD request over HTTPS."""
  request = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'StarPilot-Soloist-Verify'})
  try:
    with urllib.request.urlopen(request, timeout=timeout) as response:
      if not response.geturl().startswith('https://'):
        raise ImportFailed('Spotify’s download check was redirected', 'OFFLINE')
      etag = (response.headers.get('ETag') or '').strip().strip('"').lower()
      length = int(response.headers.get('Content-Length') or -1)
  except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
    raise ImportFailed('The comma could not reach Spotify to check this download. Connect it to the internet and try again.',
                       'OFFLINE') from error
  if not re.fullmatch(r'[0-9a-f]{32}', etag) or length <= 0:
    raise ImportFailed('Spotify’s download server did not return a checksum to compare against', 'OFFLINE')
  return etag, length


def probe_version(executable: Path, *, timeout: float = 10.0) -> str:
  """Run only `--version`, with no credentials, an empty environment and a private working directory."""
  with tempfile.TemporaryDirectory(prefix='soloist-probe-') as work:
    try:
      result = subprocess.run([str(executable), '--version'], cwd=work, env={'HOME': work, 'PATH': '/usr/bin:/bin'},
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as error:
      raise ImportFailed('Soloist did not answer its version check', 'INCOMPATIBLE') from error
    except OSError as error:
      raise ImportFailed(f'Soloist could not start on this comma: {error}', 'INCOMPATIBLE') from error
  output = (result.stdout + result.stderr).decode('utf-8', 'replace').strip()
  if result.returncode == 10:
    raise ImportFailed('This Soloist build has already expired. Download the newest one from Spotify.', 'EXPIRED')
  if result.returncode != 0:
    detail = output.splitlines()[-1][:200] if output else f'exit code {result.returncode}'
    raise ImportFailed(f'Soloist could not start on this comma: {detail}', 'INCOMPATIBLE')
  return output.splitlines()[0] if output else ''


def parse_version(line: str) -> dict:
  match = VERSION.match(line.strip())
  if not match:
    raise ImportFailed('Soloist reported an unrecognized version', 'INCOMPATIBLE')
  built = datetime.fromtimestamp(int(match.group(2)), UTC)
  return {'version': match.group(1), 'built': built.isoformat(), 'expires': (built + LIFETIME).isoformat(), 'versionLine': line.strip()[:200]}


def _fsync_dir(path: Path) -> None:
  fd = os.open(path, os.O_RDONLY)
  try:
    os.fsync(fd)
  finally:
    os.close(fd)


def _write(path: Path, data: bytes, mode: int) -> None:
  with path.open('xb') as out:
    out.write(data)
    out.flush()
    os.fsync(out.fileno())
  os.chmod(path, mode)


def _swap_link(link: Path, target: str) -> None:
  temporary = link.with_name(f'.{link.name}.{os.getpid()}')
  temporary.unlink(missing_ok=True)
  os.symlink(target, temporary)
  os.replace(temporary, link)


def _verified_path(layout: Layout) -> Path:
  return layout.root / 'verified.json'


def _verified(layout: Layout) -> set[str]:
  try:
    value = json.loads(_verified_path(layout).read_text())
  except (OSError, ValueError):
    return set()
  return {item for item in value if isinstance(item, str) and re.fullmatch(r'[0-9a-f]{64}', item)} if isinstance(value, list) else set()


def _remember_verified(layout: Layout, sha256: str) -> None:
  known = sorted(_verified(layout) | {sha256})[-16:]
  temporary = _verified_path(layout).with_suffix('.tmp')
  temporary.write_text(json.dumps(known))
  os.replace(temporary, _verified_path(layout))


def stage_release(layout: Layout, files: dict[str, bytes], metadata: dict) -> Path:
  """Write an unpacked release under releases/<sha256>/ without activating it."""
  private_dir(layout.releases)
  final = layout.releases / metadata['sha256']
  if final.is_dir() and (final / 'soloist').is_file():
    return final
  staging = Path(tempfile.mkdtemp(prefix='.staging-', dir=layout.releases))
  try:
    for name, data in files.items():
      _write(staging / name, data, 0o555 if name == 'soloist' else 0o444)
    _write(staging / 'release.json', json.dumps(metadata, sort_keys=True).encode(), 0o444)
    _fsync_dir(staging)
    shutil.rmtree(final, ignore_errors=True)
    os.replace(staging, final)
    _fsync_dir(layout.releases)
  except BaseException:
    shutil.rmtree(staging, ignore_errors=True)
    raise
  return final


def activate(layout: Layout, release: Path) -> None:
  """Atomically point current at the release, keep the old one as previous, and prune the rest."""
  old = os.readlink(layout.current) if layout.current.is_symlink() else None
  target = os.path.relpath(release, layout.root)
  if old == target:
    return
  if old is not None and (layout.root / old / 'soloist').is_file():
    _swap_link(layout.previous, old)
  _swap_link(layout.current, target)
  _fsync_dir(layout.root)
  keep = {Path(os.path.realpath(link)).name for link in (layout.current, layout.previous) if link.is_symlink()}
  for entry in layout.releases.iterdir():
    if entry.name not in keep:
      shutil.rmtree(entry, ignore_errors=True)


def rollback(layout: Layout) -> bool:
  """Restore the previous release (used when a new build cannot start)."""
  if not layout.previous.is_symlink() or not (layout.previous / 'soloist').is_file():
    return False
  failed = os.readlink(layout.current) if layout.current.is_symlink() else None
  _swap_link(layout.current, os.readlink(layout.previous))
  layout.previous.unlink(missing_ok=True)
  if failed:
    shutil.rmtree(layout.root / failed, ignore_errors=True)
  return True


def release_status(layout: Layout, now: datetime | None = None) -> dict:
  try:
    metadata = json.loads((layout.current / 'release.json').read_text())
    if not (layout.current / 'soloist').is_file():
      raise OSError
  except (OSError, ValueError):
    return {'installed': False}
  now = now or _now()
  status = {'installed': True, **{key: metadata.get(key) for key in ('version', 'built', 'expires', 'sha256')}}
  try:
    expires = datetime.fromisoformat(metadata['expires'])
  except (KeyError, TypeError, ValueError):
    return status
  days = (expires - now).total_seconds() / 86400
  status['daysLeft'] = max(0, int(days))
  status['expired'] = days <= 0
  status['level'] = 'expired' if days <= 0 else 'soon' if days <= 14 else 'ok'
  return status


def remove_releases(layout: Layout) -> None:
  for link in (layout.current, layout.previous):
    link.unlink(missing_ok=True)
  shutil.rmtree(layout.releases, ignore_errors=True)
  _verified_path(layout).unlink(missing_ok=True)


def import_archive(layout: Layout, path: Path, *, progress: Callable[..., None] = lambda **_: None,
                   digest: Callable[[], tuple[str, int]] = official_digest,
                   probe: Callable[[Path], str] = probe_version,
                   may_activate: Callable[[], bool] = lambda: True,
                   glibc_minor: int | None = None, now: datetime | None = None) -> dict:
  progress(stage='reading')
  size = path.stat().st_size
  if not 0 < size <= MAX_UPLOAD_BYTES:
    raise ImportFailed('This file is too large to be the Soloist download', 'TOO_LARGE')
  sha256, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
  with path.open('rb') as handle:
    while chunk := handle.read(1024 * 1024):
      sha256.update(chunk)
      md5.update(chunk)
  progress(stage='unpacking')
  files = read_archive(path)
  check_executable(files['soloist'], max_glibc_minor=glibc_minor)

  progress(stage='verifying')
  sha = sha256.hexdigest()
  if sha not in _verified(layout):
    etag, length = digest()
    if etag != md5.hexdigest() or length != size:
      raise ImportFailed('This file doesn’t match the Soloist build Spotify is offering right now. ' +
                         'Download it again from Spotify and upload the new file.', 'NOT_OFFICIAL')

  progress(stage='testing')
  metadata = {'sha256': sha, 'md5': md5.hexdigest(), 'size': size, 'verified': (now or _now()).isoformat()}
  private_dir(layout.root)
  release = stage_release(layout, files, metadata)
  try:
    metadata.update(parse_version(probe(release / 'soloist')))
    if datetime.fromisoformat(metadata['expires']) <= (now or _now()):
      raise ImportFailed('This Soloist build has already expired. Download the newest one from Spotify.', 'EXPIRED')
    os.chmod(release / 'release.json', 0o644)
    (release / 'release.json').write_text(json.dumps(metadata, sort_keys=True))
    os.chmod(release / 'release.json', 0o444)
    _remember_verified(layout, sha)
    progress(stage='installing')
    if not may_activate():
      raise ImportFailed('Put the car in Park or use offroad mode to finish installing', 'DRIVING')
    activate(layout, release)
  except BaseException:
    if not (layout.current.is_symlink() and Path(os.path.realpath(layout.current)) == release.resolve()):
      shutil.rmtree(release, ignore_errors=True)
    raise
  return metadata


class ImportJob:
  """One Soloist import at a time, in a background thread, with pollable status."""

  def __init__(self, layout: Layout | None = None, **overrides):
    self.layout = layout or Layout.default()
    self.overrides = overrides
    self.lock = threading.Lock()
    self.thread: threading.Thread | None = None
    self.state: dict = {'state': 'idle'}

  @property
  def work_dir(self) -> Path:
    return self.layout.imports

  def status(self) -> dict:
    with self.lock:
      return dict(self.state)

  def _set(self, **values) -> None:
    with self.lock:
      self.state.update(values)

  def busy(self) -> bool:
    return self.thread is not None and self.thread.is_alive()

  def start(self, *, path: Path, enabled: Callable[[], bool], may_activate: Callable[[], bool] = lambda: True,
            on_installed: Callable[[], None] = lambda: None) -> None:
    with self.lock:
      if self.busy():
        raise ImportFailed('An import is already running')
      self.state = {'state': 'running', 'stage': 'reading', 'started': _now().timestamp()}
      self.thread = threading.Thread(target=self._run, args=(path, enabled, may_activate, on_installed),
                                     name='soloist_import', daemon=True)
      self.thread.start()

  def _run(self, path: Path, enabled, may_activate, on_installed) -> None:
    def progress(**values):
      if not enabled():
        raise ImportFailed('Setup authorization changed', 'CANCELLED')
      self._set(**values)

    try:
      options = {'glibc_minor': system_glibc_minor(), **self.overrides}
      metadata = import_archive(self.layout, path, progress=progress, may_activate=lambda: enabled() and may_activate(), **options)
      self._set(state='done', stage='done', finished=_now().timestamp(), version=metadata.get('version'), expires=metadata.get('expires'))
      on_installed()
    except ImportFailed as error:
      self._set(state='failed', finished=_now().timestamp(), error=str(error), code=error.code)
    except Exception as error:
      self._set(state='failed', finished=_now().timestamp(), error=f'{type(error).__name__}: {error}', code='FAILED')
    finally:
      path.unlink(missing_ok=True)
