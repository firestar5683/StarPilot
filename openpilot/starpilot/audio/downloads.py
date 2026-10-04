"""Bounded installation of published sound packs while the car is parked."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import threading
import urllib.request
import uuid
import zipfile

from openpilot.starpilot.audio.sound_pack import LEGACY_NAMES, MAX_WAV_BYTES, PACK_ROOT, pack_directory, read_wav


ORIGIN = "https://huggingface.co/buckets/StarPilot-Driving/StarPilot-Resources/resolve/"
CATALOG_PATH = Path(__file__).with_name("catalog.json")
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_FILES = 32
MAX_EXPANDED_BYTES = 96 * 1024 * 1024
CHUNK = 64 * 1024
ALLOWED_FILES = {f"{name}.wav" for name in (
  "engage", "disengage", "refuse", "warning", "dm_warning", "pre_alert", "critical", "dm_critical", "prompt_repeat",
  "distracted", "engage_tizi", "disengage_tizi",
)} | set(LEGACY_NAMES.values())
SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class SoundDownloadError(Exception):
  def __init__(self, message: str, status: int = 400):
    super().__init__(message)
    self.status = status


class _Cancelled(Exception):
  pass


class SoundDownloads:
  def __init__(self, parked, root: Path = PACK_ROOT, catalog_path: Path = CATALOG_PATH, opener=None):
    self.parked = parked
    self.root = Path(root)
    self.opener = opener or urllib.request.urlopen
    self._lock = threading.Lock()
    self._cancel = threading.Event()
    self._closed = False
    self._thread = None
    self._lock_file = None
    self._job: dict | None = None
    try:
      with Path(catalog_path).open("rb") as source:
        raw = source.read(65537)
      if len(raw) > 65536:
        raise ValueError("catalog too large")
      catalog = json.loads(raw)
      if not isinstance(catalog, dict) or catalog.get("version") != 1 or not isinstance(catalog.get("packs"), list) or len(catalog["packs"]) > 64:
        raise ValueError("unsupported catalog")
      packs = {}
      for pack in catalog["packs"]:
        slug = pack["id"]
        if (not isinstance(slug, str) or not SLUG.fullmatch(slug) or slug == "stock" or slug in packs or
            pack["path"] != f"theme/Themes/{slug}/sounds.zip" or
            not isinstance(pack["name"], str) or not 0 < len(pack["name"]) <= 128 or
            type(pack["size"]) is not int or not 0 < pack["size"] <= MAX_ARCHIVE_BYTES or
            not isinstance(pack["sha256"], str) or not SHA256.fullmatch(pack["sha256"])):
          raise ValueError("invalid catalog entry")
        packs[slug] = pack
      self._packs = packs
    except (OSError, ValueError, KeyError, TypeError) as exc:
      raise SoundDownloadError("sound catalog unavailable", 503) from exc

  def snapshot(self) -> dict:
    with self._lock:
      return self._snapshot()

  def _snapshot(self) -> dict:
    try:
      parked = bool(self.parked())
    except Exception:
      parked = False
    return {
      "parked": parked,
      "packs": [{"id": p["id"], "name": p["name"], "installed": pack_directory(p["id"], self.root) is not None}
                for p in self._packs.values()],
      "job": self._job.copy() if self._job else None,
    }

  def action(self, command: str, data: dict) -> dict:
    if not isinstance(data, dict):
      raise SoundDownloadError("invalid request")
    with self._lock:
      if self._closed:
        raise SoundDownloadError("downloads are unavailable", 503)
      if command == "cancel":
        if set(data) != {"job"}:
          raise SoundDownloadError("invalid request")
        if not self._job or data.get("job") != self._job["id"] or self._job["state"] not in ("downloading", "verifying"):
          raise SoundDownloadError("download job not active", 409)
        self._cancel.set()
      elif command == "download":
        if set(data) != {"pack"}:
          raise SoundDownloadError("invalid request")
        slug = data.get("pack")
        if not isinstance(slug, str) or slug not in self._packs:
          raise SoundDownloadError("unknown sound pack")
        if not self._safe_parked():
          raise SoundDownloadError("park the car before downloading", 409)
        if self._thread and self._thread.is_alive():
          raise SoundDownloadError("a download is already running", 409)
        self._prepare_root()
        if (self.root / slug).exists() or (self.root / slug).is_symlink():
          raise SoundDownloadError("sound pack already exists", 409)
        try:
          descriptor = os.open(self.root / ".sound-download.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
          if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise OSError("unsafe lock file")
          lock_file = os.fdopen(descriptor, "r+b")
        except OSError as exc:
          raise SoundDownloadError("sound storage unavailable", 503) from exc
        try:
          fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
          lock_file.close()
          raise SoundDownloadError("a download is already running", 409) from exc
        if (self.root / slug).exists() or (self.root / slug).is_symlink():
          fcntl.flock(lock_file, fcntl.LOCK_UN)
          lock_file.close()
          raise SoundDownloadError("sound pack already exists", 409)
        self._lock_file = lock_file
        self._cancel.clear()
        self._job = {"id": uuid.uuid4().hex, "pack": slug, "state": "downloading", "bytes": 0,
                     "total": self._packs[slug]["size"], "error": None}
        self._thread = threading.Thread(target=self._run, args=(self._packs[slug],), daemon=True)
        self._thread.start()
        return self._snapshot()
      else:
        raise SoundDownloadError("unknown action")
    return self.snapshot()

  def _safe_parked(self) -> bool:
    try:
      return bool(self.parked())
    except Exception:
      return False

  def _prepare_root(self):
    try:
      if self.root.is_symlink():
        raise OSError("unsafe pack directory")
      self.root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
      raise SoundDownloadError("sound storage unavailable", 503) from exc

  def _check_active(self):
    if self._cancel.is_set() or not self._safe_parked():
      raise _Cancelled()

  def _run(self, pack: dict):
    job = self._job
    assert job is not None
    stage = None
    try:
      stage = Path(tempfile.mkdtemp(prefix=".sound-download-", dir=self.root))
      archive = stage / "archive.zip"
      digest = hashlib.sha256()
      with self.opener(ORIGIN + pack["path"], timeout=20) as response:
        with archive.open("wb") as target:
          remaining = pack["size"]
          while remaining:
            self._check_active()
            chunk = response.read(min(CHUNK, remaining + 1))
            if not chunk or len(chunk) > remaining:
              raise ValueError("archive length mismatch")
            target.write(chunk)
            digest.update(chunk)
            remaining -= len(chunk)
            with self._lock:
              job["bytes"] = pack["size"] - remaining
          self._check_active()
          if response.read(1):
            raise ValueError("archive length mismatch")
      with self._lock:
        job["state"] = "verifying"
      if digest.hexdigest() != pack["sha256"]:
        raise ValueError("archive checksum mismatch")
      sounds = stage / "sounds"
      sounds.mkdir()
      self._extract(archive, sounds)
      archive.unlink()
      with self._lock:
        self._check_active()
        if (self.root / pack["id"]).exists() or (self.root / pack["id"]).is_symlink():
          raise ValueError("sound pack already exists")
        os.rename(stage, self.root / pack["id"])
        stage = None
        job["state"] = "complete"
    except _Cancelled:
      with self._lock:
        job["state"] = "cancelled"
    except Exception as exc:
      with self._lock:
        if self._cancel.is_set() or not self._safe_parked():
          job["state"] = "cancelled"
        else:
          job["state"] = "failed"
          job["error"] = str(exc) or "download failed"
    finally:
      with self._lock:
        lock_file, self._lock_file = self._lock_file, None
      if stage is not None:
        shutil.rmtree(stage, ignore_errors=True)
      if lock_file is not None:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()

  def _extract(self, archive: Path, sounds: Path):
    with zipfile.ZipFile(archive) as source:
      members = source.infolist()
      if not 0 < len(members) <= MAX_FILES:
        raise ValueError("invalid sound archive")
      wrapped = any(member.filename == "sounds/" for member in members)
      raw_names = set()
      names = set()
      metadata = set()
      total = 0
      audio = []
      for member in members:
        self._check_active()
        name = member.filename
        mode = (member.external_attr >> 16) & 0xffff
        if (name in raw_names or member.flag_bits & 1 or
            member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
          raise ValueError("invalid sound archive member")
        raw_names.add(name)
        if (name == "sounds/" and wrapped and member.is_dir() and member.file_size == 0 and
            (mode == 0 or stat.S_IFMT(mode) in (0, stat.S_IFDIR))):
          continue
        if wrapped and re.fullmatch(r"__MACOSX/sounds/\._[A-Za-z0-9_]+\.wav", name):
          if member.is_dir() or member.file_size > 512 or (mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
            raise ValueError("invalid sound archive member")
          metadata.add(name.removeprefix("__MACOSX/sounds/._"))
          continue
        filename = name.removeprefix("sounds/") if wrapped else name
        if (name != ("sounds/" + filename if wrapped else filename) or filename not in ALLOWED_FILES or
            filename in names or member.is_dir() or (mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG)) or
            member.file_size <= 0 or member.file_size > MAX_WAV_BYTES):
          raise ValueError("invalid sound archive member")
        names.add(filename)
        audio.append((member, filename))
        total += member.file_size
        if total > MAX_EXPANDED_BYTES:
          raise ValueError("sound archive too large")
      if not audio:
        raise ValueError("sound archive contains no WAV files")
      if not metadata <= names:
        raise ValueError("invalid sound archive metadata")
      for member, filename in audio:
        with source.open(member) as data, (sounds / filename).open("xb") as output:
          remaining = member.file_size
          while remaining:
            self._check_active()
            chunk = data.read(min(CHUNK, remaining + 1))
            if not chunk or len(chunk) > remaining:
              raise ValueError("sound file length mismatch")
            output.write(chunk)
            remaining -= len(chunk)
          if data.read(1):
            raise ValueError("sound file length mismatch")
        read_wav(sounds / filename)

  def close(self):
    with self._lock:
      self._closed = True
      self._cancel.set()
      thread = self._thread
    if thread is not None:
      thread.join(timeout=2)
