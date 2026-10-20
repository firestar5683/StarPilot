"""One small now-playing snapshot for the car screen, from Spotify or from a phone's Bluetooth player."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

MAX_TEXT = 120
STALE_SECONDS = 10.0


def _text(value: Any) -> str:
  return ''.join(ch for ch in value if ch.isprintable())[:MAX_TEXT].strip() if isinstance(value, str) else ''


def _whole(value: Any, limit: int = 86400000) -> int | None:
  return int(value) if type(value) in (int, float) and 0 <= value < limit else None


def snapshot(source: str, status: str, title: str, artist: str, album: str, duration_ms: int | None,
             position: dict | None) -> dict | None:
  title = _text(title)
  if not title or status not in ('playing', 'paused'):
    return None
  return {'source': source, 'status': status, 'title': title, 'artist': _text(artist), 'album': _text(album),
          'durationMs': duration_ms, 'position': position}


def from_spotify(player: dict | None) -> dict | None:
  if not isinstance(player, dict) or not player.get('loggedIn'):
    return None
  track = player.get('track')
  if not isinstance(track, dict) or player.get('status') not in ('playing', 'paused') or not player.get('active'):
    return None
  return snapshot('spotify', player['status'], track.get('title'), track.get('artists'), track.get('album'),
                  _whole(track.get('durationMs')), player.get('position'))


def from_phone(props: dict | None, now_ms: int | None = None) -> dict | None:
  """BlueZ MediaPlayer1 properties: Track {Title, Artist, Album, Duration ms}, Status, Position ms."""
  if not isinstance(props, dict) or not isinstance(props.get('Track'), dict):
    return None
  status = {'playing': 'playing', 'paused': 'paused'}.get(str(props.get('Status', '')).lower())
  track = props['Track']
  position = _whole(props.get('Position'))
  anchor = None
  if position is not None:
    # Anchors are epoch ms, like the ones Spotify sends.
    anchor = {'ms': position, 'at': int(time.time() * 1000) if now_ms is None else now_ms,  # noqa: TID251
              'speed': 1.0 if status == 'playing' else 0.0}
  duration = _whole(track.get('Duration'))
  return snapshot('phone', status or '', track.get('Title'), track.get('Artist'), track.get('Album'),
                  duration if duration else None, anchor)


def elapsed_ms(now_playing: dict, now_ms: float | None = None) -> int:
  position, duration = now_playing.get('position'), now_playing.get('durationMs')
  if not isinstance(position, dict):
    return 0
  now_ms = time.time() * 1000 if now_ms is None else now_ms  # noqa: TID251 epoch-ms anchors
  value = position['ms'] + max(0.0, now_ms - position['at']) * position['speed']
  return int(max(0, min(duration if duration else value, value)))


def read(path: Path, now: float | None = None) -> dict | None:
  """The supervisor's published snapshot; None when missing, malformed or the supervisor stopped updating."""
  try:
    if (time.time() if now is None else now) - path.stat().st_mtime > STALE_SECONDS:  # noqa: TID251 compared with mtime
      return None
    found = json.loads(path.read_text()).get('nowPlaying')
  except (OSError, ValueError, AttributeError):
    return None
  return found if isinstance(found, dict) and found.get('title') and found.get('status') in ('playing', 'paused') else None
