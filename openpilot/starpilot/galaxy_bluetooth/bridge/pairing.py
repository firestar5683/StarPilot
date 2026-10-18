"""Local-only pairing credentials shared by comma UI and BLE bridge.

Every phone gets its own key, so one phone can be forgotten without the others.
The file is {"version": 2, "phones": [{"id", "key", "label", "added", "last_used"}]}.
A version 1 file ({"key": ...}) is read as one phone, so phones paired before this
change keep working until it is forgotten.
"""
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
from contextlib import contextmanager

DEFAULT_KEY_PATH = Path("/data/galaxy-ble/pairing.json")
MAX_PHONES = 16
MAX_FILE_BYTES = 16384
LEGACY_ID = "legacy"
LEGACY_LABEL = "Phones paired before update"
UNUSED_GRACE = datetime.timedelta(hours=1)  # A code that was shown but never scanned.
PHONE_ID = re.compile(r"[0-9a-f]{8}")
BT_ADDRESS = re.compile(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}")


def clean_name(name):
  """A phone-supplied name, safe to show in comma's UI, or None."""
  if not isinstance(name, str):
    return None
  name = "".join(ch for ch in name if ch.isprintable()).strip()[:40]
  return name or None


def valid_replaces(phone_id):
  # Only per-phone ids; the shared pre-update entry may still serve other phones.
  return isinstance(phone_id, str) and PHONE_ID.fullmatch(phone_id) is not None


def _now():
  return datetime.datetime.now().replace(microsecond=0)


def _key(text):
  if not isinstance(text, str) or len(text) != 64:
    raise ValueError("Invalid pairing key")
  key = bytes.fromhex(text)
  if len(key) != 32:
    raise ValueError("Invalid pairing key")
  return key


def _read(path):
  fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
  with os.fdopen(fd) as stream:
    info = os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
      raise ValueError("Pairing file must be a private regular file")
    raw = stream.read(MAX_FILE_BYTES + 1)
  if len(raw) > MAX_FILE_BYTES:
    raise ValueError("Pairing file is too large")
  value = json.loads(raw)
  if not isinstance(value, dict):
    raise ValueError("Invalid pairing file")
  if "phones" not in value:
    return [{"id": LEGACY_ID, "key": _key(value.get("key")), "label": LEGACY_LABEL, "added": "", "last_used": ""}]
  phones = []
  for phone in value["phones"]:
    if not isinstance(phone, dict) or not isinstance(phone.get("id"), str) or not phone["id"]:
      raise ValueError("Invalid pairing file")
    entry = {"id": phone["id"], "key": _key(phone.get("key")), "label": str(phone.get("label", "Phone"))[:64],
             "added": str(phone.get("added", "")), "last_used": str(phone.get("last_used", ""))}
    # The phone's Bluetooth address, set when its app and music pairing happen in one window.
    address = str(phone.get("bt_address", "")).upper()
    if BT_ADDRESS.fullmatch(address):
      entry["bt_address"] = address
    phones.append(entry)
  return phones


def load_phones(path=DEFAULT_KEY_PATH):
  return _read(Path(path))


def load_keys(path=DEFAULT_KEY_PATH):
  return {phone["id"]: phone["key"] for phone in load_phones(path)}


@contextmanager
def _locked(path):
  path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
  fd = os.open(path.with_suffix(".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
  with os.fdopen(fd, "w") as stream:
    fcntl.flock(stream, fcntl.LOCK_EX)
    yield


def _write(path, phones):
  fd, tmp = tempfile.mkstemp(prefix=".pairing-", dir=path.parent)
  try:
    with os.fdopen(fd, "w") as stream:
      os.fchmod(stream.fileno(), 0o600)
      json.dump({"version": 2, "phones": [{**phone, "key": phone["key"].hex()} for phone in phones]}, stream)
      stream.flush()
      os.fsync(stream.fileno())
    os.replace(tmp, path)
  finally:
    if os.path.exists(tmp):
      os.unlink(tmp)


def _load_or_empty(path):
  try:
    return _read(path)
  except FileNotFoundError:
    return []


def ensure_store(path=DEFAULT_KEY_PATH):
  """Create an empty store so the bridge can run before any phone is paired."""
  path = Path(path)
  with _locked(path):
    phones = _load_or_empty(path)
    if not path.exists():
      _write(path, phones)
    return phones


def add_phone(label, path=DEFAULT_KEY_PATH, replaces=None):
  """Issue a new key for one phone and return (id, key). `replaces` drops that phone's previous entry."""
  path = Path(path)
  with _locked(path):
    now = _now()
    phones = []
    for phone in _load_or_empty(path):
      if valid_replaces(replaces) and phone["id"] == replaces:
        continue
      try:
        stale = not phone["last_used"] and phone["added"] and now - datetime.datetime.fromisoformat(phone["added"]) > UNUSED_GRACE
      except ValueError:
        stale = False
      if not stale:
        phones.append(phone)
    if len(phones) >= MAX_PHONES:
      raise ValueError("Too many phones. Forget one first.")
    key = secrets.token_bytes(32)
    phone_id = secrets.token_hex(4)
    phones.append({"id": phone_id, "key": key, "label": clean_name(label) or "Phone", "added": now.isoformat(), "last_used": ""})
    _write(path, phones)
    return phone_id, key


def remove_phone(phone_id, path=DEFAULT_KEY_PATH):
  path = Path(path)
  with _locked(path):
    phones = _load_or_empty(path)
    kept = [phone for phone in phones if phone["id"] != phone_id]
    if len(kept) != len(phones):
      _write(path, kept)
    return len(kept) != len(phones)


def forget_all(path=DEFAULT_KEY_PATH):
  path = Path(path)
  with _locked(path):
    _write(path, [])


def introduce(phone_id, name=None, replaces=None, path=DEFAULT_KEY_PATH):
  """A connected phone names itself and drops the entry its new key replaced."""
  name = clean_name(name)
  path = Path(path)
  with _locked(path):
    phones = _load_or_empty(path)
    changed = False
    if valid_replaces(replaces) and replaces != phone_id and any(phone["id"] == replaces for phone in phones):
      phones = [phone for phone in phones if phone["id"] != replaces]
      changed = True
    for phone in phones:
      if phone["id"] == phone_id and name and phone["id"] != LEGACY_ID and phone["label"] != name:
        phone["label"] = name
        changed = True
    if changed:
      _write(path, phones)
    return changed


def mark_used(phone_id, path=DEFAULT_KEY_PATH):
  path = Path(path)
  today = _now().date().isoformat()
  with _locked(path):
    phones = _load_or_empty(path)
    for phone in phones:
      if phone["id"] == phone_id and phone["last_used"] != today:
        phone["last_used"] = today
        _write(path, phones)
        return


def describe(phone):
  """Short UI label, unique per phone: "iPhone · added Oct 16 14:02"."""
  try:
    added = datetime.datetime.fromisoformat(phone["added"]).strftime("%b %d %H:%M")
  except ValueError:
    return phone["label"]
  return f"{phone['label']} · added {added}"


def link_address(phone_id, address, path=DEFAULT_KEY_PATH):
  """Remember which Bluetooth device is this app's phone, so forgetting one forgets both."""
  address = str(address).upper()
  if not BT_ADDRESS.fullmatch(address):
    return False
  path = Path(path)
  with _locked(path):
    phones = _load_or_empty(path)
    for phone in phones:
      if phone["id"] == phone_id and phone["id"] != LEGACY_ID:
        phone["bt_address"] = address
        _write(path, phones)
        return True
  return False


def remove_by_address(address, path=DEFAULT_KEY_PATH):
  """Forget the app key of the phone that has this Bluetooth address. Returns how many were removed."""
  address = str(address).upper()
  path = Path(path)
  with _locked(path):
    phones = _load_or_empty(path)
    kept = [phone for phone in phones if phone.get("bt_address") != address]
    if len(kept) != len(phones):
      _write(path, kept)
    return len(phones) - len(kept)


def app_only(path=DEFAULT_KEY_PATH):
  """Phones that have an app key but no known Bluetooth device (older pairings, or the app only)."""
  try:
    return [phone for phone in load_phones(path) if "bt_address" not in phone]
  except (OSError, ValueError):
    return []
