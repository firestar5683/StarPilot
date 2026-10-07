"""Map overlay geometry (CPU) and rendering (STARPILOT_AUTO_GL_TEST=1 for a real GL context)."""

import math
import os
import time

import numpy as np

from openpilot.starpilot.navigation.offline_roads import TileStore
from openpilot.starpilot.navigation.road_tiles import (
  DATA_ZOOM, EXTENT, MAJOR, MINOR, MOTORWAY, STREET, TileKey, decode_road_tile, encode_road_tile, lat_lon, world_xy,
)
from openpilot.starpilot.ui.onroad_map import (
  CAR_ANCHOR, ZOOM_FAST_M_PER_PX, ZOOM_SLOW_M_PER_PX, CanvasRequest, MapFix, MapInput, MapOverlay, TileReader,
  build_canvas, line_strip, split_route, zoom_for_speed,
)
from openpilot.starpilot.system.android_auto.tests import test_gpu_nv12

gl = test_gpu_nv12.gpu  # the shared GL context fixture, under this module's name

CENTER = (36.1147, -115.1728)


def test_line_strip_joins_lines_with_degenerate_triangles():
  points = np.array([[0, 0], [10, 0], [10, 10], [50, 50], [60, 50]], np.float32)
  offsets = np.array([0, 3, 5], np.int32)
  strip = line_strip(points, offsets, 2.0, (-100, -100, 100, 100))
  assert len(strip) == 2 * 5 + 2, "two vertices per point plus one repeat on each side of the join"
  assert np.allclose(strip[0], [0, -2]) and np.allclose(strip[1], [0, 2]), "right then left of travel (y down)"
  assert np.allclose(strip[5], strip[6]) and np.allclose(strip[7], strip[8]), "the bridge is zero-area"
  # Mitered corner: the outer offset sits on both edges' offset lines.
  assert np.allclose(strip[2], [12, -2]) and np.allclose(strip[3], [8, 2])


def test_line_strip_culls_offscreen_lines_and_caps_spikes():
  points = np.array([[500, 500], [510, 500], [0, 0], [10, 0], [0, 0]], np.float32)
  strip = line_strip(points, np.array([0, 2, 5], np.int32), 1.0, (-5, -5, 50, 50))
  assert len(strip) == 6 and strip[:, 0].max() < 20
  assert np.abs(strip).max() < 1.0 + 10 + 2.5, "a hairpin's miter is capped"
  assert line_strip(points[:2], np.array([0, 2], np.int32), 1.0, (-5, -5, 50, 50)).shape == (0, 2)


def test_split_route_at_the_car():
  route = np.array([[0, 0], [0, 10], [10, 10]], float)
  done, ahead = split_route(route, (0.5, 4.0))
  assert done.tolist() == [[0, 0], [0, 4]] and ahead.tolist() == [[0, 4], [0, 10], [10, 10]]
  assert split_route(None, (0, 0)) == (None, None)


def test_zoom_widens_with_speed():
  assert zoom_for_speed(0) == ZOOM_SLOW_M_PER_PX and zoom_for_speed(40) == ZOOM_FAST_M_PER_PX
  speeds = [zoom_for_speed(v) for v in range(40)]
  assert speeds == sorted(speeds)


def synthetic_tile(key):
  """A street grid, plus a north-south motorway and an east-west major road crossing at CENTER."""
  x, y = world_xy(*CENTER)
  mx, my = round((x % 1) * EXTENT), round((y % 1) * EXTENT)
  roads = {STREET: [], MINOR: [], MAJOR: [np.array([[0, my], [4096, my]])], MOTORWAY: [np.array([[mx, 0], [mx, 4096]])]}
  for i in range(256, 4096, 512):
    roads[STREET].append(np.array([[i, 0], [i, 4096]]))
    roads[STREET].append(np.array([[0, i], [4096, i]]))
    roads[MINOR].append(np.array([[i + 128, i], [i + 300, i + 200], [i + 128, i + 400]]))
  return encode_road_tile(roads)


def tiles_around(latitude, longitude, radius=2):
  x, y = world_xy(latitude, longitude)
  return [TileKey(DATA_ZOOM, int(x) + dx, int(y) + dy) for dy in range(-radius, radius + 1) for dx in range(-radius, radius + 1)]


def test_canvas_layers_order_and_highway_simplification():
  keys = tiles_around(*CENTER, 1)
  tiles = {key: decode_road_tile(key, synthetic_tile(key)) for key in keys}
  center = world_xy(*CENTER)
  route = np.array([center, (center[0], center[1] - 0.3)])
  slow = build_canvas(CanvasRequest(center, ZOOM_SLOW_M_PER_PX, 1536, route, None, tuple(keys)), tiles, CENTER[0])
  fast = build_canvas(CanvasRequest(center, ZOOM_FAST_M_PER_PX, 1536, route, None, tuple(keys)), tiles, CENTER[0])
  assert slow.tiles_missing == 0
  # Casings, then fills, then the route glow and core on top.
  alphas = [color.a for color, _ in slow.guidance]
  assert len(slow.layers) == 2 * 4 and len(slow.guidance) == 2 and alphas[-2] < 255 and alphas[-1] == 255
  assert len(fast.layers) == 2 * 3 and len(fast.guidance) == 2, "minor roads drop out at highway zoom"
  overview = build_canvas(CanvasRequest(center, 5.0, 1536, None, None, tuple(keys)), tiles, CENTER[0])
  assert len(overview.layers) == 2 * 2, "and streets when zoomed out further"
  missing = build_canvas(CanvasRequest(center, 1.0, 1536, None, None, tuple(keys) + (TileKey(14, 0, 0),)), tiles, CENTER[0])
  assert missing.tiles_missing == 1


def test_tile_reader_loads_from_disk_and_retries_missing(tmp_path):
  store = TileStore(tmp_path, min_free_bytes=0)
  key = TileKey(DATA_ZOOM, 10, 10)
  clock = [0.0]
  reader = TileReader(tmp_path, clock=lambda: clock[0])
  try:
    reader.want([key])
    time.sleep(0.2)
    assert reader.snapshot([key]) == {}
    store.write("cache", key, synthetic_tile(key))
    clock[0] += 10
    reader.want([key])
    deadline = time.monotonic() + 3
    while not reader.snapshot([key]) and time.monotonic() < deadline:
      time.sleep(0.02)
    assert key in reader.snapshot([key]) and reader.generation == 1
  finally:
    reader.close()


# ---------------------------------------------------------------- GL

def render_overlay(rl, tmp_path, bearing, width=560, height=420, opacity=1.0, route=True, steps=40):
  store = TileStore(tmp_path, min_free_bytes=0)
  for key in tiles_around(*CENTER):
    store.write("saved", key, synthetic_tile(key))
  clock = [100.0]
  overlay = MapOverlay(tmp_path, clock=lambda: clock[0])
  x, y = world_xy(*CENTER)
  path = tuple(lat_lon(x + dx, y + dy) for dx, dy in ((0, 0.2), (0, 0.02), (0.08, 0.02), (0.08, -0.4)))
  data = MapInput(MapFix(*CENTER, bearing, 3.0, clock[0]), path if route else ())
  try:
    for _ in range(steps):
      overlay.prepare(data, width, height)
      if overlay.has_roads and overlay._pending is overlay._canvas_request and overlay.reader.generation == overlay._generation_built:
        break
      time.sleep(0.05)
    overlay.prepare(data, width, height)
    target = rl.load_render_texture(width, height)
    rl.begin_texture_mode(target)
    rl.clear_background(rl.Color(70, 90, 70, 255))          # stands in for the camera
    overlay.draw(rl.Rectangle(0, 0, width, height), opacity)
    rl.end_texture_mode()
    image = rl.load_image_from_texture(target.texture)
    rl.image_flip_vertical(image)
    pixels = np.frombuffer(rl.ffi.buffer(image.data, width * height * 4), np.uint8).reshape(height, width, 4).copy()
    rl.unload_image(image)
    rl.unload_render_texture(target)
    return pixels
  finally:
    overlay.close()


def yellow(pixels):
  r, g, b = (pixels[..., i].astype(int) for i in range(3))
  return (r > 200) & (g > 150) & (b < 140)


def test_overlay_draws_heading_up_roads_route_and_soft_edges(gl, tmp_path):
  rl = gl
  north = render_overlay(rl, tmp_path / "n", bearing=0.0)
  east = render_overlay(rl, tmp_path / "e", bearing=90.0)
  height, width = north.shape[:2]
  # The motorway runs north-south through the car: vertical when heading north, horizontal when heading east.
  if os.getenv("STARPILOT_MAP_PREVIEW_DIR"):
    for name, pixels in (("map_north.png", north), ("map_east.png", east)):
      image = rl.Image(rl.ffi.from_buffer(np.ascontiguousarray(pixels)), width, height, 1, 7)
      rl.export_image(image, os.path.join(os.environ["STARPILOT_MAP_PREVIEW_DIR"], name))
  ys, xs = np.nonzero(yellow(north))
  assert len(xs) > 200 and np.ptp(ys) > height * 0.6 and np.ptp(xs) < 40
  ys, xs = np.nonzero(yellow(east))
  assert len(xs) > 200 and np.ptp(xs) > width * 0.6 and np.ptp(ys) < 40
  # The car puck is white at its anchor; the corners fade to the camera underneath.
  car = north[int(height * CAR_ANCHOR), width // 2]
  assert car[:3].min() > 200
  assert np.abs(north[2, 2, :3].astype(int) - (70, 90, 70)).max() < 6
  # The route (violet) shows ahead of the car.
  r, g, b = (north[..., i].astype(int) for i in range(3))
  assert ((b > 200) & (r > 120) & (r < 210) & (g < 175)).sum() > 300


def test_overlay_opacity_fades_map_background(gl, tmp_path):
  rl = gl
  full = render_overlay(rl, tmp_path / "a", bearing=0.0, opacity=1.0, route=False).astype(int)
  half = render_overlay(rl, tmp_path / "b", bearing=0.0, opacity=0.35, route=False).astype(int)
  camera = np.array([70, 90, 70])
  center = (slice(100, 240), slice(100, 360))
  full_delta = np.abs(full[center][..., :3] - camera).mean()
  half_delta = np.abs(half[center][..., :3] - camera).mean()
  assert 0.25 < half_delta / full_delta < 0.45


def test_overlay_without_gps_waits_without_drawing_roads(gl, tmp_path):
  rl = gl
  overlay = MapOverlay(tmp_path)
  try:
    overlay.prepare(MapInput(None), 300, 220)
    assert overlay.status == "waiting" and not overlay.has_roads
    target = rl.load_render_texture(300, 220)
    rl.begin_texture_mode(target)
    overlay.draw(rl.Rectangle(0, 0, 300, 220), 0.7)
    rl.end_texture_mode()
    rl.unload_render_texture(target)
  finally:
    overlay.close()
  assert math.isfinite(EXTENT)


class FakeGpsMaster:
  """SubMaster shape that starpilot.gps.source.select_location reads."""

  def __init__(self):
    from types import SimpleNamespace
    self.ns = SimpleNamespace
    self.messages, self.valid, self.logMonoTime = {}, {}, {}

  def update(self, _timeout):
    pass

  def __getitem__(self, service):
    return self.messages[service]

  def put(self, service, stamp, **gps):
    fields = {"hasFix": True, "latitude": 36.1, "longitude": -115.1, "horizontalAccuracy": 5.0, "speed": 10.0,
              "bearingDeg": 90.0, "bearingAccuracyDeg": 5.0, **gps}
    if service == "starpilotCarState":
      self.messages[service] = self.ns(gps=self.ns(sourceMonoTime=stamp, **fields))
    else:
      from openpilot.starpilot.gps.source import GPS_SOURCES
      self.messages[service] = self.ns(source=GPS_SOURCES[service], **fields)
    self.valid[service], self.logMonoTime[service] = True, stamp


def test_map_feed_uses_navigation_gps_choice_with_car_fallback(monkeypatch):
  from openpilot.starpilot.gps.source import GPS_SOURCES
  from openpilot.starpilot.ui.onroad_map import MapFeed
  now = 50_000_000_000
  monkeypatch.setattr(time, "monotonic_ns", lambda: now)
  monkeypatch.setattr(time, "monotonic", lambda: now / 1e9)
  sm = FakeGpsMaster()
  for service in GPS_SOURCES:
    sm.valid[service], sm.logMonoTime[service] = False, 0
  feed = MapFeed(sm)
  assert feed.read().fix is None
  sm.put("starpilotCarState", now - 200_000_000, latitude=36.2)
  fix = feed.read().fix
  assert fix.latitude == 36.2 and fix.monotonic == (now - 200_000_000) / 1e9, "the car's GPS when no receiver has a fix"
  sm.put("gpsLocationExternal", now - 100_000_000, latitude=36.3, bearingAccuracyDeg=200.0)
  fix = feed.read().fix
  assert fix.latitude == 36.3 and fix.bearing is None, "a receiver wins; an unusable heading is dropped"


def test_route_stays_bright_at_minimum_map_opacity(gl, tmp_path):
  full = render_overlay(gl, tmp_path / "full", bearing=0.0, opacity=1.0)
  faded = render_overlay(gl, tmp_path / "faded", bearing=0.0, opacity=0.15)
  r, g, b = (full[..., i].astype(int) for i in range(3))
  core = (b > 245) & (r > 130) & (r < 210) & (g < 180)
  assert core.sum() > 100
  assert np.abs(full[core, :3].astype(int) - faded[core, :3].astype(int)).mean() < 3
  assert np.abs(faded[2, 2, :3].astype(int) - (70, 90, 70)).max() < 6
