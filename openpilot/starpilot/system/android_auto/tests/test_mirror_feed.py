import io
import threading
import urllib.error
from pathlib import Path
from unittest.mock import Mock

import pytest

from openpilot.starpilot.system.android_auto import mirror_feed as feed

FIXTURE = Path(__file__).with_name("fixtures") / "apkmirror_feed.xml"


@pytest.fixture
def cache(monkeypatch):
  threads = []
  thread_class = threading.Thread

  def thread(**kwargs):
    instance = thread_class(**kwargs)
    threads.append(instance)
    return instance

  monkeypatch.setattr(feed.threading, "Thread", thread)
  monkeypatch.setattr(feed, "_cache", None)
  monkeypatch.setattr(feed, "_refresh_after", 0)
  monkeypatch.setattr(feed, "_in_flight", False)
  yield threads
  for instance in threads:
    instance.join(timeout=2)
    assert not instance.is_alive()


def serve(monkeypatch, body):
  opener = Mock()
  opener.open.return_value = io.BytesIO(body)
  build = Mock(return_value=opener)
  monkeypatch.setattr(feed.urllib.request, "build_opener", build)
  return opener, build


def test_real_trimmed_feed(monkeypatch):
  opener, build = serve(monkeypatch, FIXTURE.read_bytes())
  releases = feed.fetch_releases(timeout=3)
  assert [item["version"] for item in releases] == ["17.9.6640", "17.7.6636", "17.8.6638"]
  assert releases[0]["published"] == "2026-10-07T17:09:49+00:00"
  request = opener.open.call_args.args[0]
  assert request.full_url == feed.FEED_URL
  assert request.get_header("User-agent") == "StarPilot-AndroidAuto/1"
  assert request.get_header("Accept") == "application/rss+xml"
  assert opener.open.call_args.kwargs == {"timeout": 3}
  assert build.call_args.args[0].proxies == {}


def xml_item(url, title="Android Auto", published="invalid"):
  return f"<rss><channel><item><title>{title}</title><link>{url}</link><pubDate>{published}</pubDate></item></channel></rss>".encode()


@pytest.mark.parametrize("url", [
  "https://evil.test/apk/google-inc/android-auto/android-auto-17-9-6640-release/",
  "http://www.apkmirror.com/apk/google-inc/android-auto/android-auto-17-9-6640-release/",
  "https://www.apkmirror.com/apk/google-inc/maps/android-auto-17-9-6640-release/",
  "https://www.apkmirror.com/apk/google-inc/android-auto/android-auto-17-9-6640-release/#respond",
  "https://www.apkmirror.com/apk/google-inc/android-auto/android-auto-17-9-6640-release/junk",
  "https://www.apkmirror.com/apk/google-inc/android-auto/android-auto-17-9-6640-release/\n",
])
def test_reject_non_release_links(monkeypatch, url):
  serve(monkeypatch, xml_item(url))
  assert feed.fetch_releases() == []


@pytest.mark.parametrize("title", ["Android Auto ALPHA", "Android Auto beta"])
def test_skip_prereleases(monkeypatch, title):
  serve(monkeypatch, xml_item(feed.LISTING_URL + "android-auto-17-9-6640-release/", title))
  assert feed.fetch_releases() == []


def test_invalid_date_is_optional(monkeypatch):
  serve(monkeypatch, xml_item(feed.LISTING_URL + "android-auto-17-9-6640-release/"))
  assert feed.fetch_releases()[0]["published"] is None


@pytest.mark.parametrize("body", [
  b'<!DOCTYPE rss><rss/>', b'<!ENTITY foo "bar"><rss/>',
  '<!DOCTYPE rss [<!ENTITY foo "bar">]><rss/>'.encode("utf-16"),
  b" " * (feed.MAX_FEED_BYTES + 1), b"<rss>", b"<html>Challenge</html>",
])
def test_bounded_safe_parsing(monkeypatch, body):
  serve(monkeypatch, body)
  assert feed.fetch_releases() is None


@pytest.mark.parametrize("error", [TimeoutError(), urllib.error.HTTPError(feed.FEED_URL, 403, "blocked", {}, None)])
def test_network_failure_is_optional(monkeypatch, error):
  opener, _ = serve(monkeypatch, b"")
  opener.open.side_effect = error
  assert feed.fetch_releases() is None


def test_feed_does_not_follow_redirects():
  with pytest.raises(ValueError):
    feed._NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://www.apkmirror.com/challenge")


@pytest.mark.parametrize("result,ttl", [([], feed.SUCCESS_TTL), (None, feed.FAILURE_TTL)])
def test_cache_ttl_and_no_synchronous_fetch(monkeypatch, cache, result, ttl):
  fetch = Mock(return_value=result)
  monkeypatch.setattr(feed, "fetch_releases", fetch)
  clock = [100.0]
  assert feed.cached_releases() is None
  fetch.assert_not_called()
  feed.start_background_refresh(now=lambda: clock[0])
  cache[-1].join(2)
  assert feed.cached_releases() == result
  clock[0] += ttl - 1
  feed.start_background_refresh(now=lambda: clock[0])
  assert fetch.call_count == 1
  clock[0] += 1
  feed.start_background_refresh(now=lambda: clock[0])
  cache[-1].join(2)
  assert fetch.call_count == 2


def test_single_flight_and_fallback_after_failure(monkeypatch, cache):
  entered, release = threading.Event(), threading.Event()
  fetch = Mock()
  def blocked():
    entered.set()
    assert release.wait(2)
    return [{"version": "17.9.6640", "url": feed.LISTING_URL + "android-auto-17-9-6640-release/"}]
  fetch.side_effect = blocked
  monkeypatch.setattr(feed, "fetch_releases", fetch)
  callers = [threading.Thread(target=feed.start_background_refresh) for _ in range(2)]
  try:
    for caller in callers:
      caller.start()
    assert entered.wait(2)
    for caller in callers:
      caller.join(2)
    assert fetch.call_count == 1
    assert feed.cached_releases() is None
  finally:
    release.set()
  for instance in cache:
    instance.join(2)
  assert feed.mirror_status()["compatible"] == {"version": feed.KNOWN_GOOD_VERSION, "url": feed.COMPATIBLE_RELEASE_URL}
  snapshot = feed.cached_releases()
  snapshot[0]["url"] = "changed"
  assert feed.cached_releases()[0]["url"] != "changed"
  monkeypatch.setattr(feed, "_refresh_after", 0)
  fetch.side_effect = None
  fetch.return_value = None
  feed.start_background_refresh()
  cache[-1].join(2)
  assert feed.mirror_status() is None


def test_compatible_feed_release(monkeypatch, cache):
  monkeypatch.setattr(feed, "_cache", [
    {"version": "17.9.6640", "url": feed.LISTING_URL + "android-auto-17-9-6640-release/"},
    {"version": "17.6.6634", "url": feed.COMPATIBLE_RELEASE_URL},
  ])
  assert feed.mirror_status()["latest"]["version"] == "17.9.6640"
  assert feed.mirror_status()["compatible"] == {"version": "17.6.6634", "url": feed.COMPATIBLE_RELEASE_URL}


def test_thread_start_failure_never_breaks_setup(monkeypatch, cache):
  monkeypatch.setattr(feed.threading, "Thread", Mock(side_effect=RuntimeError("no threads")))
  feed.start_background_refresh()
  assert not feed._in_flight
  assert feed.mirror_status() is None
