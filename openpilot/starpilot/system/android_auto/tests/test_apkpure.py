import io
import threading
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from openpilot.starpilot.system.android_auto import apkpure
from openpilot.starpilot.system.android_auto.apk_identity import MAX_FILE_BYTES, PACKAGE

NOW = datetime(2026, 10, 11, tzinfo=UTC).timestamp()
EXPIRES = "2026-10-14T02:41:31+00:00"
LINK = "https://download.pureapk.com/b/XAPK/Y29t?_fn=QW5k&k=c413&c=1%7CAUTO"


def varint(value):
  out = bytearray()
  while True:
    byte = value & 0x7F
    value >>= 7
    out.append(byte | (0x80 if value else 0))
    if not value:
      return bytes(out)


def field(number, value):
  if isinstance(value, int):
    return varint(number << 3) + varint(value)
  data = value.encode() if isinstance(value, str) else value
  return varint(number << 3 | 2) + varint(len(data)) + data


def release(version="17.7.663654-release", code=177663654, url=LINK, size=50281364, expires=EXPIRES, package=PACKAGE):
  asset = field(1, expires) + field(4, size) + field(8, "XAPK") + field(9, url)
  return field(4, package) + field(5, str(code)) + field(6, version) + field(13, "Google LLC") + field(24, asset)


def response(*releases):
  # Shaped like the real reply: 1 → 7 → repeated 2 {1 "version_list", 3 → 2 app}
  items = b"".join(field(2, field(1, "version_list") + field(3, field(2, item))) for item in releases)
  return field(1, field(7, field(1, field(2, 1)) + items))


def test_parses_newest_release_first():
  body = response(release("17.6.663454-release", 176663454), release(), release("17.7.663653-release", 177663653))
  releases = apkpure.parse_releases(body)
  assert [item["version"] for item in releases] == ["17.7.663654-release", "17.7.663653-release", "17.6.663454-release"]
  assert releases[0] == {"version": "17.7.663654-release", "code": 177663654, "url": LINK, "size": 50281364,
                         "expires": datetime.fromisoformat(EXPIRES).timestamp()}


@pytest.mark.parametrize("bad", [
  {"url": LINK.replace("https://", "http://")},
  {"url": LINK.replace("download.pureapk.com", "download.pureapk.com.evil.test")},
  {"url": LINK.replace("download.pureapk.com", "user@download.pureapk.com")},
  {"url": LINK.replace("download.pureapk.com", "download.pureapk.com:8443")},
  {"url": LINK.replace("/b/XAPK/", "/b/EXE/")},
  {"url": LINK + "#frag"},
  {"url": LINK + " x"},
  {"version": "17.8.663804-beta"},
  {"version": "17.8.163804-release.daily"},
  {"package": "com.google.android.gms"},
  {"size": 0},
  {"size": MAX_FILE_BYTES + 1},
  {"expires": "soon"},
])
def test_rejects_untrusted_or_unusable_entries(bad):
  assert apkpure.parse_releases(response(release(**bad))) == []


@pytest.mark.parametrize("body", [b"", b"\xff\xff\xff", b"\x0a\x7f", b"<html>Just a moment</html>"])
def test_garbage_bodies_yield_nothing(body):
  assert apkpure.parse_releases(body) == []


def fake_open(body):
  opener = Mock()
  opener.open.return_value.__enter__ = lambda self: io.BytesIO(body)
  opener.open.return_value.__exit__ = lambda self, *args: False
  return opener


def test_fetch_skips_links_about_to_expire(monkeypatch):
  soon = datetime.fromtimestamp(NOW + 600, UTC).isoformat()
  body = response(release(expires=soon), release("17.6.663454-release", 176663454))
  opener = fake_open(body)
  monkeypatch.setattr(apkpure.urllib.request, "build_opener", lambda *handlers: opener)
  latest = apkpure.fetch_latest(now=NOW)
  assert latest is not None
  assert latest["version"] == "17.6.663454-release"
  request = opener.open.call_args.args[0]
  assert request.full_url == apkpure.API_URL and request.get_header("X-sv") == "29"
  assert request.get_header("User-agent") == "StarPilot-AndroidAuto/1"


def test_fetch_failures_return_none(monkeypatch):
  monkeypatch.setattr(apkpure.urllib.request, "build_opener", lambda *handlers: fake_open(b"x" * (apkpure.MAX_BODY_BYTES + 1)))
  assert apkpure.fetch_latest(now=NOW) is None
  def offline(*handlers):
    raise OSError("offline")
  monkeypatch.setattr(apkpure.urllib.request, "build_opener", offline)
  assert apkpure.fetch_latest(now=NOW) is None


def test_redirects_are_rejected():
  with pytest.raises(ValueError):
    apkpure._NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://apkpure.com/challenge")


@pytest.fixture
def cache(monkeypatch):
  monkeypatch.setattr(apkpure, "_cache", None)
  monkeypatch.setattr(apkpure, "_refresh_after", 0.0)
  monkeypatch.setattr(apkpure, "_in_flight", False)
  monkeypatch.setattr(apkpure, "_sleep", lambda delay: None)


def run_refresh(monkeypatch, result, clock):
  calls = []
  def fetch():
    calls.append(1)
    return result
  monkeypatch.setattr(apkpure, "fetch_latest", fetch)
  started = []
  class Inline:
    def __init__(self, target, **kwargs): self.target = target
    def start(self):
      started.append(1)
      self.target()
  monkeypatch.setattr(apkpure.threading, "Thread", Inline)
  apkpure.start_background_refresh(now=lambda: clock[0])
  return calls


def test_cache_ttls_follow_link_expiry_and_failures(monkeypatch, cache):
  clock = [100.0]
  monkeypatch.setattr(apkpure, "_now", lambda: NOW)
  good = {"version": "17.7.663654-release", "code": 1, "url": LINK, "size": 5, "expires": NOW + 2 * 3600}
  assert run_refresh(monkeypatch, good, clock) == [1]
  assert apkpure._refresh_after == pytest.approx(100.0 + 3600)  # refresh when the link enters its last hour
  assert apkpure.download_status(now=NOW) == {"version": "17.7.663654-release", "url": LINK, "size": 5}
  assert apkpure.download_status(now=NOW + 3601) is None
  assert run_refresh(monkeypatch, None, clock) == []  # still fresh
  clock[0] = apkpure._refresh_after
  assert run_refresh(monkeypatch, None, clock) == [1, 1, 1]  # three tries before giving up
  assert apkpure.download_status(now=NOW) is None
  assert apkpure._refresh_after == pytest.approx(clock[0] + apkpure.FAILURE_TTL)
  clock[0] += apkpure.FAILURE_TTL
  run_refresh(monkeypatch, {**good, "expires": NOW + 3 * 86400}, clock)
  assert apkpure._refresh_after == pytest.approx(clock[0] + apkpure.SUCCESS_TTL)


def test_refresh_retries_before_giving_up_and_reports_pending(monkeypatch, cache):
  monkeypatch.setattr(apkpure, "_now", lambda: NOW)
  good = {"version": "17.7.663654-release", "code": 1, "url": LINK, "size": 5, "expires": NOW + 2 * 86400}
  results, waits, pending = [None, good], [], []
  def fetch():
    pending.append(apkpure.lookup_pending())
    return results.pop(0)
  monkeypatch.setattr(apkpure, "fetch_latest", fetch)
  monkeypatch.setattr(apkpure, "_sleep", waits.append)
  class Inline:
    def __init__(self, target, **kwargs): self.target = target
    def start(self): self.target()
  monkeypatch.setattr(apkpure.threading, "Thread", Inline)
  assert not apkpure.lookup_pending()
  apkpure.start_background_refresh(now=lambda: 0.0)
  assert waits == [apkpure.RETRY_DELAYS[0]]
  assert pending == [True, True]  # the page waits while tries remain
  assert not apkpure.lookup_pending()
  status = apkpure.download_status()
  assert status is not None
  assert status["url"] == LINK


def test_refresh_is_single_flight(monkeypatch, cache):
  entered, release_fetch = threading.Event(), threading.Event()
  calls = []
  def fetch():
    calls.append(1)
    entered.set()
    release_fetch.wait(2)
  monkeypatch.setattr(apkpure, "fetch_latest", fetch)
  apkpure.start_background_refresh()
  assert entered.wait(2)
  apkpure.start_background_refresh()
  release_fetch.set()
  for thread in threading.enumerate():
    if thread.name == "aa-apkpure":
      thread.join(2)
  assert calls == [1, 1, 1]  # one lookup's three tries; the second start didn't add another


def test_version_for_size_names_only_an_exact_size_match(monkeypatch, cache):
  assert apkpure.version_for_size(5) is None
  monkeypatch.setattr(apkpure, "_cache", {"version": "17.7.663654-release", "code": 1, "url": LINK, "size": 5, "expires": NOW})
  assert apkpure.version_for_size(5) == "17.7.663654-release"  # an expired link still names the file it pointed to
  assert apkpure.version_for_size(6) is None
