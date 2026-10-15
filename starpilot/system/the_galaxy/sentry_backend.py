import base64
import json
import math
import os
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

from openpilot.starpilot.system.the_galaxy import utilities

SENTRY_NOTIFICATION_RATE_LIMIT_SECONDS = 180.0

# Set by register_sentry_routes() to the calling the_galaxy module's globals() dict. Not a
# plain import: the_galaxy.py is sometimes exec'd under a throwaway module name that's never
# registered in sys.modules (e.g. by tests via importlib.util.spec_from_file_location), so a
# normal import here could either fail to resolve or load a second, independent copy of it.
# globals() from a function defined in the_galaxy.py always returns that module's own live
# namespace dict regardless of how (or whether) it's registered in sys.modules.
_galaxy = None


def _sentry_event_roots() -> tuple[Path, ...]:
  roots = [Path("/data/media/0/sentryd")]
  if _galaxy["PC"]:
    roots.insert(0, Path(_galaxy["Paths"].comma_home()) / "starpilot" / "data" / "sentryd")
  return tuple(root.resolve() for root in roots)


_SENTRY_IMAGE_CACHE_SECONDS = 7 * 24 * 60 * 60
_SENTRY_EVENT_INDEX_NAME = "events.json"
_SENTRY_EVENT_INDEX_LOCK = threading.Lock()


def _sentry_event_index_path() -> Path:
  return _sentry_event_roots()[0] / _SENTRY_EVENT_INDEX_NAME


def _load_sentry_event_catalog_unlocked() -> list[dict]:
  index_path = _sentry_event_index_path()
  try:
    raw_events = json.loads(index_path.read_text())
  except (OSError, TypeError, ValueError, json.JSONDecodeError):
    return []

  if not isinstance(raw_events, list):
    return []

  events = []
  for raw_event in raw_events:
    event = _normalize_sentry_event(raw_event)
    if event is not None:
      events.append(event)
  return events


def _save_sentry_event_catalog_unlocked(events: list[dict]) -> None:
  index_path = _sentry_event_index_path()
  index_path.parent.mkdir(parents=True, exist_ok=True)
  temporary_path = index_path.with_suffix(".tmp")
  temporary_path.write_text(json.dumps(events, separators=(",", ":")))
  temporary_path.chmod(0o600)
  temporary_path.replace(index_path)


def _stored_sentry_event() -> dict | None:
  raw_event = _galaxy["params"].get("SentryModeLastEvent", encoding="utf-8") or "{}"
  try:
    payload = raw_event if isinstance(raw_event, dict) else json.loads(raw_event)
  except (TypeError, ValueError, json.JSONDecodeError):
    return None
  return _normalize_sentry_event(payload)


def _discover_legacy_sentry_events(known_event_ids: set[str]) -> list[dict]:
  discovered = []
  for root in _sentry_event_roots():
    try:
      directories = sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
      )
    except OSError:
      continue

    for directory in directories:
      event_id = directory.name
      if event_id == _SENTRY_LIVE_EVENT_ID or event_id in known_event_ids or len(event_id) > 96:
        continue

      image_paths = [
        str(path) for path in (directory / "wide.jpg", directory / "driver.jpg")
        if path.is_file()
      ]
      if not image_paths:
        continue

      try:
        detected_at = datetime.fromtimestamp(directory.stat().st_mtime, timezone.utc).isoformat()
      except OSError:
        detected_at = ""
      is_test = event_id.startswith("test-")
      discovered.append({
        "eventId": event_id,
        "kind": "alarm" if is_test else "warning",
        "detectedAt": detected_at,
        "message": "Test sentry event." if is_test else "Movement detected while parked.",
        "imagePaths": image_paths,
      })
      known_event_ids.add(event_id)
  return discovered


def _sentry_event_catalog() -> list[dict]:
  with _SENTRY_EVENT_INDEX_LOCK:
    events = _load_sentry_event_catalog_unlocked()
    known_event_ids = {event["eventId"] for event in events}
    legacy_events = _discover_legacy_sentry_events(known_event_ids)
    if legacy_events:
      events.extend(legacy_events)
    latest_event = _stored_sentry_event()
    if latest_event is not None and latest_event["eventId"] not in known_event_ids:
      events.insert(0, latest_event)
      _save_sentry_event_catalog_unlocked(events)
    elif legacy_events:
      _save_sentry_event_catalog_unlocked(events)
    return events


def _record_sentry_event(event: dict) -> None:
  with _SENTRY_EVENT_INDEX_LOCK:
    events = _load_sentry_event_catalog_unlocked()
    known_event_ids = {existing["eventId"] for existing in events}
    events.extend(_discover_legacy_sentry_events(known_event_ids))
    events = [existing for existing in events if existing.get("eventId") != event["eventId"]]
    events.insert(0, event)
    _save_sentry_event_catalog_unlocked(events)


def _safe_sentry_image_paths(raw_paths) -> list[str]:
  if not isinstance(raw_paths, list):
    return []

  roots = _sentry_event_roots()
  safe_paths = []
  for raw_path in raw_paths:
    try:
      path = Path(str(raw_path)).resolve()
      if path.is_file() and any(path.is_relative_to(root) for root in roots):
        safe_paths.append(str(path))
    except (OSError, TypeError, ValueError):
      continue
  return safe_paths


def _normalize_sentry_event(payload) -> dict | None:
  if not isinstance(payload, dict):
    return None

  event_id = str(payload.get("eventId") or "").strip()
  kind = str(payload.get("kind") or "").strip().lower()
  if not event_id or kind not in {"warning", "alarm", "power_off", "selfie"}:
    return None

  event = {
    "eventId": event_id[:96],
    "kind": kind,
    "detectedAt": str(payload.get("detectedAt") or ""),
    "message": str(payload.get("message") or "Movement detected while parked.")[:500],
    "imagePaths": _safe_sentry_image_paths(payload.get("imagePaths")),
  }
  reason = str(payload.get("reason") or "").strip()
  if reason:
    event["reason"] = reason[:96]
  return event


def _sentry_image_path(event_id: str, filename: str) -> Path | None:
  if not event_id or Path(event_id).name != event_id:
    return None
  if filename not in {"wide.jpg", "driver.jpg"} or Path(filename).name != filename:
    return None

  for root in _sentry_event_roots():
    path = (root / event_id / filename).resolve()
    if root in path.parents and path.is_file():
      return path
  return None


def _public_sentry_event(event: dict) -> dict:
  public_event = dict(event)
  public_event.pop("imagePaths", None)
  public_event["imageUrls"] = []
  event_id = str(public_event.get("eventId") or "")
  for raw_path in event.get("imagePaths", []):
    path = Path(str(raw_path)).resolve()
    if path.parent.name != event_id:
      continue
    if _sentry_image_path(event_id, path.name) == path:
      public_event["imageUrls"].append(
        f"/api/sentry/images/{quote(event_id, safe='')}/{quote(path.name, safe='')}"
      )
  return public_event


def _parse_sentry_instant(value) -> datetime | None:
  text = str(value or "").strip()
  if not text:
    return None
  try:
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
  except ValueError:
    return None
  return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _filter_sentry_events_by_time(events: list[dict], since: datetime | None, until: datetime | None) -> list[dict]:
  """Keep events detected in [since, until). Events with an unparseable timestamp never match a date filter."""
  if since is None and until is None:
    return events
  matched = []
  for event in events:
    detected_at = _parse_sentry_instant(event.get("detectedAt"))
    if detected_at is None:
      continue
    if since is not None and detected_at < since:
      continue
    if until is not None and detected_at >= until:
      continue
    matched.append(event)
  return matched


def _sentry_time_filter_from_request():
  """Returns (since, until, error_message); error_message is set when a supplied value is not a valid ISO timestamp."""
  bounds = []
  for key in ("since", "until"):
    raw_value = _galaxy["request"].args.get(key)
    if raw_value in (None, ""):
      bounds.append(None)
      continue
    instant = _parse_sentry_instant(raw_value)
    if instant is None:
      return None, None, f"Invalid '{key}' timestamp."
    bounds.append(instant)
  return bounds[0], bounds[1], None


def _delete_sentry_event_storage(event_id: str) -> bool:
  """Removes the event's directory from every root; raises OSError after trying all roots if any removal failed."""
  deleted = False
  failure = None
  for root in _sentry_event_roots():
    directory = (root / event_id).resolve()
    if root not in directory.parents or not directory.is_dir():
      continue
    try:
      shutil.rmtree(directory)
    except OSError as error:
      _galaxy["cloudlog"].exception(f"sentry event storage delete failed: {directory}")
      failure = error
      continue
    deleted = True
  if failure is not None:
    raise failure
  return deleted


def _forget_sentry_events(removed_ids: set[str]) -> bool:
  """Drops the events from the catalog and, if the last-event param named one, repoints it at the newest survivor.

  Returns whether the catalog changed.
  """
  current_event = _stored_sentry_event()
  with _SENTRY_EVENT_INDEX_LOCK:
    events = _load_sentry_event_catalog_unlocked()
    retained_events = [event for event in events if event.get("eventId") not in removed_ids]
    catalog_changed = len(retained_events) != len(events)
    if catalog_changed:
      _save_sentry_event_catalog_unlocked(retained_events)

  if current_event is not None and current_event.get("eventId") in removed_ids:
    if retained_events:
      _galaxy["params"].put("SentryModeLastEvent", json.dumps(retained_events[0], separators=(",", ":")))
    else:
      _galaxy["params"].remove("SentryModeLastEvent")
  return catalog_changed


_SENTRY_TIMELAPSE_LOCK = threading.Lock()
_SENTRY_TIMELAPSE_FRAME_WIDTH = 640
_SENTRY_TIMELAPSE_MAX_FRAMES = 600
_SENTRY_TIMELAPSE_OUTPUT_FPS = 30
_SENTRY_TIMELAPSE_MAX_SECONDS = 60.0
_SENTRY_TIMELAPSE_MIN_FRAME_SECONDS = 0.04
# Gap-paced frame time: base + scale * log10(1 + gap in minutes), clamped. About 0.22s for a 1 minute gap,
# 0.6s for an hour, 0.9s for a day and 1.15s for a week, so bursts stay readable and lulls still pause.
_SENTRY_TIMELAPSE_GAP_BASE_SECONDS = 0.15
_SENTRY_TIMELAPSE_GAP_SCALE_SECONDS = 0.25
_SENTRY_TIMELAPSE_GAP_MAX_SECONDS = 1.5
_SENTRY_TIMELAPSE_LAST_FRAME_SECONDS = 1.0
_SENTRY_TIMELAPSE_FILES = {"wide": ("wide.jpg",), "driver": ("driver.jpg",), "both": ("wide.jpg", "driver.jpg")}
# kind -> (badge label, badge color); alarms also get a border so they stand out at a glance.
_SENTRY_TIMELAPSE_BADGES = {
  "warning": ("WARNING", (245, 166, 35)),
  "alarm": ("ALARM", (220, 38, 38)),
  "selfie": ("SELFIE", (59, 130, 246)),
}
_SENTRY_TIMELAPSE_DEFAULT_BADGE = ("EVENT", (140, 140, 140))
_SENTRY_TIMELAPSE_ALARM_BORDER = 8
_SENTRY_TIMELAPSE_BAR_HEIGHT = 26
_SENTRY_TIMELAPSE_FONTS = (
  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
  "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
)


def _sentry_timelapse_font(size: int):
  from PIL import ImageFont

  for font_path in _SENTRY_TIMELAPSE_FONTS:
    try:
      return ImageFont.truetype(font_path, size)
    except OSError:
      continue
  try:
    return ImageFont.load_default(size=size)
  except TypeError:
    return ImageFont.load_default()


def _sentry_timelapse_sources(events: list[dict], filenames: tuple[str, ...], max_frames: int) -> list[tuple[datetime, str, list[Path | None]]]:
  """Oldest-first (detected_at, kind, image paths) for events that have at least one requested image, evenly
  sampled to max_frames. A path is None where that event is missing one of the requested cameras (e.g. a
  driver-only Comma Selfie sampled in "both" mode) — the renderer leaves that camera's tile blank rather
  than dropping the event.
  """
  frames = []
  for event in events:
    event_id = str(event.get("eventId") or "")
    detected_at = _parse_sentry_instant(event.get("detectedAt"))
    if detected_at is None:
      continue
    paths = [_sentry_image_path(event_id, filename) for filename in filenames]
    if any(paths):
      frames.append((detected_at, str(event.get("kind") or ""), paths))
  frames.sort(key=lambda frame: frame[0])
  if len(frames) > max_frames:
    frames = [frames[i * (len(frames) - 1) // (max_frames - 1)] for i in range(max_frames)] if max_frames > 1 else frames[-1:]
  return frames


def _sentry_timelapse_gaps(frames: list[tuple[datetime, str, list[Path | None]]]) -> list[float | None]:
  """Seconds from each frame to the next one; None for the last frame."""
  return [(frames[i + 1][0] - frames[i][0]).total_seconds() for i in range(len(frames) - 1)] + [None]


def _sentry_timelapse_durations(gaps: list[float | None], timing: str, fps: int) -> list[float]:
  """How long each frame is shown. 'gap' compresses the real gaps logarithmically, 'even' uses 1/fps.

  Either way the total is scaled down to _SENTRY_TIMELAPSE_MAX_SECONDS if it would run longer.
  """
  if timing == "even":
    durations = [1.0 / fps] * len(gaps)
  else:
    durations = []
    for gap in gaps:
      if gap is None:
        durations.append(_SENTRY_TIMELAPSE_LAST_FRAME_SECONDS)
        continue
      seconds = _SENTRY_TIMELAPSE_GAP_BASE_SECONDS + _SENTRY_TIMELAPSE_GAP_SCALE_SECONDS * math.log10(1 + max(gap, 0.0) / 60.0)
      durations.append(min(seconds, _SENTRY_TIMELAPSE_GAP_MAX_SECONDS))

  total = sum(durations)
  if total > _SENTRY_TIMELAPSE_MAX_SECONDS:
    scale = _SENTRY_TIMELAPSE_MAX_SECONDS / total
    durations = [max(duration * scale, _SENTRY_TIMELAPSE_MIN_FRAME_SECONDS) for duration in durations]
  return durations


def _format_sentry_gap(seconds: float) -> str:
  seconds = int(max(seconds, 0))
  if seconds < 60:
    return f"{seconds}s"
  minutes = seconds // 60
  if minutes < 60:
    return f"{minutes}m"
  hours, minutes = divmod(minutes, 60)
  if hours < 24:
    return f"{hours}h {minutes}m"
  days, hours = divmod(hours, 24)
  return f"{days}d {hours}h"


def _sentry_timelapse_timeline(frames: list[tuple[datetime, str, list[Path | None]]]) -> list[float]:
  """Each frame's position (0..1) along the real time span of the range."""
  start = frames[0][0]
  span = (frames[-1][0] - start).total_seconds()
  if span <= 0:
    return [0.5] * len(frames)
  return [(frame[0] - start).total_seconds() / span for frame in frames]


def _render_sentry_timelapse_frame(
  paths: list[Path | None], detected_at: datetime, kind: str, gap_to_next: float | None,
  index: int, positions: list[float], kinds: list[str], output_path: Path,
) -> None:
  from PIL import Image, ImageDraw

  # Keyed by slot (not appended) so a camera this event is missing (e.g. a driver-only Comma
  # Selfie in "both" mode) leaves its tile position blank instead of shifting the others over.
  tiles = {}
  for slot, path in enumerate(paths):
    if path is None:
      continue
    with Image.open(path) as source:
      image = source.convert("RGB")
    height = max(2, round(image.height * _SENTRY_TIMELAPSE_FRAME_WIDTH / image.width) // 2 * 2)
    tiles[slot] = image.resize((_SENTRY_TIMELAPSE_FRAME_WIDTH, height))

  frame_height = max((tile.height for tile in tiles.values()), default=_SENTRY_TIMELAPSE_FRAME_WIDTH * 3 // 4)
  frame = Image.new("RGB", (_SENTRY_TIMELAPSE_FRAME_WIDTH * len(paths), frame_height))
  for slot, tile in tiles.items():
    frame.paste(tile, (slot * _SENTRY_TIMELAPSE_FRAME_WIDTH, 0))

  badge_label, badge_color = _SENTRY_TIMELAPSE_BADGES.get(kind, _SENTRY_TIMELAPSE_DEFAULT_BADGE)
  label = detected_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
  draw = ImageDraw.Draw(frame)
  font = _sentry_timelapse_font(22)
  small_font = _sentry_timelapse_font(17)

  # The overlays are always inset by the border width, so they do not jump when an alarm frame draws its border.
  inset = _SENTRY_TIMELAPSE_ALARM_BORDER
  if kind == "alarm":
    draw.rectangle((0, 0, frame.width - 1, frame.height - 1), outline=badge_color, width=_SENTRY_TIMELAPSE_ALARM_BORDER)

  # Drawn as shapes plus text, not a Unicode glyph, so it does not depend on the font having the symbol.
  x, y = 10 + inset, 8 + inset
  dot = 14
  badge_width = draw.textlength(badge_label, font=font)
  left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
  line_height = bottom - top
  total = dot + 8 + badge_width + 16 + (right - left)
  gap_text = f"next event in {_format_sentry_gap(gap_to_next)}" if gap_to_next is not None else "last event"
  box_bottom = y + line_height + 8 + 22
  draw.rectangle((x - 6, y - 4, x + total + 6, box_bottom), fill=(0, 0, 0))
  draw.ellipse((x, y + (line_height - dot) // 2 + 2, x + dot, y + (line_height - dot) // 2 + 2 + dot), fill=badge_color)
  draw.text((x + dot + 8, y), badge_label, fill=badge_color, font=font)
  draw.text((x + dot + 8 + badge_width + 16, y), label, fill=(255, 255, 255), font=font)
  draw.text((x, y + line_height + 8), gap_text, fill=(170, 170, 170), font=small_font)

  # Timeline bar along the bottom: every event in real-time position, the current one highlighted.
  bar_top = frame.height - inset - _SENTRY_TIMELAPSE_BAR_HEIGHT
  bar_left, bar_right = inset + 10, frame.width - inset - 10
  draw.rectangle((inset, bar_top, frame.width - inset, frame.height - inset), fill=(0, 0, 0))
  middle = bar_top + _SENTRY_TIMELAPSE_BAR_HEIGHT // 2
  draw.line((bar_left, middle, bar_right, middle), fill=(120, 120, 120), width=3)
  for other_index, position in enumerate(positions):
    tick_x = bar_left + position * (bar_right - bar_left)
    tick_color = _SENTRY_TIMELAPSE_BADGES.get(kinds[other_index], _SENTRY_TIMELAPSE_DEFAULT_BADGE)[1]
    if other_index > index:
      tick_color = tuple(channel * 2 // 5 for channel in tick_color)
    draw.line((tick_x, bar_top + 4, tick_x, frame.height - inset - 4), fill=tick_color, width=3)
  current_x = bar_left + positions[index] * (bar_right - bar_left)
  draw.rectangle((current_x - 3, bar_top + 2, current_x + 3, frame.height - inset - 2), fill=(255, 255, 255))
  frame.save(output_path, "JPEG", quality=88)


def _encode_sentry_timelapse(frames: list[tuple[datetime, str, list[Path | None]]], durations: list[float]) -> bytes:
  """Renders the frames and encodes them to MP4 with ffmpeg, each shown for its duration; raises RuntimeError on failure.

  Each rendered frame is repeated (as hard links) to fill its duration at the output frame rate, so ffmpeg only
  sees a plain image sequence. The device's ffmpeg is a minimal build with no fps filter, and the concat
  demuxer's per-file durations were unreliable there.
  """
  gaps = _sentry_timelapse_gaps(frames)
  positions = _sentry_timelapse_timeline(frames)
  kinds = [frame[1] for frame in frames]
  with tempfile.TemporaryDirectory(prefix="sentry-timelapse-") as work_dir:
    work = Path(work_dir)
    sequence = work / "sequence"
    sequence.mkdir()
    elapsed = 0.0
    written = 0
    for index, (detected_at, kind, paths) in enumerate(frames):
      rendered = work / f"frame{index:05d}.jpg"
      try:
        _render_sentry_timelapse_frame(paths, detected_at, kind, gaps[index], index, positions, kinds, rendered)
      except FileNotFoundError:
        # The event was deleted while the timelapse was encoding; skip its frame.
        _galaxy["cloudlog"].warning(f"sentry timelapse skipped a deleted frame: {paths}")
        continue
      # Cumulative rounding keeps the total exact; every frame gets at least one output frame.
      elapsed += durations[index]
      end = max(round(elapsed * _SENTRY_TIMELAPSE_OUTPUT_FPS), written + 1)
      while written < end:
        target = sequence / f"{written:06d}.jpg"
        try:
          os.link(rendered, target)
        except OSError:
          shutil.copyfile(rendered, target)
        written += 1

    output = work / "timelapse.mp4"
    command = [
      utilities.FFMPEG_BIN, "-hide_banner", "-loglevel", "error", "-y",
      "-framerate", str(_SENTRY_TIMELAPSE_OUTPUT_FPS), "-i", str(sequence / "%06d.jpg"),
      "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "26", "-movflags", "+faststart",
      str(output),
    ]
    try:
      result = subprocess.run(command, capture_output=True, timeout=180)
    except subprocess.TimeoutExpired as error:
      raise RuntimeError("Timelapse encoding timed out.") from error
    if result.returncode != 0 or not output.is_file():
      detail = result.stderr.decode("utf-8", "replace").strip()[-400:]
      _galaxy["cloudlog"].error(f"sentry timelapse ffmpeg exit {result.returncode}: {detail}")
      raise RuntimeError(f"Timelapse encoding failed: {detail.splitlines()[-1] if detail else 'ffmpeg exited with ' + str(result.returncode)}")
    return output.read_bytes()


def _capture_sentry_test_images(event_id: str) -> list[str]:
  from openpilot.system.camerad.snapshot import jpeg_write, snapshot

  _galaxy["params"].put_bool("SentryModeCapture", True)
  try:
    rear, front = snapshot(allow_existing=True)
  except Exception:
    _galaxy["cloudlog"].exception("Galaxy: sentry test snapshot failed")
    return []
  finally:
    _galaxy["params"].put_bool("SentryModeCapture", False)

  if rear is None and front is None:
    return []

  directory = _sentry_event_roots()[0] / event_id
  directory.mkdir(parents=True, exist_ok=True)
  paths = []
  if rear is not None:
    path = directory / "wide.jpg"
    jpeg_write(str(path), rear)
    paths.append(str(path))
  if front is not None:
    path = directory / "driver.jpg"
    jpeg_write(str(path), front)
    paths.append(str(path))
  return paths


_SENTRY_LIVE_CAPTURE_LOCK = threading.Lock()
_SENTRY_LIVE_EVENT_ID = "live"


def _capture_sentry_live_images() -> list[str]:
  from openpilot.system.camerad.snapshot import jpeg_write, snapshot

  _galaxy["params"].put_bool("SentryModeCapture", True)
  try:
    rear, front = snapshot(allow_existing=True, include_front=True)
  except Exception:
    _galaxy["cloudlog"].exception("Galaxy: live Sentry snapshot failed")
    return []
  finally:
    _galaxy["params"].put_bool("SentryModeCapture", False)

  if rear is None and front is None:
    return []

  directory = _sentry_event_roots()[0] / _SENTRY_LIVE_EVENT_ID
  directory.mkdir(parents=True, exist_ok=True)
  paths = []
  if rear is not None:
    path = directory / "wide.jpg"
    jpeg_write(str(path), rear)
    paths.append(str(path))
  if front is not None:
    path = directory / "driver.jpg"
    jpeg_write(str(path), front)
    paths.append(str(path))
  return paths




_SENTRY_PUSH_LOCK = threading.Lock()
_SENTRY_NOTIFICATION_RATE_LIMIT_LOCK = threading.Lock()
_SENTRY_NOTIFICATION_LAST_AT: float | None = None
_SENTRY_PUSH_PRIVATE_KEY_NAME = "sentry_vapid_private.pem"
_SENTRY_PUSH_SUBSCRIPTIONS_NAME = "sentry_push_subscriptions.json"
_SENTRY_PUSH_SUBJECT = os.getenv("STARPILOT_VAPID_SUBJECT", "mailto:galaxy@firestar.link")


def _sentry_push_paths() -> tuple[Path, Path]:
  galaxy_dir = _galaxy["_get_galaxy_dir"]()
  return galaxy_dir / _SENTRY_PUSH_PRIVATE_KEY_NAME, galaxy_dir / _SENTRY_PUSH_SUBSCRIPTIONS_NAME


def _load_sentry_push_subscriptions() -> list[dict]:
  _, subscriptions_path = _sentry_push_paths()
  try:
    payload = json.loads(subscriptions_path.read_text())
  except (OSError, TypeError, ValueError, json.JSONDecodeError):
    return []

  if not isinstance(payload, list):
    return []
  return [subscription for subscription in payload if isinstance(subscription, dict)]


def _save_sentry_push_subscriptions(subscriptions: list[dict]) -> None:
  _, subscriptions_path = _sentry_push_paths()
  subscriptions_path.parent.mkdir(parents=True, exist_ok=True)
  temporary_path = subscriptions_path.with_suffix(".tmp")
  temporary_path.write_text(json.dumps(subscriptions, separators=(",", ":")))
  temporary_path.chmod(0o600)
  temporary_path.replace(subscriptions_path)


def _normalize_sentry_push_subscription(payload) -> dict | None:
  if not isinstance(payload, dict):
    return None

  subscription = payload.get("subscription", payload)
  if not isinstance(subscription, dict):
    return None

  endpoint = str(subscription.get("endpoint") or "").strip()
  keys = subscription.get("keys")
  if not endpoint.startswith("https://") or len(endpoint) > 4096 or not isinstance(keys, dict):
    return None

  p256dh = str(keys.get("p256dh") or "").strip()
  auth = str(keys.get("auth") or "").strip()
  if not p256dh or not auth or len(p256dh) > 512 or len(auth) > 512:
    return None

  return {
    "endpoint": endpoint,
    "expirationTime": subscription.get("expirationTime"),
    "keys": {"p256dh": p256dh, "auth": auth},
  }


def _get_sentry_vapid():
  try:
    from py_vapid import Vapid
  except ModuleNotFoundError as error:
    raise RuntimeError("pywebpush is not installed") from error

  with _SENTRY_PUSH_LOCK:
    private_key_path, _ = _sentry_push_paths()
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    if private_key_path.is_file():
      try:
        if private_key_path.stat().st_size > 0:
          return Vapid.from_file(str(private_key_path))
      except Exception as error:
        _galaxy["cloudlog"].warning("Galaxy: Existing Sentry VAPID private key was invalid, regenerating: %s", error)

    vapid = Vapid()
    vapid.generate_keys()
    temporary_path = private_key_path.with_suffix(".tmp")
    vapid.save_key(str(temporary_path))
    temporary_path.chmod(0o600)
    temporary_path.replace(private_key_path)
    return vapid


def _sentry_vapid_public_key(vapid) -> str:
  from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

  raw_key = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
  return base64.urlsafe_b64encode(raw_key).rstrip(b"=").decode("ascii")


def _sentry_push_subscription_count() -> int:
  with _SENTRY_PUSH_LOCK:
    return len(_load_sentry_push_subscriptions())


def _sentry_public_base_url() -> str:
  configured_url = os.getenv("STARPILOT_GALAXY_PUBLIC_URL", "").strip().rstrip("/")
  if configured_url:
    return configured_url

  slug = _galaxy["_read_galaxy_text"](_galaxy["_get_galaxy_dir"]() / "glxyslug")
  return f"https://galaxy.firestar.link/{slug}" if slug else ""


def _sentry_external_image_urls(event: dict) -> list[str]:
  base_url = _sentry_public_base_url()
  if not base_url:
    return []

  public_event = _public_sentry_event(event)
  return [f"{base_url}{image_url}" for image_url in public_event["imageUrls"]]


def _sentry_first_image(event: dict) -> tuple[str, bytes] | None:
  for raw_path in event.get("imagePaths", []):
    path = Path(str(raw_path))
    try:
      return path.name, path.read_bytes()
    except OSError:
      continue
  return None


def _sentry_notification_channels() -> dict[str, bool]:
  return {
    "webPush": _sentry_push_subscription_count() > 0,
    "webhook": bool((_galaxy["params"].get("SentryModeWebhook", encoding="utf-8") or "").strip()),
    "ntfy": bool((_galaxy["params"].get("SentryModeNtfyUrl", encoding="utf-8") or "").strip()),
  }


def _sentry_notification_rate_limit_path() -> Path:
  return _galaxy["_get_galaxy_dir"]() / "sentry_notification_rate_limit.json"


def _load_sentry_notification_last_at() -> float | None:
  try:
    payload = json.loads(_sentry_notification_rate_limit_path().read_text())
    value = float(payload.get("lastNotificationAt")) if isinstance(payload, dict) else None
  except (OSError, TypeError, ValueError, json.JSONDecodeError):
    return None
  return value if value is not None and math.isfinite(value) else None


def _claim_sentry_notification_slot(event: dict) -> bool:
  """Reserve the shared notification slot for a real Sentry event."""
  global _SENTRY_NOTIFICATION_LAST_AT

  now = time.time()
  with _SENTRY_NOTIFICATION_RATE_LIMIT_LOCK:
    persisted_last_at = _load_sentry_notification_last_at()
    last_at = max(
      (value for value in (_SENTRY_NOTIFICATION_LAST_AT, persisted_last_at) if value is not None),
      default=None,
    )
    if last_at is not None:
      elapsed = max(0.0, now - last_at)
      if elapsed < SENTRY_NOTIFICATION_RATE_LIMIT_SECONDS:
        remaining = SENTRY_NOTIFICATION_RATE_LIMIT_SECONDS - elapsed
        _galaxy["cloudlog"].info(
          "Galaxy: Sentry notification suppressed by rate limit (%.0f seconds remaining; event=%s)",
          remaining,
          event.get("eventId", ""),
        )
        return False

    _SENTRY_NOTIFICATION_LAST_AT = now
    rate_limit_path = _sentry_notification_rate_limit_path()
    temporary_path = rate_limit_path.with_suffix(".tmp")
    try:
      rate_limit_path.parent.mkdir(parents=True, exist_ok=True)
      temporary_path.write_text(json.dumps({
        "lastNotificationAt": now,
        "eventId": str(event.get("eventId") or ""),
      }, separators=(",", ":")))
      temporary_path.chmod(0o600)
      temporary_path.replace(rate_limit_path)
    except OSError:
      _galaxy["cloudlog"].warning("Galaxy: unable to persist Sentry notification rate-limit state")
      try:
        temporary_path.unlink(missing_ok=True)
      except OSError:
        pass
    return True


def _sentry_test_notification_event() -> dict:
  return {
    "eventId": f"notification-test-{int(time.time())}-{secrets.token_hex(4)}",
    "kind": "warning",
    "detectedAt": datetime.now(timezone.utc).isoformat(),
    "message": "This is a test StarPilot Sentry notification.",
    "imagePaths": [],
  }


def _dispatch_sentry_push(event: dict) -> None:
  try:
    from openpilot.starpilot.system.the_galaxy.web_push import webpush

    vapid = _get_sentry_vapid()
  except Exception:
    _galaxy["cloudlog"].exception("Galaxy: Sentry Web Push is unavailable")
    return

  event_id = str(event.get("eventId") or "")
  payload = {
    "title": "StarPilot Sentry Mode",
    "body": str(event.get("message") or "Movement detected while parked."),
    "eventId": event_id,
    "url": f"/sentry?event={quote(event_id, safe='')}",
  }
  image_urls = _sentry_external_image_urls(event)
  if image_urls:
    payload["image"] = image_urls[0]

  with _SENTRY_PUSH_LOCK:
    subscriptions = _load_sentry_push_subscriptions()

  expired_endpoints = set()
  for subscription in subscriptions:
    endpoint = subscription.get("endpoint")
    try:
      webpush(
        subscription_info=subscription,
        data=json.dumps(payload, separators=(",", ":")),
        vapid_private_key=vapid,
        vapid_claims={"sub": _SENTRY_PUSH_SUBJECT},
        ttl=300,
        timeout=10,
      )
    except Exception as error:
      response = getattr(error, "response", None)
      if getattr(response, "status_code", None) in {404, 410}:
        expired_endpoints.add(endpoint)
      _galaxy["cloudlog"].warning("Galaxy: Sentry Web Push delivery failed: %s", error)

  if expired_endpoints:
    with _SENTRY_PUSH_LOCK:
      current = _load_sentry_push_subscriptions()
      _save_sentry_push_subscriptions([
        subscription for subscription in current
        if subscription.get("endpoint") not in expired_endpoints
      ])


def _dispatch_sentry_event(event: dict, *, bypass_rate_limit: bool = False) -> None:
  if not any(_sentry_notification_channels().values()):
    return
  if not bypass_rate_limit and not _claim_sentry_notification_slot(event):
    return

  _dispatch_sentry_push(event)
  message = f"🚨 StarPilot Sentry Mode: {event['message']}"
  webhook = (_galaxy["params"].get("SentryModeWebhook", encoding="utf-8") or "").strip()
  if webhook:
    files = []
    handles = []
    try:
      for image_path in event.get("imagePaths", []):
        handle = open(image_path, "rb")
        handles.append(handle)
        files.append(("file", (Path(image_path).name, handle, "image/jpeg")))

      body = {"content": message, "event": json.dumps(event, separators=(",", ":"))}
      response = requests.post(webhook, data=body, files=files or None, timeout=10)
      response.raise_for_status()
    except Exception:
      _galaxy["cloudlog"].exception("Galaxy: sentry webhook notification failed")
    finally:
      for handle in handles:
        try:
          handle.close()
        except OSError:
          pass

  ntfy_url = (_galaxy["params"].get("SentryModeNtfyUrl", encoding="utf-8") or "").strip()
  if ntfy_url:
    try:
      headers = {"Title": "StarPilot Sentry Mode", "Priority": "urgent", "Tags": "warning,car"}
      image = _sentry_first_image(event)
      if image is None:
        response = requests.post(ntfy_url, data=message.encode("utf-8"), headers=headers, timeout=10)
      else:
        filename, image_data = image
        headers.update({
          "Content-Type": "image/jpeg",
          "Filename": filename,
          "Message": f"StarPilot Sentry Mode: {event['message']}",
        })
        response = requests.put(ntfy_url, data=image_data, headers=headers, timeout=10)
      response.raise_for_status()
    except Exception:
      _galaxy["cloudlog"].exception("Galaxy: ntfy notification failed")



def register_sentry_routes(app, galaxy_globals):
  global _galaxy
  _galaxy = galaxy_globals

  @app.route("/service-worker.js", methods=["GET"])
  def sentry_service_worker():
    response = _galaxy["send_from_directory"](app.static_folder, "service-worker.js", mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Service-Worker-Allowed"] = "/"
    return response

  @app.route("/api/sentry/push/config", methods=["GET"])
  def sentry_push_config():
    try:
      public_key = _sentry_vapid_public_key(_get_sentry_vapid())
    except (RuntimeError, ModuleNotFoundError) as error:
      _galaxy["cloudlog"].warning("Galaxy: Sentry Web Push dependencies unavailable: %s", error)
      return _galaxy["jsonify"]({"enabled": False, "error": "Web Push dependencies are unavailable."}), 503
    except Exception as error:
      _galaxy["cloudlog"].exception("Galaxy: Failed to initialize Sentry Web Push: %s", error)
      return _galaxy["jsonify"]({"enabled": False, "error": f"Push notification service error: {error}"}), 500

    return _galaxy["jsonify"]({
      "enabled": True,
      "publicKey": public_key,
      "subscriptionCount": _sentry_push_subscription_count(),
    })

  @app.route("/api/sentry/push/subscribe", methods=["POST"])
  def sentry_push_subscribe():
    subscription = _normalize_sentry_push_subscription(_galaxy["request"].get_json(silent=True))
    if subscription is None:
      return _galaxy["jsonify"]({"error": "Invalid browser push subscription."}), 400

    try:
      _get_sentry_vapid()
    except (RuntimeError, ModuleNotFoundError) as error:
      _galaxy["cloudlog"].warning("Galaxy: Sentry Web Push dependencies unavailable: %s", error)
      return _galaxy["jsonify"]({"error": "Web Push dependencies are unavailable."}), 503
    except Exception as error:
      _galaxy["cloudlog"].exception("Galaxy: Failed to initialize Sentry Web Push for subscription: %s", error)
      return _galaxy["jsonify"]({"error": f"Push notification service error: {error}"}), 500

    with _SENTRY_PUSH_LOCK:
      subscriptions = _load_sentry_push_subscriptions()
      subscriptions = [
        existing for existing in subscriptions
        if existing.get("endpoint") != subscription["endpoint"]
      ]
      subscriptions.append(subscription)
      _save_sentry_push_subscriptions(subscriptions)

    return _galaxy["jsonify"]({"subscribed": True, "subscriptionCount": len(subscriptions)})

  @app.route("/api/sentry/push/unsubscribe", methods=["POST"])
  def sentry_push_unsubscribe():
    payload = _galaxy["request"].get_json(silent=True) or {}
    endpoint = str(payload.get("endpoint") or "").strip()
    if not endpoint:
      return _galaxy["jsonify"]({"error": "Missing browser push endpoint."}), 400

    with _SENTRY_PUSH_LOCK:
      subscriptions = [
        subscription for subscription in _load_sentry_push_subscriptions()
        if subscription.get("endpoint") != endpoint
      ]
      _save_sentry_push_subscriptions(subscriptions)

    return _galaxy["jsonify"]({"unsubscribed": True, "subscriptionCount": len(subscriptions)})

  @app.route("/api/sentry/push/test", methods=["POST"])
  def sentry_push_test():
    if _sentry_push_subscription_count() == 0:
      return _galaxy["jsonify"]({"error": "Enable browser notifications first."}), 409

    event = _sentry_test_notification_event()
    threading.Thread(target=_dispatch_sentry_push, args=(event,), name="galaxy-sentry-push-test", daemon=True).start()
    return _galaxy["jsonify"]({"accepted": True, "eventId": event["eventId"]}), 202

  @app.route("/api/sentry/test-notification", methods=["POST"])
  def sentry_test_notification():
    channels = _sentry_notification_channels()
    if not any(channels.values()):
      return _galaxy["jsonify"]({
        "error": "Configure browser notifications, ntfy, or a webhook before sending a test notification.",
        "channels": channels,
      }), 409

    event = _sentry_test_notification_event()
    threading.Thread(
      target=_dispatch_sentry_event,
      args=(event,),
      kwargs={"bypass_rate_limit": True},
      name="galaxy-sentry-notification-test",
      daemon=True,
    ).start()
    return _galaxy["jsonify"]({
      "accepted": True,
      "eventId": event["eventId"],
      "channels": channels,
    }), 202

  @app.route("/api/sentry/status", methods=["GET"])
  def sentry_status():
    raw_status = _galaxy["params"].get("SentryModeStatus", encoding="utf-8") or "{}"
    try:
      status = json.loads(raw_status)
    except (TypeError, ValueError, json.JSONDecodeError):
      status = {}

    events = _sentry_event_catalog()
    last_event = events[0] if events else {}

    return _galaxy["jsonify"]({
      "enabled": _galaxy["params"].get_bool("SentryModeEnabled"),
      "status": status if isinstance(status, dict) else {},
      "lastEvent": _public_sentry_event(last_event),
    })

  @app.route("/api/sentry/events", methods=["GET"])
  def get_sentry_events():
    since, until, filter_error = _sentry_time_filter_from_request()
    if filter_error:
      return _galaxy["jsonify"]({"error": filter_error}), 400

    events = _filter_sentry_events_by_time(_sentry_event_catalog(), since, until)

    return _galaxy["jsonify"]({
      "events": [_public_sentry_event(event) for event in events],
      "total": len(events),
      "hasMore": False,
    })

  @app.route("/api/sentry/events", methods=["DELETE"])
  def delete_sentry_events():
    if not _galaxy["params"].get_bool("IsOffroad"):
      return _galaxy["jsonify"]({"error": "Sentry events can only be deleted while parked."}), 409

    since, until, filter_error = _sentry_time_filter_from_request()
    if filter_error:
      return _galaxy["jsonify"]({"error": filter_error}), 400
    if since is None and until is None and _galaxy["request"].args.get("all") != "1":
      return _galaxy["jsonify"]({"error": "Refusing to delete every Sentry event without all=1."}), 400

    targets = _filter_sentry_events_by_time(_sentry_event_catalog(), since, until)
    target_ids = {event["eventId"] for event in targets}

    failed = 0
    removed_ids = set()
    for event_id in target_ids:
      if not event_id or event_id in {".", ".."} or Path(event_id).name != event_id:
        failed += 1
        continue
      try:
        _delete_sentry_event_storage(event_id)
        removed_ids.add(event_id)
      except OSError:
        failed += 1

    _forget_sentry_events(removed_ids)

    return _galaxy["jsonify"]({"deleted": len(removed_ids), "failed": failed})

  @app.route("/api/sentry/events/<event_id>", methods=["DELETE"])
  def delete_sentry_event(event_id):
    if not _galaxy["params"].get_bool("IsOffroad"):
      return _galaxy["jsonify"]({"error": "Sentry events can only be deleted while parked."}), 409
    if not event_id or event_id in {".", ".."} or Path(event_id).name != event_id:
      return _galaxy["jsonify"]({"error": "Invalid Sentry event ID."}), 400

    _sentry_event_catalog()

    try:
      deleted_storage = _delete_sentry_event_storage(event_id)
    except OSError:
      return _galaxy["jsonify"]({"error": "Failed to delete the Sentry event's images."}), 500

    catalog_deleted = _forget_sentry_events({event_id})
    if not deleted_storage and not catalog_deleted:
      return _galaxy["jsonify"]({"error": "Sentry event not found."}), 404

    return _galaxy["jsonify"]({"deleted": True, "eventId": event_id})

  @app.route("/api/sentry/timelapse", methods=["GET"])
  def sentry_timelapse():
    if not _galaxy["params"].get_bool("IsOffroad"):
      return _galaxy["jsonify"]({"error": "Sentry timelapse can only be made while parked."}), 409

    since, until, filter_error = _sentry_time_filter_from_request()
    if filter_error:
      return _galaxy["jsonify"]({"error": filter_error}), 400

    camera = _galaxy["request"].args.get("camera", "wide")
    timing = _galaxy["request"].args.get("timing", "gap")
    fps = _galaxy["request"].args.get("fps", default=4, type=int)
    if camera not in _SENTRY_TIMELAPSE_FILES:
      return _galaxy["jsonify"]({"error": "camera must be wide, driver, or both."}), 400
    if timing not in {"gap", "even"}:
      return _galaxy["jsonify"]({"error": "timing must be gap or even."}), 400
    fps = min(max(fps if fps is not None else 4, 1), 30)

    events = _filter_sentry_events_by_time(_sentry_event_catalog(), since, until)
    frames = _sentry_timelapse_sources(events, _SENTRY_TIMELAPSE_FILES[camera], _SENTRY_TIMELAPSE_MAX_FRAMES)
    if not frames:
      return _galaxy["jsonify"]({"error": "No Sentry images to make a timelapse from."}), 404
    durations = _sentry_timelapse_durations(_sentry_timelapse_gaps(frames), timing, fps)

    if not _SENTRY_TIMELAPSE_LOCK.acquire(blocking=False):
      return _galaxy["jsonify"]({"error": "A timelapse is already being made."}), 409
    try:
      data = _encode_sentry_timelapse(frames, durations)
    except (RuntimeError, OSError) as error:
      _galaxy["cloudlog"].exception("sentry timelapse failed")
      return _galaxy["jsonify"]({"error": str(error) or "Timelapse encoding failed."}), 500
    finally:
      _SENTRY_TIMELAPSE_LOCK.release()

    response = _galaxy["Response"](data, mimetype="video/mp4")
    response.headers["Content-Disposition"] = 'attachment; filename="sentry-timelapse.mp4"'
    response.headers["X-Timelapse-Frames"] = str(len(frames))
    response.headers["X-Timelapse-Seconds"] = f"{sum(durations):.1f}"
    response.headers["Cache-Control"] = "no-store"
    return response

  @app.route("/api/sentry/images/<event_id>/<filename>", methods=["GET"])
  def sentry_image(event_id, filename):
    image_path = _sentry_image_path(event_id, filename)
    if image_path is None:
      return _galaxy["jsonify"]({"error": "Sentry image not found."}), 404
    # Stored event images never change, so let the browser keep them (the viewer re-visits frames constantly).
    # The live snapshot is overwritten in place, so it must not be cached.
    max_age = 0 if event_id == _SENTRY_LIVE_EVENT_ID else _SENTRY_IMAGE_CACHE_SECONDS
    return _galaxy["send_file"](image_path, mimetype="image/jpeg", max_age=max_age)

  @app.route("/api/sentry/live", methods=["GET"])
  def sentry_live():
    if not _galaxy["params"].get_bool("IsOffroad"):
      return _galaxy["jsonify"]({"error": "Live Sentry view is only available while parked."}), 409

    with _SENTRY_LIVE_CAPTURE_LOCK:
      image_paths = _capture_sentry_live_images()
    if not image_paths:
      return _galaxy["jsonify"]({"error": "Unable to capture the Sentry cameras."}), 503

    captured_at = datetime.now(timezone.utc).isoformat()
    event = _public_sentry_event({
      "eventId": _SENTRY_LIVE_EVENT_ID,
      "imagePaths": image_paths,
    })
    return _galaxy["jsonify"]({"capturedAt": captured_at, "imageUrls": event["imageUrls"]})

  @app.route("/api/sentry/selfie", methods=["POST"])
  def sentry_selfie():
    if _galaxy["request"].remote_addr not in {None, "127.0.0.1", "::1"}:
      return _galaxy["jsonify"]({"error": "Comma Selfies must originate on the device."}), 403

    with _SENTRY_LIVE_CAPTURE_LOCK:
      jpeg = _galaxy["_get_live_driver_jpeg"]()
    if jpeg is None:
      return _galaxy["jsonify"]({"error": "Unable to capture the driver camera."}), 503

    captured_at = datetime.now(timezone.utc).isoformat()
    event_id = f"selfie-{int(time.time())}-{secrets.token_hex(4)}"
    directory = _sentry_event_roots()[0] / event_id
    directory.mkdir(parents=True, exist_ok=True)
    image_path = directory / "driver.jpg"
    image_path.write_bytes(jpeg)
    event = {
      "eventId": event_id,
      "kind": "selfie",
      "detectedAt": captured_at,
      "imagePaths": [str(image_path)],
      "message": "Comma Selfie",
    }
    _record_sentry_event(event)
    _galaxy["params"].put("SentryModeLastEvent", json.dumps(event, separators=(",", ":")))
    return _galaxy["jsonify"]({"accepted": True, "capturedAt": captured_at, "eventId": event_id}), 201

  @app.route("/api/sentry/test", methods=["POST"])
  def sentry_test():
    if _galaxy["request"].remote_addr not in {None, "127.0.0.1", "::1"}:
      return _galaxy["jsonify"]({"error": "Sentry tests must originate on the device."}), 403
    if not _galaxy["params"].get_bool("IsOffroad"):
      return _galaxy["jsonify"]({"error": "Sentry tests are only available while parked."}), 409

    event_id = f"test-{int(time.time())}-{secrets.token_hex(4)}"
    event = {
      "eventId": event_id,
      "kind": "alarm",
      "detectedAt": datetime.now(timezone.utc).isoformat(),
      "imagePaths": [],
      "message": "Test sentry event.",
    }

    def capture_and_publish():
      event["imagePaths"] = _capture_sentry_test_images(event_id)
      _record_sentry_event(event)
      _galaxy["params"].put("SentryModeLastEvent", json.dumps(event, separators=(",", ":")))
      threading.Thread(
        target=_dispatch_sentry_event,
        args=(event,),
        kwargs={"bypass_rate_limit": True},
        name="galaxy-sentry-test-notify",
        daemon=True,
      ).start()

    threading.Thread(target=capture_and_publish, name="galaxy-sentry-test-capture", daemon=True).start()
    return _galaxy["jsonify"]({"accepted": True, "eventId": event_id}), 202

  @app.route("/api/sentry/events", methods=["POST"])
  def sentry_event():
    if _galaxy["request"].remote_addr not in {None, "127.0.0.1", "::1"}:
      return _galaxy["jsonify"]({"error": "Sentry events must originate on the device."}), 403

    event = _normalize_sentry_event(_galaxy["request"].get_json(silent=True))
    if event is None:
      return _galaxy["jsonify"]({"error": "Invalid sentry event."}), 400

    _record_sentry_event(event)
    _galaxy["params"].put("SentryModeLastEvent", json.dumps(event, separators=(",", ":")))
    if _galaxy["request"].args.get("blocking") == "1":
      _dispatch_sentry_event(event)
    else:
      threading.Thread(target=_dispatch_sentry_event, args=(event,), name="galaxy-sentry-notify", daemon=True).start()
    return _galaxy["jsonify"]({"accepted": True, "eventId": event["eventId"]}), 202

