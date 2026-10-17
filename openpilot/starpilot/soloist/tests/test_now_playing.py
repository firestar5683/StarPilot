import json

from openpilot.starpilot.soloist import now_playing
from openpilot.starpilot.system.android_auto.projection_now_playing import ProjectionNowPlayingFeed

PLAYER = {'loggedIn': True, 'active': True, 'status': 'playing',
          'track': {'title': 'Midnight City', 'artists': 'M83', 'album': 'Hurry Up', 'durationMs': 243000},
          'position': {'ms': 10000, 'at': 1000, 'speed': 1.0}}


def test_spotify_snapshot_needs_an_active_logged_in_player():
  found = now_playing.from_spotify(PLAYER)
  assert found['source'] == 'spotify' and found['title'] == 'Midnight City' and found['artist'] == 'M83'
  for change in ({'loggedIn': False}, {'active': False}, {'status': 'idle'}, {'track': None}):
    assert now_playing.from_spotify({**PLAYER, **change}) is None
  assert now_playing.from_spotify(None) is None


def test_phone_snapshot_reads_bluez_media_player():
  props = {'Status': 'playing', 'Position': 5000, 'Track': {'Title': 'Song', 'Artist': 'Band', 'Album': 'LP', 'Duration': 200000}}
  found = now_playing.from_phone(props, now_ms=2000)
  assert (found['source'], found['status'], found['title'], found['artist']) == ('phone', 'playing', 'Song', 'Band')
  assert found['durationMs'] == 200000 and found['position'] == {'ms': 5000, 'at': 2000, 'speed': 1.0}
  assert now_playing.from_phone({**props, 'Status': 'paused'}, now_ms=2000)['position']['speed'] == 0.0
  for bad in (None, {}, {'Status': 'stopped', 'Track': props['Track']}, {'Status': 'playing', 'Track': {}},
              {'Status': 'playing', 'Track': {'Title': '\x00\x01'}}):
    assert now_playing.from_phone(bad) is None


def test_untrusted_text_is_cleaned_and_bounded():
  found = now_playing.from_phone({'Status': 'playing', 'Track': {'Title': 'A\x00B' + 'x' * 500, 'Artist': 7}})
  assert found['title'].startswith('AB') and len(found['title']) == now_playing.MAX_TEXT and found['artist'] == ''


def test_elapsed_follows_the_anchor_and_clamps_to_the_duration():
  found = now_playing.from_spotify(PLAYER)
  assert now_playing.elapsed_ms(found, 4000) == 13000
  assert now_playing.elapsed_ms(found, 10 ** 12) == 243000
  assert now_playing.elapsed_ms({**found, 'position': None}, 4000) == 0


def test_published_snapshot_is_ignored_when_stale_or_broken(tmp_path):
  path = tmp_path / 'status.json'
  assert now_playing.read(path) is None
  path.write_text(json.dumps({'nowPlaying': now_playing.from_spotify(PLAYER)}))
  mtime = path.stat().st_mtime
  assert now_playing.read(path, now=mtime + 1)['title'] == 'Midnight City'
  assert now_playing.read(path, now=mtime + 60) is None
  path.write_text('{broken')
  assert now_playing.read(path, now=mtime + 1) is None
  path.write_text(json.dumps({'nowPlaying': {'title': 'x', 'status': 'idle'}}))
  assert now_playing.read(path, now=mtime + 1) is None


def test_feed_only_reads_while_enabled():
  reads = []
  feed = ProjectionNowPlayingFeed(read=lambda: reads.append(1) or {'title': 'x'})
  feed.poll()
  assert reads == [] and feed.snapshot() is None
  feed._enabled = True
  feed.poll()
  assert feed.snapshot() == {'title': 'x'}
  feed.set_enabled(False)
  assert feed.snapshot() is None
  feed.close()
