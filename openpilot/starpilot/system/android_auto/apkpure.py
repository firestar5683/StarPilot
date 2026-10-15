"""Finds the newest Android Auto download link on APKPure for the user's browser.

The comma only reads APKPure's release list. The user's phone or computer downloads
the app itself and uploads it as before, so the comma never fetches the package.
Any failure leaves the upload path working; nothing here affects identity checks.
"""
from __future__ import annotations

import logging
import re
import threading
import time
import urllib.request
from datetime import UTC, datetime
from urllib.parse import urlsplit

from openpilot.starpilot.system.android_auto.apk_identity import MAX_FILE_BYTES, PACKAGE

API_URL = f"https://api.pureapk.com/m/v3/cms/app_version?hl=en-US&package_name={PACKAGE}"
# x-sv (the Android SDK level) is the only header the API requires; x-abis asks for arm64 builds.
HEADERS = {"User-Agent": "StarPilot-AndroidAuto/1", "x-sv": "29", "x-abis": "arm64-v8a"}
DOWNLOAD_HOST = "download.pureapk.com"
VERSION = re.compile(r"[0-9]+(?:\.[0-9]+)+-release", re.ASCII)
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_DEPTH = 8
SUCCESS_TTL = 6 * 3600
FAILURE_TTL = 60  # a failed lookup (e.g. at boot before the clock syncs) retries soon
RETRY_DELAYS = (3, 8)  # three tries before the page falls back to APKMirror
LINK_MARGIN = 3600  # never hand out a link that expires within the hour

_lock = threading.Lock()
_cache: dict | None = None
_refresh_after = 0.0
_in_flight = False
_sleep = time.sleep


def _now() -> float:
  # Link expiry is an absolute time, so this compares against the wall clock.
  return datetime.now(UTC).timestamp()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self, req, fp, code, msg, headers, newurl):
    raise ValueError("APKPure redirect rejected")


def _varint(data: bytes, index: int) -> tuple[int, int]:
  value = shift = 0
  while shift < 64:
    byte = data[index]
    index += 1
    value |= (byte & 0x7F) << shift
    if byte < 0x80:
      return value, index
    shift += 7
  raise ValueError("Bad varint")


def _fields(data: bytes) -> list[tuple[int, int | bytes]]:
  """Decode one protobuf message into (field, value); raises ValueError if it isn't one."""
  fields = []
  index = 0
  while index < len(data):
    key, index = _varint(data, index)
    number, kind = key >> 3, key & 7
    if number == 0:
      raise ValueError("Bad field")
    if kind == 0:
      value, index = _varint(data, index)
    elif kind == 2:
      size, index = _varint(data, index)
      if index + size > len(data):
        raise ValueError("Truncated field")
      value, index = data[index:index + size], index + size
    elif kind in (1, 5):
      size = 8 if kind == 1 else 4
      if index + size > len(data):
        raise ValueError("Truncated field")
      value, index = data[index:index + size], index + size
    else:
      raise ValueError("Unsupported wire type")
    fields.append((number, value))
  return fields


def _text(fields, number: int) -> str:
  value = next((value for field, value in fields if field == number and isinstance(value, bytes)), b"")
  return value.decode("utf-8", "strict")


def _release(fields) -> dict | None:
  """An app-version message: 4 package, 5 version code, 6 version name, 24 asset (1 expiry, 4 size, 9 link)."""
  try:
    if _text(fields, 4) != PACKAGE or not VERSION.fullmatch(version := _text(fields, 6)):
      return None
    code = int(_text(fields, 5))
    asset = _fields(next(value for field, value in fields if field == 24 and isinstance(value, bytes)))
    url = _text(asset, 9)
    size = next((value for field, value in asset if field == 4 and isinstance(value, int)), 0)
    expires = datetime.fromisoformat(_text(asset, 1)).astimezone(UTC)
  except (StopIteration, ValueError, IndexError, UnicodeDecodeError):
    return None
  parsed = urlsplit(url)
  if (parsed.scheme != "https" or parsed.hostname != DOWNLOAD_HOST or parsed.port is not None or parsed.username
      or parsed.password or parsed.fragment or not parsed.path.startswith(("/b/XAPK/", "/b/APK/")) or len(url) > 4096
      or any(ord(char) <= 0x20 or ord(char) >= 0x7F for char in url)):
    return None
  if not 0 < size <= MAX_FILE_BYTES:
    return None
  return {"version": version, "code": code, "url": url, "size": size, "expires": expires.timestamp()}


def parse_releases(body: bytes) -> list[dict]:
  """Every valid Android Auto release in an APKPure app_version response, newest first."""
  releases = []
  pending = [(body, 0)]
  while pending:
    data, depth = pending.pop()
    try:
      fields = _fields(data)
    except (ValueError, IndexError):
      continue
    if (release := _release(fields)) is not None:
      releases.append(release)
      continue
    if depth < MAX_DEPTH:
      pending.extend((value, depth + 1) for _, value in fields if isinstance(value, bytes) and len(value) > 1)
  return sorted(releases, key=lambda release: release["code"], reverse=True)


def fetch_latest(timeout: float = 10, now: float | None = None) -> dict | None:
  """The newest release whose link is still valid; None if APKPure can't be used right now."""
  try:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    with opener.open(urllib.request.Request(API_URL, headers=HEADERS), timeout=timeout) as response:
      body = response.read(MAX_BODY_BYTES + 1)
    if len(body) > MAX_BODY_BYTES:
      raise ValueError("APKPure response too large")
    now = _now() if now is None else now
    return next((release for release in parse_releases(body) if release["expires"] - LINK_MARGIN > now), None)
  except Exception as error:
    # Never log response bodies or signed links.
    logging.getLogger(__name__).debug("APKPure release list unavailable: %s", type(error).__name__)
    return None


def start_background_refresh(now=time.monotonic) -> None:
  """Single-flight refresh, started lazily by the setup page. Never delays setup on network I/O."""
  global _in_flight, _refresh_after
  try:
    with _lock:
      if _in_flight or now() < _refresh_after:
        return
      _in_flight = True

    def refresh():
      global _cache, _in_flight, _refresh_after
      result = None
      try:
        for delay in (*RETRY_DELAYS, None):
          if (result := fetch_latest()) is not None or delay is None:
            break
          _sleep(delay)
      except Exception:
        pass  # The upload path must keep working when the hint is unavailable.
      finally:
        with _lock:
          _cache = result
          ttl = FAILURE_TTL if result is None else max(FAILURE_TTL, min(SUCCESS_TTL, result["expires"] - LINK_MARGIN - _now()))
          _refresh_after = now() + ttl
          _in_flight = False

    threading.Thread(target=refresh, name="aa-apkpure", daemon=True).start()
  except Exception:
    with _lock:
      _in_flight = False
      _refresh_after = time.monotonic() + FAILURE_TTL


def lookup_pending() -> bool:
  """True while a lookup is still trying and there's no usable link to show yet."""
  with _lock:
    in_flight = _in_flight
  return in_flight and download_status() is None


def download_status(now: float | None = None) -> dict | None:
  """The cached link for the browser, without any network work."""
  with _lock:
    release = None if _cache is None else dict(_cache)
  if release is None or release["expires"] - LINK_MARGIN <= (_now() if now is None else now):
    return None
  return {"version": release["version"], "url": release["url"], "size": release["size"]}


def version_for_size(size: int) -> str | None:
  """The cached release's version when a package has exactly its size; a display label only."""
  with _lock:
    release = _cache
  return release["version"] if release is not None and release["size"] == size else None
