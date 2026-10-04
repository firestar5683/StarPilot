"""Installed alert WAV packs."""

from pathlib import Path
import re
import wave

import numpy as np

PACK_ROOT = Path("/data/themes/theme_packs")
DEFAULT_PACK = "starpilot"
BUILTIN_FILES = {
  "engage.wav": "engage.wav", "disengage.wav": "disengage.wav",
  "refuse.wav": "warning_1.wav", "warning.wav": "warning_1.wav", "pre_alert.wav": "warning_1.wav",
  "dm_warning.wav": "warning_2.wav", "critical.wav": "warning_2.wav", "dm_critical.wav": "warning_3.wav",
}
REMOVED_PACKS = frozenset(("frog", "frogpilot"))
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
