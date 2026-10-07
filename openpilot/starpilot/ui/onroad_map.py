"""Heading-up road-line map, drawn as a translucent overlay on the Android Auto screen.

Roads come from the compact tiles ``navtilesd`` writes; this module never
touches the network. The work is split so no frame waits on anything slow:

  worker thread   reads and decodes tiles, and turns roads and the route into
                  triangle strips for a north-up canvas around the car
  prepare()       outside any parent render target: draws a finished canvas
                  into a texture (only when one is ready), then composes the
                  widget: canvas rotated heading-up, the car, a glass tint
  draw()          inside the frame: one textured quad through a shader that
                  rounds and feathers the edges; opacity fades the map, not navigation guidance

Colors are premultiplied end to end, so translucent glows and the feathered
edge composite without dark fringes.
"""

from __future__ import annotations

import math
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyray as rl

from openpilot.starpilot.navigation.road_tiles import (
  DATA_ZOOM, EXTENT, LINK, MAJOR, MINOR, MOTORWAY, STREET, RoadTile, TileFormatError, TileKey, decode_road_tile,
  encode_road_tile, meters_per_tile, world_xy,
)
from openpilot.system.ui.lib.application import GL_VERSION

SUPERSAMPLE = 1.5            # canvas pixels per screen pixel: edges are smoothed when it is scaled down
MAX_CANVAS = 2560
TILE_CACHE = 48
MISSING_RETRY_S = 3.0
DEAD_RECKON_S = 1.0
CAR_ANCHOR = 0.68            # the car sits below center so more road ahead is visible
ZOOM_SLOW_M_PER_PX = 0.9     # parking-lot and city detail
ZOOM_FAST_M_PER_PX = 3.4     # highway overview
MIN_HEADING_SPEED = 1.5      # m/s; GPS heading is noise below this


@dataclass(frozen=True)
class RoadStyle:
  fill: tuple[int, int, int]
  width: float               # screen pixels at the reference zoom
  hide_above_m_per_px: float = math.inf


# Bottom to top. Casings go under every fill so crossings read cleanly.
ROAD_STYLES: dict[int, RoadStyle] = {
  MINOR: RoadStyle((112, 124, 140), 2.4, hide_above_m_per_px=2.2),
  STREET: RoadStyle((176, 188, 204), 3.4, hide_above_m_per_px=4.5),
  LINK: RoadStyle((214, 220, 232), 3.6),
  MAJOR: RoadStyle((236, 240, 246), 5.2),
  MOTORWAY: RoadStyle((255, 196, 92), 6.8),
}
CASING = (0, 0, 0, 200)
CASING_EXTRA = 2.6
ROUTE_GLOW = (150, 110, 255, 90)
ROUTE_CORE = (178, 150, 255, 255)
ROUTE_DONE = (118, 104, 150, 200)
GLASS = (8, 12, 20, 132)
REFERENCE_M_PER_PX = 1.4


def premultiplied(color: Sequence[int], alpha_scale: float = 1.0) -> rl.Color:
  r, g, b, a = (*color, 255) if len(color) == 3 else color
  alpha = a / 255.0 * alpha_scale
  return rl.Color(round(r * alpha), round(g * alpha), round(b * alpha), round(255 * alpha))


def zoom_for_speed(speed_mps: float) -> float:
  """Meters per screen pixel: street detail when slow, a wider view at highway speed."""
  t = min(1.0, max(0.0, (speed_mps - 8.0) / 24.0))
  t = t * t * (3 - 2 * t)
  return ZOOM_SLOW_M_PER_PX + (ZOOM_FAST_M_PER_PX - ZOOM_SLOW_M_PER_PX) * t


# ---------------------------------------------------------------- geometry

def line_strip(points: np.ndarray, offsets: np.ndarray, half_width: float, bounds: tuple[float, float, float, float],
               max_miter: float = 2.5) -> np.ndarray:
  """One triangle strip for many polylines: mitered quads, joined by degenerate triangles.

  ``points`` (N, 2) and ``offsets`` (L + 1) describe L polylines of at least two
  points. Lines entirely outside ``bounds`` (x0, y0, x1, y1) are skipped.
  """
  if len(offsets) < 2 or len(points) < 2:
    return np.empty((0, 2), np.float32)
  starts, ends = offsets[:-1], offsets[1:]
  x0, y0, x1, y1 = bounds
  lo, hi = np.minimum.reduceat(points, starts, axis=0), np.maximum.reduceat(points, starts, axis=0)
  keep = (hi[:, 0] >= x0) & (lo[:, 0] <= x1) & (hi[:, 1] >= y0) & (lo[:, 1] <= y1) & (ends - starts >= 2)
  if not keep.any():
    return np.empty((0, 2), np.float32)
  lengths = (ends - starts)[keep]
  line_offsets = np.concatenate(([0], np.cumsum(lengths)[:-1]))
  index = np.arange(int(lengths.sum())) - np.repeat(line_offsets, lengths) + np.repeat(starts[keep], lengths)
  p = points[index].astype(np.float32)
  first = np.zeros(len(p), bool)
  first[np.concatenate(([0], np.cumsum(lengths)[:-1]))] = True
  last = np.roll(first, -1)
  last[-1] = True

  seg = np.diff(p, axis=0)
  norm = np.hypot(seg[:, 0], seg[:, 1])
  seg /= np.maximum(norm, 1e-6)[:, None]
  normal = np.stack((-seg[:, 1], seg[:, 0]), axis=1)           # left of travel
  n_prev = np.vstack((normal[:1], normal))                     # segment ending at each vertex
  n_next = np.vstack((normal, normal[-1:]))                    # segment starting at each vertex
  n_prev[first] = n_next[first]
  n_next[last] = n_prev[last]
  miter = n_prev + n_next
  miter_len = np.hypot(miter[:, 0], miter[:, 1])
  flat = miter_len < 1e-3                                      # a full reversal: fall back to the segment normal
  miter[flat] = n_next[flat]
  miter_len[flat] = 1.0
  miter /= miter_len[:, None]
  scale = 1.0 / np.clip(np.einsum("ij,ij->i", miter, n_next), 1.0 / max_miter, 1.0)
  offset = miter * (scale * half_width)[:, None]

  # Right of travel, then left: front-facing for raylib in y-down screen space,
  # so backface culling never drops a road.
  strip = np.empty((len(p) * 2, 2), np.float32)
  strip[0::2] = p - offset
  strip[1::2] = p + offset
  # Repeat the last vertex of each line and the first of the next: two zero-area
  # triangles bridge the gap and keep every real triangle's winding.
  repeat = np.ones(len(strip), np.int64)
  line_starts = np.flatnonzero(first) * 2
  repeat[line_starts[1:]] += 1
  repeat[line_starts[1:] - 1] += 1
  return np.repeat(strip, repeat, axis=0)


@dataclass
class CanvasRequest:
  center: tuple[float, float]          # world (data-zoom tile units) at the canvas center
  m_per_px: float                      # screen meters per pixel this canvas was built for
  side: int                            # canvas texture side in pixels (supersampled)
  route: np.ndarray | None             # (N, 2) world points ahead of the car
  route_done: np.ndarray | None        # (N, 2) world points already driven
  tiles: tuple[TileKey, ...]


@dataclass
class CanvasGeometry:
  request: CanvasRequest
  layers: list[tuple[rl.Color, np.ndarray]] = field(default_factory=list)
  tiles_missing: int = 0
  guidance: list[tuple[rl.Color, np.ndarray]] = field(default_factory=list)


def build_canvas(request: CanvasRequest, tiles: dict[TileKey, RoadTile], latitude: float) -> CanvasGeometry:
  """Screen-space strips for a north-up canvas. Pure numpy; runs off the render thread."""
  side = request.side
  px_per_m = SUPERSAMPLE / request.m_per_px
  px_per_unit = meters_per_tile(latitude) * px_per_m           # canvas pixels per world tile unit
  cx, cy = request.center
  bounds = (-8.0, -8.0, side + 8.0, side + 8.0)
  ratio = math.sqrt(REFERENCE_M_PER_PX / request.m_per_px)
  width_scale = SUPERSAMPLE * min(1.35, max(0.7, ratio))
  geometry = CanvasGeometry(request)
  per_class: dict[int, list[tuple[np.ndarray, np.ndarray]]] = {}
  for key in request.tiles:
    tile = tiles.get(key)
    if tile is None:
      geometry.tiles_missing += 1
      continue
    ox = (key.x - cx) * px_per_unit + side / 2
    oy = (key.y - cy) * px_per_unit + side / 2
    scale = px_per_unit / EXTENT
    for road_class, (points, offsets) in tile.lines.items():
      if request.m_per_px > ROAD_STYLES[road_class].hide_above_m_per_px:
        continue
      per_class.setdefault(road_class, []).append((points * scale + (ox, oy), offsets))
  merged = {}
  for road_class, parts in per_class.items():
    points = np.concatenate([part[0] for part in parts])
    offsets, base = [np.zeros(1, np.int32)], 0
    for part_points, part_offsets in parts:
      offsets.append(part_offsets[1:] + base)
      base += len(part_points)
    merged[road_class] = (points, np.concatenate(offsets))
  order = [c for c in ROAD_STYLES if c in merged]
  for road_class in order:
    style = ROAD_STYLES[road_class]
    strip = line_strip(*merged[road_class], (style.width + CASING_EXTRA) * width_scale / 2, bounds)
    if len(strip):
      geometry.layers.append((premultiplied(CASING), strip))
  for road_class in order:
    style = ROAD_STYLES[road_class]
    strip = line_strip(*merged[road_class], style.width * width_scale / 2, bounds)
    if len(strip):
      geometry.layers.append((premultiplied(style.fill), strip))

  def route_points(world):
    return ((world - (cx, cy)) * px_per_unit + side / 2).astype(np.float32)

  for world, layers in ((request.route_done, ((ROUTE_DONE, 5.0),)),
                        (request.route, ((ROUTE_GLOW, 17.0), (ROUTE_CORE, 7.0)))):
    if world is not None and len(world) >= 2:
      points = route_points(world)
      for color, width in layers:
        strip = line_strip(points, np.array([0, len(points)], np.int32), width * width_scale / 2, bounds)
        if len(strip):
          target = geometry.guidance if world is request.route else geometry.layers
          target.append((premultiplied(color), strip))
  return geometry


def split_route(route: np.ndarray, position: tuple[float, float]) -> tuple[np.ndarray | None, np.ndarray | None]:
  """(driven, ahead) world polylines, split at the point on the route nearest the car."""
  if route is None or len(route) < 2:
    return None, None
  a, b = route[:-1], route[1:]
  ab = b - a
  t = np.clip(np.einsum("ij,ij->i", np.asarray(position) - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-12), 0, 1)
  nearest = a + ab * t[:, None]
  index = int(np.argmin(np.hypot(*(nearest - position).T)))
  split = nearest[index]
  return np.vstack((route[:index + 1], split)), np.vstack((split, route[index + 1:]))


# ---------------------------------------------------------------- data

@dataclass(frozen=True)
class MapFix:
  latitude: float
  longitude: float
  bearing: float | None
  speed: float
  monotonic: float


@dataclass(frozen=True)
class MapInput:
  fix: MapFix | None
  route: tuple[tuple[float, float], ...] = ()      # (latitude, longitude)


class TileReader:
  """Road tiles from disk, decoded on a worker thread; the render thread only reads the cache."""

  def __init__(self, root: Path | None = None, clock: Callable[[], float] = time.monotonic):
    from openpilot.starpilot.navigation.offline_roads import TileStore
    self.store = TileStore(root)
    self.clock = clock
    self._lock = threading.Condition()
    self._tiles: OrderedDict[TileKey, RoadTile] = OrderedDict()
    self._missing: dict[TileKey, float] = {}
    self._wanted: tuple[TileKey, ...] = ()
    self._jobs: list[Callable[[], None]] = []
    self.generation = 0
    self._stopped = False
    self._thread = threading.Thread(target=self._run, name="map-tiles", daemon=True)
    self._thread.start()

  def want(self, keys: Sequence[TileKey]) -> None:
    with self._lock:
      self._wanted = tuple(keys)
      self._lock.notify()

  def submit(self, job: Callable[[], None]) -> None:
    with self._lock:
      self._jobs = [job]          # only the newest canvas matters
      self._lock.notify()

  def snapshot(self, keys: Sequence[TileKey]) -> dict[TileKey, RoadTile]:
    with self._lock:
      return {key: self._tiles[key] for key in keys if key in self._tiles}

  def _next_load(self) -> TileKey | None:
    now = self.clock()
    for key in self._wanted:
      if key not in self._tiles and self._missing.get(key, -math.inf) <= now:
        return key
    return None

  def _run(self) -> None:
    while True:
      with self._lock:
        while not self._stopped and not self._jobs and self._next_load() is None:
          self._lock.wait(timeout=MISSING_RETRY_S / 2)
        if self._stopped:
          return
        key = self._next_load()
        job = self._jobs.pop() if key is None and self._jobs else None
      if key is not None:
        raw = self.store.read(key)
        try:
          tile = decode_road_tile(key, raw) if raw is not None else None
        except TileFormatError:
          tile = None
        with self._lock:
          if tile is None:
            self._missing[key] = self.clock() + MISSING_RETRY_S
          else:
            self._missing.pop(key, None)
            self._tiles[key] = tile
            self._tiles.move_to_end(key)
            while len(self._tiles) > TILE_CACHE:
              self._tiles.popitem(last=False)
            self.generation += 1
      elif job is not None:
        try:
          job()
        except Exception:
          pass

  def close(self) -> None:
    with self._lock:
      self._stopped = True
      self._lock.notify()
    self._thread.join(timeout=1.0)


# ---------------------------------------------------------------- shader

MASK_VERTEX = GL_VERSION + """
in vec3 vertexPosition;
in vec2 vertexTexCoord;
in vec4 vertexColor;
out vec2 fragTexCoord;
uniform mat4 mvp;
void main() {
  fragTexCoord = vertexTexCoord;
  gl_Position = mvp * vec4(vertexPosition, 1.0);
}
"""

MASK_FRAGMENT = GL_VERSION + """
in vec2 fragTexCoord;
out vec4 finalColor;
uniform sampler2D texture0;
uniform sampler2D guidance;
uniform vec2 size;       // widget pixels
uniform float radius;    // corner radius in pixels
uniform float feather;   // soft edge width in pixels
uniform float opacity;
void main() {
  vec2 p = fragTexCoord * size;
  vec2 q = abs(p - size * 0.5) - (size * 0.5 - vec2(radius));
  float outside = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;   // rounded-rect distance, < 0 inside
  float edge = clamp(-outside / feather, 0.0, 1.0);
  edge = edge * edge * (3.0 - 2.0 * edge);
  // The glass fades a little toward the top so the road ahead blends into the camera.
  float top = smoothstep(0.0, 0.22, fragTexCoord.y) * 0.35 + 0.65;
  // A faint glass rim where the feather meets the solid part.
  float rim = (1.0 - smoothstep(0.0, 1.6, abs(outside + feather))) * 0.14;
  vec2 uv = vec2(fragTexCoord.x, 1.0 - fragTexCoord.y);
  vec4 base = texture(texture0, uv) * (opacity * top);
  vec4 route = texture(guidance, uv);
  finalColor = (route + base * (1.0 - route.a)) * edge + vec4(rim * opacity * top) * (1.0 - route.a);
}
"""


# ---------------------------------------------------------------- overlay

class MapOverlay:
  """Owns two canvases (front/back), a widget texture and the mask shader."""

  def __init__(self, root: Path | None = None, *, reader: TileReader | None = None, fonts=None,
               clock: Callable[[], float] = time.monotonic):
    self.reader = reader or TileReader(root, clock)
    self.fonts = fonts
    self.clock = clock
    self._lock = threading.Lock()
    self._ready: CanvasGeometry | None = None
    self._pending: CanvasRequest | None = None
    self._canvas: rl.RenderTexture | None = None
    self._canvas_request: CanvasRequest | None = None
    self._widget: rl.RenderTexture | None = None
    self._guidance: rl.RenderTexture | None = None
    self._route_layers: list[tuple[rl.Color, np.ndarray]] = []
    self._widget_size: tuple[int, int] | None = None
    self._shader: rl.Shader | None = None
    self._uniforms: dict[str, int] = {}
    self._uniform_values = (rl.ffi.new("Vector2 *"), rl.ffi.new("float *"), rl.ffi.new("float *"), rl.ffi.new("float *"))
    self._pending_at = -math.inf
    self.has_roads = False
    self._route_key: tuple | None = None
    self._route_world: np.ndarray | None = None
    self._generation_built = -1
    # Smoothed display state.
    self._world: tuple[float, float] | None = None
    self._latitude = 0.0
    self._bearing = 0.0
    self._has_heading = False
    self._m_per_px = ZOOM_SLOW_M_PER_PX
    self._last_prepare: float | None = None
    self.status = "waiting"

  # ---- state

  def _advance(self, data: MapInput, now: float) -> None:
    fix = data.fix
    dt = 0.0 if self._last_prepare is None else min(0.2, max(0.0, now - self._last_prepare))
    self._last_prepare = now
    if fix is None:
      self.status = "waiting" if self._world is None else self.status
      return
    target_world = world_xy(fix.latitude, fix.longitude)
    age = min(DEAD_RECKON_S, max(0.0, now - fix.monotonic))
    if fix.bearing is not None and fix.speed > MIN_HEADING_SPEED:
      units = fix.speed * age / meters_per_tile(fix.latitude)
      heading = math.radians(fix.bearing)
      target_world = (target_world[0] + math.sin(heading) * units, target_world[1] - math.cos(heading) * units)
      delta = (fix.bearing - self._bearing + 540.0) % 360.0 - 180.0
      self._bearing = (self._bearing + delta * (min(1.0, dt * 6.0) if self._has_heading else 1.0)) % 360.0
      self._has_heading = True
    if self._world is None or math.hypot(target_world[0] - self._world[0], target_world[1] - self._world[1]) > 0.5:
      self._world = target_world                               # first fix or a jump: no slow glide across town
    else:
      k = min(1.0, dt * 12.0)
      self._world = (self._world[0] + (target_world[0] - self._world[0]) * k,
                     self._world[1] + (target_world[1] - self._world[1]) * k)
    self._latitude = fix.latitude
    target_zoom = zoom_for_speed(fix.speed)
    self._m_per_px += (target_zoom - self._m_per_px) * min(1.0, dt * 0.8)
    self.status = "live"

  def _route(self, route: tuple[tuple[float, float], ...]) -> None:
    key = (len(route), route[:1], route[-1:])
    if key != self._route_key:
      self._route_key = key
      self._route_world = np.array([world_xy(lat, lon) for lat, lon in route], np.float64) if len(route) >= 2 else None

  # ---- canvas planning

  @staticmethod
  def _reach(width: int, height: int) -> float:
    """Screen pixels from the car to the widget's farthest corner, at any rotation."""
    return math.hypot(width / 2, height * max(CAR_ANCHOR, 1 - CAR_ANCHOR))

  def _canvas_side(self, width: int, height: int) -> int:
    return int(min(MAX_CANVAS, math.ceil(self._reach(width, height) * 2 * 1.6 * SUPERSAMPLE / 64) * 64))

  def _needs_canvas(self, side: int) -> bool:
    request = self._canvas_request
    if request is None or request.side != side:
      return True
    px_per_unit = meters_per_tile(self._latitude) * SUPERSAMPLE / request.m_per_px
    drift = math.hypot(self._world[0] - request.center[0], self._world[1] - request.center[1]) * px_per_unit
    reach = self._reach(*self._widget_size) * SUPERSAMPLE * self._m_per_px / request.m_per_px
    ratio = request.m_per_px / self._m_per_px
    return drift > (side / 2 - reach) * 0.5 or not 0.82 < ratio < 1.22 or self.reader.generation != self._generation_built

  def _request(self, side: int) -> CanvasRequest:
    reach_m = side / SUPERSAMPLE * self._m_per_px * 0.75
    reach = reach_m / meters_per_tile(self._latitude)
    x, y = self._world
    tiles = tuple(TileKey(DATA_ZOOM, tx % (1 << DATA_ZOOM), ty)
                  for ty in range(int(math.floor(y - reach)), int(math.floor(y + reach)) + 1)
                  for tx in range(int(math.floor(x - reach)), int(math.floor(x + reach)) + 1)
                  if 0 <= ty < 1 << DATA_ZOOM)
    done, ahead = split_route(self._route_world, self._world) if self._route_world is not None else (None, None)
    return CanvasRequest(self._world, self._m_per_px, side, ahead, done, tiles)

  def _schedule(self, request: CanvasRequest) -> None:
    self._pending = request
    self._pending_at = self.clock()
    self.reader.want(sorted(request.tiles, key=lambda k: (k.x + 0.5 - request.center[0]) ** 2 + (k.y + 0.5 - request.center[1]) ** 2))
    generation = self.reader.generation
    latitude = self._latitude

    def job():
      geometry = build_canvas(request, self.reader.snapshot(request.tiles), latitude)
      with self._lock:
        if self._pending is request:
          self._ready = geometry
          self._generation_built = generation
    self.reader.submit(job)

  # ---- GPU

  def _ensure_targets(self, width: int, height: int, side: int) -> bool:
    if self._widget_size != (width, height):
      if self._widget is not None:
        rl.unload_render_texture(self._widget)
      if self._guidance is not None:
        rl.unload_render_texture(self._guidance)
      self._widget = rl.load_render_texture(width, height)
      self._guidance = rl.load_render_texture(width, height)
      self._widget_size = None
      if not self._widget.id or not self._guidance.id:
        for target in (self._widget, self._guidance):
          if target.id:
            rl.unload_render_texture(target)
        self._widget = self._guidance = None
        return False
      self._widget_size = (width, height)
      for target in (self._widget, self._guidance):
        rl.set_texture_filter(target.texture, rl.TextureFilter.TEXTURE_FILTER_BILINEAR)
    if self._shader is None:
      self._shader = rl.load_shader_from_memory(MASK_VERTEX, MASK_FRAGMENT)
      if not self._shader.id:
        raise RuntimeError("Map overlay shader unavailable")
      self._uniforms = {name: rl.get_shader_location(self._shader, name) for name in ("size", "radius", "feather", "opacity", "guidance")}
    return True

  def _draw_canvas(self, geometry: CanvasGeometry) -> None:
    side = geometry.request.side
    if self._canvas is None or self._canvas.texture.width != side:
      if self._canvas is not None:
        rl.unload_render_texture(self._canvas)
      self._canvas = rl.load_render_texture(side, side)
      if not self._canvas.id:
        self._canvas = None
        return
      rl.set_texture_filter(self._canvas.texture, rl.TextureFilter.TEXTURE_FILTER_BILINEAR)
    rl.begin_texture_mode(self._canvas)
    try:
      rl.clear_background(rl.BLANK)
      rl.begin_blend_mode(rl.BlendMode.BLEND_ALPHA_PREMULTIPLY)
      for color, strip in geometry.layers:
        strip = np.ascontiguousarray(strip, np.float32)
        rl.draw_triangle_strip(rl.ffi.from_buffer("Vector2 *", strip), len(strip), color)
      rl.end_blend_mode()
    finally:
      rl.end_texture_mode()
    self._route_layers = geometry.guidance
    self._canvas_request = geometry.request
    self.has_roads = geometry.tiles_missing < len(geometry.request.tiles)

  def _puck(self, x: float, y: float) -> None:
    rl.draw_circle_v(rl.Vector2(x, y), 26, premultiplied((150, 110, 255, 70)))
    points = [(0, -19), (-14, 15), (0, 7), (14, 15)]
    outline = [rl.Vector2(x + px * 1.25, y + py * 1.25) for px, py in points]
    body = [rl.Vector2(x + px, y + py) for px, py in points]
    for shape, color in ((outline, premultiplied((96, 70, 210))), (body, premultiplied((255, 255, 255)))):
      rl.draw_triangle(shape[0], shape[1], shape[2], color)
      rl.draw_triangle(shape[0], shape[2], shape[3], color)

  def _compass(self, width: int, height: int) -> None:
    """A small needle in the top right that always points north."""
    inset = max(22.0, min(width, height) * 0.09)
    cx, cy = width - inset, inset
    rl.draw_circle_v(rl.Vector2(cx, cy), 13, premultiplied((8, 12, 20, 170)))
    angle = math.radians(-self._bearing)
    def point(r, a):
      return rl.Vector2(cx + r * math.sin(angle + a), cy - r * math.cos(angle + a))
    rl.draw_triangle(point(10, 0), point(5, -2.3), point(5, 2.3), premultiplied((255, 110, 96)))
    rl.draw_triangle(point(10, math.pi), point(5, math.pi + 2.3), point(5, math.pi - 2.3), premultiplied((210, 214, 224, 200)))

  def _compose_layer(self, width: int, height: int, guidance: bool) -> None:
    rl.begin_texture_mode(self._guidance if guidance else self._widget)
    try:
      rl.clear_background(rl.BLANK)
      rl.begin_blend_mode(rl.BlendMode.BLEND_ALPHA_PREMULTIPLY)
      if not guidance:
        rl.draw_rectangle(0, 0, width, height, premultiplied(GLASS))
      request = self._canvas_request
      if self._canvas is not None and request is not None and self._world is not None:
        px_per_unit = meters_per_tile(self._latitude) / request.m_per_px
        zoom = request.m_per_px / self._m_per_px / SUPERSAMPLE
        side = request.side
        # The car's spot on the canvas, in canvas pixels.
        car_x = (self._world[0] - request.center[0]) * px_per_unit * SUPERSAMPLE + side / 2
        car_y = (self._world[1] - request.center[1]) * px_per_unit * SUPERSAMPLE + side / 2
        anchor = rl.Vector2(width / 2, height * CAR_ANCHOR)
        if guidance:
          rl.rl_push_matrix()
          try:
            rl.rl_translatef(anchor.x, anchor.y, 0)
            rl.rl_rotatef(-self._bearing, 0, 0, 1)
            rl.rl_scalef(zoom, zoom, 1)
            rl.rl_translatef(-car_x, -car_y, 0)
            for color, strip in self._route_layers:
              strip = np.ascontiguousarray(strip, np.float32)
              rl.draw_triangle_strip(rl.ffi.from_buffer("Vector2 *", strip), len(strip), color)
          finally:
            rl.rl_pop_matrix()
          self._puck(anchor.x, anchor.y)
          self._compass(width, height)
        else:
          rl.draw_texture_pro(self._canvas.texture, rl.Rectangle(0, 0, side, -side),
                              rl.Rectangle(anchor.x, anchor.y, side * zoom, side * zoom),
                              rl.Vector2(car_x * zoom, car_y * zoom), -self._bearing, rl.WHITE)
      rl.end_blend_mode()
    finally:
      rl.end_texture_mode()

  def _compose(self, width: int, height: int) -> None:
    self._compose_layer(width, height, False)
    self._compose_layer(width, height, True)

  # ---- public

  def prepare(self, data: MapInput, width: int, height: int) -> None:
    """Outside any render target: advance, rebuild the canvas if needed and compose the widget."""
    width, height = max(16, int(width)), max(16, int(height))
    if not self._ensure_targets(width, height, 0):
      return
    now = self.clock()
    self._advance(data, now)
    self._route(data.route)
    if self._world is not None:
      side = self._canvas_side(width, height)
      with self._lock:
        ready, self._ready = self._ready, None
      if ready is not None:
        self._draw_canvas(ready)
      in_flight = self._pending is not None and self._canvas_request is not self._pending and now - self._pending_at < 2.0
      if not in_flight and self._needs_canvas(side):
        self._schedule(self._request(side))
    self._compose(width, height)

  def draw(self, rect: rl.Rectangle, opacity: float) -> None:
    """Inside the frame: the composed widget, rounded, feathered and faded."""
    if self._widget is None or self._shader is None:
      return
    width, height = self._widget_size
    size, radius, feather, alpha = self._uniform_values
    size.x, size.y = width, height
    radius[0] = min(width, height) * 0.09
    feather[0] = max(10.0, min(width, height) * 0.07)
    alpha[0] = max(0.0, min(1.0, opacity))
    rl.begin_blend_mode(rl.BlendMode.BLEND_ALPHA_PREMULTIPLY)
    rl.begin_shader_mode(self._shader)
    try:
      # Typed pointers: pyray drops float arrays and by-value structs passed as uniform data.
      vec2, scalar = rl.ShaderUniformDataType.SHADER_UNIFORM_VEC2, rl.ShaderUniformDataType.SHADER_UNIFORM_FLOAT
      for name, value, kind in (("size", size, vec2), ("radius", radius, scalar), ("feather", feather, scalar), ("opacity", alpha, scalar)):
        rl.set_shader_value(self._shader, self._uniforms[name], value, kind)
      rl.set_shader_value_texture(self._shader, self._uniforms["guidance"], self._guidance.texture)
      rl.draw_texture_pro(self._widget.texture, rl.Rectangle(0, 0, width, height), rect, rl.Vector2(0, 0), 0, rl.WHITE)
    finally:
      rl.end_shader_mode()
      rl.end_blend_mode()
    text = "Waiting for GPS" if self.status == "waiting" else "" if self.has_roads or self._canvas_request is None else "No map data here yet"
    if text and self.fonts is not None:
      from openpilot.starpilot.ui.presentation import FontRole
      measured = self.fonts.measure(text, FontRole.MEDIUM, 26)
      self.fonts.draw(text, FontRole.MEDIUM, 26, rect.x + (rect.width - measured.width) / 2,
                      rect.y + rect.height * CAR_ANCHOR + 40, rl.Color(225, 228, 238, round(200 * opacity)))

  def close(self) -> None:
    self.reader.close()
    if rl.is_window_ready():
      for target in (self._canvas, self._widget, self._guidance):
        if target is not None:
          rl.unload_render_texture(target)
      if self._shader is not None and self._shader.id:
        rl.unload_shader(self._shader)
    self._canvas = self._widget = self._guidance = None
    self._route_layers = []
    self._shader = None


# ---------------------------------------------------------------- live input

class MapFeed:
  """The same GPS choice as navigation (either receiver, then the car's own), and the active route."""

  def __init__(self, sm=None):
    from openpilot.starpilot.gps.source import GPS_SOURCES
    if sm is None:
      from openpilot.cereal import messaging
      sm = messaging.SubMaster(list(GPS_SOURCES))
    self.sm = sm
    self._fix: MapFix | None = None

  def read(self, navigation_sm=None) -> MapInput:
    from openpilot.starpilot.gps.source import bearing, select_location
    self.sm.update(0)
    now = time.monotonic()
    selected = select_location(self.sm, time.monotonic_ns())
    if selected is not None:
      stamp, gps = selected
      speed = float(getattr(gps, "speed", float("nan")))
      if math.isfinite(speed) and -85 < gps.latitude < 85:
        # The fix's own timestamp, so dead reckoning starts from when it was measured.
        self._fix = MapFix(gps.latitude, gps.longitude, bearing(gps), max(0.0, speed), stamp / 1e9)
    if self._fix is not None and now - self._fix.monotonic > 5.0:
      self._fix = None
    route: tuple[tuple[float, float], ...] = ()
    if navigation_sm is not None:
      try:
        from openpilot.starpilot.navigation.wire import navigation_state
        nav = navigation_state(navigation_sm["starpilotNavigation"]) if navigation_sm.valid["starpilotNavigation"] else None
        if nav is not None and nav.status in ("guiding", "arrived"):
          route = tuple((point.latitude, point.longitude) for point in nav.route)
      except Exception:
        route = ()
    return MapInput(self._fix, route)


# ---------------------------------------------------------------- parked preview

SAMPLE_TILE = TileKey(DATA_ZOOM, 2950, 6427)
SAMPLE_CAR = (1450.0, 2930.0)          # tile units inside SAMPLE_TILE, south of a left turn
SAMPLE_BEARING = 0.0


def _sample_roads() -> dict[int, list[np.ndarray]]:
  """A believable neighborhood for the parked layout preview; drawn from no real map."""
  t = np.linspace(-4500, 8600, 90)
  roads: dict[int, list[np.ndarray]] = {
    MOTORWAY: [np.stack((2700 + 520 * np.sin(t / 1900), t), axis=1)],
    MAJOR: [np.array([[-4500, 2300], [1200, 2620], [8600, 2050]]), np.array([[1450, 8600], [1450, 2620], [1700, -4500]])],
    STREET: [], MINOR: [], LINK: [np.array([[2400, 1500], [2650, 1900], [3050, 2200]])],
  }
  angle = math.radians(8)
  rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
  for i in range(-12, 22):
    offset = i * 420.0
    roads[STREET].append(np.array([[offset, -4500], [offset + 60, 8600]]) @ rotation.T)
    roads[STREET].append(np.array([[-4500, offset], [8600, offset - 90]]) @ rotation.T)
    roads[MINOR].append(np.array([[offset + 210, offset - 300], [offset + 330, offset - 120], [offset + 210, offset + 60]]))
  return roads


class SampleTileReader:
  """TileReader's interface over one synthetic tile; jobs run inline."""

  def __init__(self):
    raw = encode_road_tile(_sample_roads())
    self._tile = decode_road_tile(SAMPLE_TILE, raw)
    self.generation = 1

  def want(self, keys) -> None:
    pass

  def submit(self, job) -> None:
    job()

  def snapshot(self, keys) -> dict[TileKey, RoadTile]:
    return {key: self._tile for key in keys if key == SAMPLE_TILE}

  def close(self) -> None:
    pass


def sample_input() -> MapInput:
  from openpilot.starpilot.navigation.road_tiles import lat_lon
  def world(x, y):
    return lat_lon(SAMPLE_TILE.x + x / EXTENT, SAMPLE_TILE.y + y / EXTENT)
  latitude, longitude = world(*SAMPLE_CAR)
  route = tuple(world(x, y) for x, y in ((1450, 4200), (1450, 2620), (1200, 2620), (-1800, 2460)))
  return MapInput(MapFix(latitude, longitude, SAMPLE_BEARING, 8.0, time.monotonic()), route)
