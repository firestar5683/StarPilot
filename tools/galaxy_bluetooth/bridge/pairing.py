"""Local-only pairing credentials shared by comma UI and BLE bridge."""
import fcntl
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile
from contextlib import contextmanager

DEFAULT_KEY_PATH = Path("/data/galaxy-ble/pairing.json")


def load_key(path=DEFAULT_KEY_PATH):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError("Pairing file must be a private regular file")
        raw = stream.read(1025)
        if len(raw) > 1024:
            raise ValueError("Pairing file is too large")
        key_text = json.loads(raw)["key"]
        if not isinstance(key_text, str) or len(key_text) != 64:
            raise ValueError("Invalid pairing key")
        key = bytes.fromhex(key_text)
        if len(key) != 32:
            raise ValueError("Invalid pairing key")
        return key


@contextmanager
def _locked(path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path.with_suffix(".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def _write_key(path, key):
    fd, tmp = tempfile.mkstemp(prefix=".pairing-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump({"key": key.hex()}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def ensure_key(path=DEFAULT_KEY_PATH):
    path = Path(path)
    with _locked(path):
        try:
            return load_key(path)
        except FileNotFoundError:
            key = secrets.token_bytes(32)
            _write_key(path, key)
            return key


def rotate_key(path=DEFAULT_KEY_PATH):
    path = Path(path)
    with _locked(path):
        key = secrets.token_bytes(32)
        _write_key(path, key)
        return key


def qr_payload(key):
    if len(key) != 32:
        raise ValueError("Invalid pairing key")
    return json.dumps({"type": "galaxy-bluetooth", "version": 1, "key": key.hex()}, separators=(",", ":"))
