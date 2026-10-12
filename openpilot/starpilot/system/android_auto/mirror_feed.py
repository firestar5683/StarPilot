"""Optional APKMirror release hints. Only the RSS feed is read, never app pages."""
from __future__ import annotations

import logging
import re
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC
from email.utils import parsedate_to_datetime

from openpilot.starpilot.system.android_auto.apk_identity import (
  COMPATIBLE_RELEASE_URL, COMPATIBLE_VERSION_PREFIXES, KNOWN_GOOD_VERSION,
)

FEED_URL = "https://www.apkmirror.com/apk/google-inc/android-auto/feed/"
LISTING_URL = "https://www.apkmirror.com/apk/google-inc/android-auto/"
RELEASE_LINK = re.compile(r"https://www\.apkmirror\.com/apk/google-inc/android-auto/android-auto-(\d+(?:-\d+)+)-release/", re.ASCII)
MAX_FEED_BYTES = 256 * 1024
SUCCESS_TTL = 6 * 3600
FAILURE_TTL = 15 * 60

_lock = threading.Lock()
_cache: list[dict] | None = None
_refresh_after = 0.0
_in_flight = False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self, req, fp, code, msg, headers, newurl):
    raise ValueError("RSS redirect rejected")


def fetch_releases(timeout: float = 10) -> list[dict] | None:
  """Read bounded public RSS; failures mean the existing manual flow stays available."""
  try:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(FEED_URL, headers={
      "User-Agent": "StarPilot-AndroidAuto/1", "Accept": "application/rss+xml",
    })
    with opener.open(request, timeout=timeout) as response:
      body = response.read(MAX_FEED_BYTES + 1)
    if len(body) > MAX_FEED_BYTES or re.search(br"<!\s*(DOCTYPE|ENTITY)\b", body.replace(b"\x00", b""), re.I):
      raise ValueError("Unsafe RSS body")
    root = ET.fromstring(body)
    if root.tag != "rss" or root.find("channel") is None:
      raise ValueError("Not an RSS feed")
    releases = []
    seen = set()
    for item in root.findall("channel/item"):
      if re.search(r"\b(beta|alpha)\b", item.findtext("title", ""), re.I):
        continue
      url = item.findtext("link", "")
      match = RELEASE_LINK.fullmatch(url)
      if match is None or url in seen:
        continue
      seen.add(url)
      try:
        date = parsedate_to_datetime(item.findtext("pubDate", ""))
        published = date.replace(tzinfo=date.tzinfo or UTC).astimezone(UTC).isoformat()
      except (ValueError, TypeError, OverflowError):
        published = None
      releases.append({"version": match[1].replace("-", "."), "url": url, "published": published})
    return sorted(releases, key=lambda release: release["published"] or "", reverse=True)
  except Exception as error:
    # Do not include response bodies, URLs from errors, or challenge text in logs.
    logging.getLogger(__name__).debug("Android Auto mirror feed unavailable: %s", type(error).__name__)
    return None


def cached_releases() -> list[dict] | None:
  """Return a snapshot without any network work."""
  with _lock:
    return None if _cache is None else [dict(release) for release in _cache]


def start_background_refresh(now=time.monotonic) -> None:
  """Single-flight refresh, lazily started by the setup page. Never delay setup on I/O."""
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
        result = fetch_releases()
      except Exception:
        pass  # Optional hints must not surface background thread failures.
      finally:
        with _lock:
          _cache = result
          _refresh_after = now() + (SUCCESS_TTL if result is not None else FAILURE_TTL)
          _in_flight = False

    threading.Thread(target=refresh, name="aa-mirror-feed", daemon=True).start()
  except Exception:
    with _lock:
      _in_flight = False
      _refresh_after = time.monotonic() + FAILURE_TTL


def mirror_status() -> dict | None:
  releases = cached_releases()
  if not releases:
    return None
  compatible = next((release for release in releases if release["version"].startswith(COMPATIBLE_VERSION_PREFIXES)),
                    {"version": KNOWN_GOOD_VERSION, "url": COMPATIBLE_RELEASE_URL})
  return {"latest": {key: releases[0][key] for key in ("version", "url")},
          "compatible": {key: compatible[key] for key in ("version", "url")}}
