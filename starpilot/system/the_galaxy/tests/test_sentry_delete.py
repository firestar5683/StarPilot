import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from test_dashboard_stats import FakeParams, MODULE_DIR, _install_server_import_stubs
from test_sentry_push_and_routing import the_galaxy

from openpilot.starpilot.system.the_galaxy import sentry_backend


def _iso(hour: int) -> str:
  return datetime(2026, 9, 1, hour, 0, 0, tzinfo=timezone.utc).isoformat()


class SentryEnv:
  def __init__(self, roots: list[Path], client):
    self.roots = roots
    self.client = client

  def add_event(self, event_id: str, hour: int, roots: tuple[int, ...] = (0,)) -> None:
    """Records an event newer than any recorded before it; its image directory exists in each of `roots`."""
    image_paths = []
    for root_index in roots:
      directory = self.roots[root_index] / event_id
      directory.mkdir(parents=True, exist_ok=True)
      image = directory / "wide.jpg"
      image.write_bytes(b"jpeg")
      image_paths.append(str(image.resolve()))
    sentry_backend._record_sentry_event({
      "eventId": event_id,
      "kind": "warning",
      "detectedAt": _iso(hour),
      "imagePaths": image_paths,
      "message": event_id,
    })

  def set_last_event(self, event_id: str) -> None:
    event = next(event for event in sentry_backend._sentry_event_catalog() if event["eventId"] == event_id)
    the_galaxy.params.put("SentryModeLastEvent", json.dumps(event))

  def catalog_ids(self) -> list[str]:
    return [event["eventId"] for event in sentry_backend._load_sentry_event_catalog_unlocked()]

  def last_event_id(self):
    raw = the_galaxy.params.get("SentryModeLastEvent", encoding="utf-8")
    return json.loads(raw)["eventId"] if raw else None


@pytest.fixture
def env(monkeypatch, tmp_path):
  assert the_galaxy._import_galaxy_web_symbols()
  monkeypatch.setattr(the_galaxy, "params", FakeParams({"IsOffroad": True}))
  monkeypatch.setattr(the_galaxy, "_get_galaxy_dir", lambda: tmp_path)
  roots = [(tmp_path / "root0").resolve(), (tmp_path / "root1").resolve()]
  for root in roots:
    root.mkdir()
  monkeypatch.setattr(sentry_backend, "_sentry_event_roots", lambda: tuple(roots))

  app = the_galaxy.Flask(
    f"test_galaxy_delete_{time.monotonic_ns()}",
    template_folder=str(MODULE_DIR / "templates"),
    static_folder=str(MODULE_DIR / "assets"),
  )
  the_galaxy.setup(app)
  return SentryEnv(roots, app.test_client())


def test_delete_single_removes_storage_and_catalog(env):
  env.add_event("a", 1)
  env.add_event("b", 2, roots=(0, 1))

  response = env.client.delete("/api/sentry/events/b")

  assert response.status_code == 200
  assert env.catalog_ids() == ["a"]
  assert not (env.roots[0] / "b").exists() and not (env.roots[1] / "b").exists()
  assert (env.roots[0] / "a").exists()


def test_delete_single_unknown_event_is_404(env):
  env.add_event("a", 1)
  assert env.client.delete("/api/sentry/events/nope").status_code == 404


def test_delete_single_resyncs_last_event_to_newest_survivor(env):
  env.add_event("a", 1)
  env.add_event("b", 2)
  env.add_event("c", 3)
  env.set_last_event("c")

  assert env.client.delete("/api/sentry/events/c").status_code == 200
  assert env.last_event_id() == "b"

  assert env.client.delete("/api/sentry/events/a").status_code == 200
  assert env.last_event_id() == "b"  # a was not the last event, so the param is untouched


def test_delete_single_removes_last_event_param_when_nothing_is_left(env):
  env.add_event("a", 1)
  env.set_last_event("a")

  assert env.client.delete("/api/sentry/events/a").status_code == 200
  assert env.last_event_id() is None


def test_delete_all_requires_all_flag(env):
  env.add_event("a", 1)
  assert env.client.delete("/api/sentry/events").status_code == 400
  assert env.catalog_ids() == ["a"]


def test_delete_all_clears_everything_and_the_last_event_param(env):
  env.add_event("a", 1)
  env.add_event("b", 2, roots=(0, 1))
  env.set_last_event("b")

  response = env.client.delete("/api/sentry/events?all=1")

  assert response.get_json() == {"deleted": 2, "failed": 0}
  assert env.catalog_ids() == []
  assert env.last_event_id() is None
  assert not (env.roots[1] / "b").exists()


def test_delete_range_resyncs_last_event_to_newest_survivor(env):
  env.add_event("old", 1)
  env.add_event("mid", 5)
  env.add_event("new", 9)
  env.set_last_event("new")

  # Delete the newest event only: since is inclusive, so [08:00, ...) matches "new".
  response = env.client.delete("/api/sentry/events", query_string={"since": _iso(8)})

  assert response.get_json() == {"deleted": 1, "failed": 0}
  assert env.catalog_ids() == ["mid", "old"]
  assert env.last_event_id() == "mid"


def test_delete_range_leaves_last_event_param_when_it_survives(env):
  env.add_event("old", 1)
  env.add_event("new", 9)
  env.set_last_event("new")

  env.client.delete("/api/sentry/events", query_string={"until": _iso(5)})

  assert env.catalog_ids() == ["new"]
  assert env.last_event_id() == "new"


def _fail_rmtree_under(monkeypatch, failing_root: Path):
  real_rmtree = the_galaxy.shutil.rmtree

  def rmtree(path, *args, **kwargs):
    if failing_root in Path(path).parents:
      raise OSError("simulated rmtree failure")
    return real_rmtree(path, *args, **kwargs)

  monkeypatch.setattr(the_galaxy.shutil, "rmtree", rmtree)


def test_bulk_delete_keeps_event_and_logs_when_a_later_root_fails(env, monkeypatch):
  env.add_event("a", 1)
  env.add_event("b", 2, roots=(0, 1))
  _fail_rmtree_under(monkeypatch, env.roots[1])
  logged = []
  monkeypatch.setattr(the_galaxy.cloudlog, "exception", lambda message, *args, **kwargs: logged.append(message))

  response = env.client.delete("/api/sentry/events?all=1")

  assert response.get_json() == {"deleted": 1, "failed": 1}
  assert env.catalog_ids() == ["b"]  # still listed: its root-1 storage still exists, so a retry can finish it
  assert (env.roots[1] / "b").exists()
  assert not (env.roots[0] / "b").exists()  # the root that succeeded was still cleaned
  assert len(logged) == 1 and "root1" in logged[0]


def test_single_delete_returns_500_when_storage_removal_fails(env, monkeypatch):
  env.add_event("b", 2, roots=(0, 1))
  _fail_rmtree_under(monkeypatch, env.roots[1])
  monkeypatch.setattr(the_galaxy.cloudlog, "exception", lambda *args, **kwargs: None)

  response = env.client.delete("/api/sentry/events/b")

  assert response.status_code == 500
  assert "error" in response.get_json()
  assert env.catalog_ids() == ["b"]


def test_test_events_are_first_class_timelapse_sources(env):
  env.add_event("test-123-abcd", 1)
  env.add_event("real", 2)
  events = sentry_backend._sentry_event_catalog()

  frames = sentry_backend._sentry_timelapse_sources(events, ("wide.jpg",), 600)

  assert len(frames) == 2


def test_timelapse_skips_a_frame_deleted_mid_encode(env, monkeypatch, tmp_path):
  env.add_event("a", 1)
  env.add_event("b", 2)
  env.add_event("c", 3)
  frames = sentry_backend._sentry_timelapse_sources(sentry_backend._sentry_event_catalog(), ("wide.jpg",), 600)
  assert len(frames) == 3

  def render(paths, detected_at, kind, gap, index, positions, kinds, output_path):
    if "b" in {path.parent.name for path in paths}:
      raise FileNotFoundError(str(paths[0]))
    output_path.write_bytes(b"frame")

  encoded = []

  def run(command, **kwargs):
    sequence = Path(command[command.index("-i") + 1]).parent
    encoded.extend(sorted(path.name for path in sequence.iterdir()))
    Path(command[-1]).write_bytes(b"mp4")

    class Result:
      returncode = 0
      stderr = b""

    return Result()

  warnings = []
  monkeypatch.setattr(the_galaxy.cloudlog, "warning", warnings.append, raising=False)  # the shared stub has no .warning
  monkeypatch.setattr(sentry_backend, "_render_sentry_timelapse_frame", render)
  monkeypatch.setattr(the_galaxy.subprocess, "run", run)

  data = sentry_backend._encode_sentry_timelapse(frames, [1.0, 1.0, 1.0])

  assert data == b"mp4"
  fps = sentry_backend._SENTRY_TIMELAPSE_OUTPUT_FPS
  assert len(encoded) == 2 * fps  # frames a and c, one second each; b was skipped
  assert len(warnings) == 1 and "/b/" in warnings[0]


@pytest.mark.skipif(shutil.which(getattr(the_galaxy.utilities, "FFMPEG_BIN", "ffmpeg")) is None, reason="ffmpeg not installed")
def test_timelapse_real_encode_skips_a_frame_deleted_mid_encode(env, monkeypatch, tmp_path):
  from PIL import Image

  for hour, event_id in enumerate(("a", "b", "c"), start=1):
    env.add_event(event_id, hour)
    Image.new("RGB", (320, 180), (40 * hour, 90, 160)).save(env.roots[0] / event_id / "wide.jpg")
  frames = sentry_backend._sentry_timelapse_sources(sentry_backend._sentry_event_catalog(), ("wide.jpg",), 600)
  assert len(frames) == 3

  real_render = sentry_backend._render_sentry_timelapse_frame

  def render_with_delete(paths, detected_at, kind, gap, index, positions, kinds, output_path):
    if index == 1:  # the user deletes the middle event just before its frame is rendered
      shutil.rmtree(paths[0].parent)
    return real_render(paths, detected_at, kind, gap, index, positions, kinds, output_path)

  monkeypatch.setattr(sentry_backend, "_render_sentry_timelapse_frame", render_with_delete)
  monkeypatch.setattr(the_galaxy.cloudlog, "warning", lambda *args, **kwargs: None, raising=False)

  data = sentry_backend._encode_sentry_timelapse(frames, [1.0, 1.0, 1.0])

  video = tmp_path / "out.mp4"
  video.write_bytes(data)
  assert data[4:8] == b"ftyp"
  probe = subprocess.run(
    [str(Path(the_galaxy.utilities.FFMPEG_BIN).with_name("ffprobe")), "-v", "error", "-select_streams", "v:0",
     "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(video)],
    capture_output=True, text=True,
  )
  assert probe.returncode == 0, probe.stderr
  assert int(probe.stdout.strip()) == 2 * sentry_backend._SENTRY_TIMELAPSE_OUTPUT_FPS  # frames a and c, one second each
