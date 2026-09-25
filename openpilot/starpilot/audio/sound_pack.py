"""Installed alert WAV packs."""

from pathlib import Path
import re
import os
import stat
import wave

import numpy as np

PACK_ROOT = Path("/data/themes/theme_packs")
DEFAULT_PACK = "starpilot"
BUILTIN_FILES = {
  "engage.wav": "engage.wav", "disengage.wav": "disengage.wav",
  "refuse.wav": "warning_1.wav", "warning.wav": "warning_1.wav", "pre_alert.wav": "warning_1.wav",
  "dm_warning.wav": "warning_2.wav", "critical.wav": "warning_2.wav", "dm_critical.wav": "warning_3.wav",
}
REMOVED_PACKS = frozenset(("frog", "frogpilot", "stalin"))
MAX_WAV_BYTES = 48000 * 2 * 30 + 4096
LEGACY_NAMES = {
  "warning.wav": "prompt.wav", "dm_warning.wav": "prompt_distracted.wav",
  "critical.wav": "warning_soft.wav", "dm_critical.wav": "warning_immediate.wav",
}


def pack_directory(name: str, root: Path = PACK_ROOT) -> Path | None:
  if name in (DEFAULT_PACK, "stock") or name.casefold() in REMOVED_PACKS or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_~.-]{0,127}", name):
    return None
  directory = root / name / "sounds"
  try:
    if any(path.is_symlink() for path in (root, root / name, directory)) or not directory.is_dir():
      return None
    return directory
  except OSError:
    return None


def installed_packs(root: Path = PACK_ROOT) -> tuple[str, ...]:
  try:
    return (DEFAULT_PACK, "stock") + tuple(sorted(path.name for path in root.iterdir() if pack_directory(path.name, root) is not None))
  except OSError:
    return (DEFAULT_PACK, "stock")


def read_selection(params) -> tuple[bytes | None, str, bool]:
  try:
    try:
      with Path(params.get_param_path("SoundPack")).open("rb") as source:
        raw = source.read(129)
    except FileNotFoundError:
      raw = None
    if raw is not None and len(raw) > 128:
      return raw, DEFAULT_PACK, False
    try:
      name = DEFAULT_PACK if raw is None else raw.decode("utf-8")
    except UnicodeError:
      return raw, DEFAULT_PACK, True
    if name.casefold() in REMOVED_PACKS:
      name = DEFAULT_PACK
    valid = name in (DEFAULT_PACK, "stock") or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_~.-]{0,127}", name) is not None
    return raw, name if valid else DEFAULT_PACK, True
  except (OSError, KeyError, TypeError, ValueError, UnicodeError):
    return None, DEFAULT_PACK, False


def migrate_removed_selection(params, root: Path = PACK_ROOT) -> bool:
  """Persist the fork default when a saved pack no longer identifies a valid choice."""
  from openpilot.starpilot.saved_document import commit_exact
  raw, name, readable = read_selection(params)
  if not readable or raw == DEFAULT_PACK.encode():
    return False
  legacy_default = raw is None or raw.strip().lower() in (b"", b"default", b"frog", b"frogpilot")
  valid_choice = name == "stock" or pack_directory(name, root) is not None
  if not legacy_default and valid_choice:
    return False
  return commit_exact(params, key="SoundPack", max_bytes=128, raw=DEFAULT_PACK.encode(), expected=raw,
                      authorized=lambda: True, temp_prefix=".sound-pack-migration-").verified


def cleanup_removed_packs(root: Path = PACK_ROOT, *, parked) -> tuple[str, ...]:
  """Bounded parked migration over captured directory descriptors.

  Enumerate at most 256 root entries and 64 pack entries, depth 4 / 96 MiB.
  Keep captured descriptors, never follow links, and check entry identities
  before mutations. External renames between check and syscall remain a POSIX
  race; symlink targets are never traversed.
  Concurrent growth/revocation leaves remaining obsolete files for a later retry.
  """
  def safe():
    try:
      return bool(parked())
    except Exception:
      return False

  def inode(value):
    return value.st_dev, value.st_ino

  def revision(value):
    return inode(value), value.st_mtime_ns, value.st_ctime_ns

  removed, opened = [], []
  try:
    if not safe() or root.is_symlink():
      return ()
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    opened.append(root_fd)
    root_identity = inode(os.fstat(root_fd))
    names = []
    with os.scandir(root_fd) as entries:
      for entry in entries:
        if len(names) == 256:
          return ()
        names.append(entry.name)
    for name in names:
      if name.casefold() not in REMOVED_PACKS or not safe():
        continue
      expected = os.stat(name, dir_fd=root_fd, follow_symlinks=False)

      def guard(name=name, expected=expected):
        return (safe() and inode(root.lstat()) == root_identity and
                inode(os.stat(name, dir_fd=root_fd, follow_symlinks=False)) == inode(expected))

      if stat.S_ISLNK(expected.st_mode):
        if guard():
          os.unlink(name, dir_fd=root_fd)
          removed.append(name)
        continue
      if not stat.S_ISDIR(expected.st_mode):
        continue
      pack_fds, budget = [], [0, 0]
      try:
        pack_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        pack_fds.append(pack_fd)
        if inode(os.fstat(pack_fd)) != inode(expected):
          continue

        def plan(directory_fd, depth, *, budget=budget, pack_fds=pack_fds, guard=guard):
          if depth > 4 or not guard():
            raise ValueError('cleanup depth or authority')
          node = [directory_fd, revision(os.fstat(directory_fd)), []]
          with os.scandir(directory_fd) as entries:
            for entry in entries:
              budget[0] += 1
              if budget[0] > 64:
                raise ValueError('cleanup entry bound')
              saved = os.stat(entry.name, dir_fd=directory_fd, follow_symlinks=False)
              child = None
              if stat.S_ISDIR(saved.st_mode):
                child_fd = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
                pack_fds.append(child_fd)
                if inode(os.fstat(child_fd)) != inode(saved):
                  raise ValueError('cleanup inode changed')
                child = plan(child_fd, depth + 1)
              elif not (stat.S_ISREG(saved.st_mode) or stat.S_ISLNK(saved.st_mode)):
                raise ValueError('cleanup unexpected entry')
              else:
                budget[1] += saved.st_size
                if budget[1] > 96 * 1024 * 1024:
                  raise ValueError('cleanup byte bound')
              node[2].append((entry.name, saved, child))
          if revision(os.fstat(directory_fd)) != node[1]:
            raise ValueError('cleanup directory changed')
          return node

        tree = plan(pack_fd, 1)

        def same_entries(directory_fd, expected_names):
          observed = set()
          with os.scandir(directory_fd) as entries:
            for entry in entries:
              if len(observed) == 64:
                return False
              observed.add(entry.name)
          return observed == expected_names

        def remove(node, *, guard=guard):
          directory_fd, _, children = node
          for index, (entry_name, saved, child) in enumerate(children):
            expected_names = {item[0] for item in children[index:]}
            if (not guard() or not same_entries(directory_fd, expected_names) or
                revision(os.fstat(directory_fd)) != node[1]):
              raise ValueError('cleanup authority or growth')
            current = os.stat(entry_name, dir_fd=directory_fd, follow_symlinks=False)
            if revision(current) != revision(saved):
              raise ValueError('cleanup replacement entry')
            if child is not None:
              remove(child)
              if not guard() or inode(os.stat(entry_name, dir_fd=directory_fd, follow_symlinks=False)) != inode(saved):
                raise ValueError('cleanup replacement directory')
              os.rmdir(entry_name, dir_fd=directory_fd)
            else:
              os.unlink(entry_name, dir_fd=directory_fd)
            node[1] = revision(os.fstat(directory_fd))
          if (not guard() or not same_entries(directory_fd, set()) or
              revision(os.fstat(directory_fd)) != node[1]):
            raise ValueError('cleanup authority or growth')

        remove(tree)
        if guard():
          os.rmdir(name, dir_fd=root_fd)
          removed.append(name)
      except (OSError, ValueError):
        pass
      finally:
        for descriptor in reversed(pack_fds):
          os.close(descriptor)
  except (OSError, TypeError, ValueError):
    pass
  finally:
    for descriptor in reversed(opened):
      os.close(descriptor)
  return tuple(removed)


def read_wav(path: Path) -> np.ndarray:
  if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_WAV_BYTES:
    raise ValueError("invalid WAV file")
  with wave.open(str(path), "rb") as source:
    frames = source.getnframes()
    if (source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getcomptype()) != (1, 2, 48000, "NONE"):
      raise ValueError("invalid WAV format")
    if not 0 < frames <= 48000 * 30:
      raise ValueError("invalid WAV duration")
    raw = source.readframes(frames)
    if len(raw) != frames * 2:
      raise ValueError("truncated WAV")
  result = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / (2**16/2)
  result.flags.writeable = False
  return result


class SoundPackLoader:
  def __init__(self, params, stock: Path, root: Path = PACK_ROOT):
    self.params, self.stock, self.root = params, stock, root
    self.signature = None
    self.checked_at = float("-inf")
    self.stock_sounds: dict[str, np.ndarray] = {}
    self.builtin_sounds: dict[str, np.ndarray] = {}

  def is_builtin(self, samples: np.ndarray) -> bool:
    return any(samples is loaded for loaded in self.builtin_sounds.values())

  def refresh(self, filenames: tuple[str, ...], now: float) -> dict[str, np.ndarray] | None:
    if 0 <= now - self.checked_at < 1.0:
      return None
    self.checked_at = now
    raw, name, readable = read_selection(self.params)
    directory = pack_directory(name, self.root) if readable else None
    paths = tuple(directory / candidate for filename in filenames
                  for candidate in dict.fromkeys((LEGACY_NAMES.get(filename, filename), filename))) if directory else ()
    paths += tuple(self.stock.parent / "sounds_starpilot" / BUILTIN_FILES[filename]
                   for filename in filenames if filename in BUILTIN_FILES)
    metadata = []
    for path in paths:
      try:
        stat = path.lstat()
        metadata.append((stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))
      except OSError:
        metadata.append(None)
    signature = (raw, directory, filenames, tuple(metadata))
    if signature == self.signature:
      return None
    result = {}
    builtin_loaded = {}
    for filename in filenames:
      selected = None
      if (name == DEFAULT_PACK or not readable) and filename in BUILTIN_FILES:
        builtin = BUILTIN_FILES[filename]
        try:
          if builtin not in builtin_loaded:
            builtin_loaded[builtin] = read_wav(self.stock.parent / "sounds_starpilot" / builtin)
          selected = builtin_loaded[builtin]
          self.builtin_sounds[builtin] = selected
        except (OSError, EOFError, ValueError, wave.Error):
          # A damaged optional pack must not stop working stock alerts.
          pass
      if selected is None:
        if filename not in self.stock_sounds:
          self.stock_sounds[filename] = read_wav(self.stock / filename)
        selected = self.stock_sounds[filename]
      if directory:
        for candidate in dict.fromkeys((LEGACY_NAMES.get(filename, filename), filename)):
          try:
            selected = read_wav(directory / candidate)
            break
          except (OSError, EOFError, ValueError, wave.Error):
            pass
      result[filename] = selected
    self.signature = signature
    return result
