"""Road-line map tiles for the Android Auto map overlay.

The overlay draws roads as lines over the camera, so it needs road geometry,
not a picture of a map. Mapbox Vector Tiles carry that geometry; this module
keeps only the ``road`` layer and stores it in a small compact file per tile.
One stored zoom serves every display zoom (vectors scale without blurring),
and there is no light/dark pair: colors are chosen when drawing.

Pure functions only: no network, GPU or process state. ``navtilesd`` owns the
downloads and the renderer reads the files this module writes.
"""

from __future__ import annotations

import math
import struct
import zlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

DATA_ZOOM = 14
EXTENT = 4096
MVT_URL = "https://api.mapbox.com/v4/mapbox.mapbox-streets-v8/{z}/{x}/{y}.vector.pbf"
MAX_DOWNLOAD_BYTES = 4 * 1024 * 1024
MAX_STORED_BYTES = 2 * 1024 * 1024

# Draw order is the reverse of importance, so major roads end up on top.
MOTORWAY, MAJOR, STREET, LINK, MINOR = range(5)
CLASS_NAMES = ("motorway", "major", "street", "link", "minor")
_CLASS_OF = {
  "motorway": MOTORWAY, "trunk": MOTORWAY,
  "primary": MAJOR, "secondary": MAJOR,
  "tertiary": STREET, "street": STREET, "street_limited": STREET,
  "motorway_link": LINK, "trunk_link": LINK, "primary_link": LINK, "secondary_link": LINK, "tertiary_link": LINK,
  "service": MINOR, "track": MINOR,
}

MAGIC = b"SPRT"
VERSION = 1
_HEADER = struct.Struct("<4sBB")
_CLASS_HEADER = struct.Struct("<BII")
_COORD_LIMIT = 32767


class TileFormatError(ValueError):
  pass


@dataclass(frozen=True, slots=True, order=True)
class TileKey:
  z: int
  x: int
  y: int

  def path(self) -> str:
    return f"{self.z}/{self.x}/{self.y}.rt"


# ---------------------------------------------------------------- web mercator

def world_xy(latitude: float, longitude: float, zoom: int = DATA_ZOOM) -> tuple[float, float]:
  """Web Mercator position in tile units at ``zoom`` (tile x, tile y as floats)."""
  latitude = max(-85.05112878, min(85.05112878, latitude))
  n = float(1 << zoom)
  x = (longitude + 180.0) / 360.0 * n
  sin_lat = math.sin(math.radians(latitude))
  y = (0.5 - math.log((1.0 + sin_lat) / (1.0 - sin_lat)) / (4.0 * math.pi)) * n
  return x, y


def lat_lon(x: float, y: float, zoom: int = DATA_ZOOM) -> tuple[float, float]:
  n = float(1 << zoom)
  longitude = x / n * 360.0 - 180.0
  latitude = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n))))
  return latitude, longitude


def meters_per_tile(latitude: float, zoom: int = DATA_ZOOM) -> float:
  return 40075016.686 * math.cos(math.radians(latitude)) / (1 << zoom)


def tiles_in_radius(latitude: float, longitude: float, radius_m: float, zoom: int = DATA_ZOOM) -> list[TileKey]:
  """Tiles whose square touches a circle, nearest first."""
  cx, cy = world_xy(latitude, longitude, zoom)
  reach = radius_m / max(1.0, meters_per_tile(latitude, zoom))
  limit = (1 << zoom) - 1
  keys = []
  for ty in range(max(0, int(cy - reach)), min(limit, int(cy + reach)) + 1):
    for tx in range(int(math.floor(cx - reach)), int(math.floor(cx + reach)) + 1):
      nx, ny = min(max(cx, tx), tx + 1), min(max(cy, ty), ty + 1)
      if (nx - cx) ** 2 + (ny - cy) ** 2 <= reach * reach:
        keys.append((math.hypot(tx + 0.5 - cx, ty + 0.5 - cy), TileKey(zoom, tx % (1 << zoom), ty)))
  return [key for _, key in sorted(keys)]


def corridor_tiles(points: Sequence[tuple[float, float]], radius_tiles: int = 1, zoom: int = DATA_ZOOM,
                   limit: int = 4000) -> list[TileKey]:
  """Tiles along a (latitude, longitude) polyline, in travel order."""
  seen: set[TileKey] = set()
  ordered: list[TileKey] = []
  previous = None
  wrap = 1 << zoom
  for latitude, longitude in points:
    point = world_xy(latitude, longitude, zoom)
    samples = [point]
    if previous is not None:
      steps = int(max(abs(point[0] - previous[0]), abs(point[1] - previous[1])) * 2)
      samples = [(previous[0] + (point[0] - previous[0]) * i / (steps + 1),
                  previous[1] + (point[1] - previous[1]) * i / (steps + 1)) for i in range(1, steps + 2)]
    previous = point
    for sx, sy in samples:
      for dy in range(-radius_tiles, radius_tiles + 1):
        for dx in range(-radius_tiles, radius_tiles + 1):
          ty = int(sy) + dy
          if 0 <= ty < wrap:
            key = TileKey(zoom, (int(sx) + dx) % wrap, ty)
            if key not in seen:
              seen.add(key)
              ordered.append(key)
              if len(ordered) >= limit:
                return ordered
  return ordered


# ---------------------------------------------------------------- protobuf / MVT

def _varint(data: bytes, pos: int) -> tuple[int, int]:
  result = shift = 0
  while True:
    if pos >= len(data):
      raise TileFormatError("truncated varint")
    byte = data[pos]
    pos += 1
    result |= (byte & 0x7F) << shift
    if byte < 0x80:
      return result, pos
    shift += 7
    if shift > 63:
      raise TileFormatError("varint too long")


def _fields(data: bytes):
  """(field number, wire type, value) for each field; length-delimited values are memoryviews."""
  pos, end = 0, len(data)
  view = memoryview(data)
  while pos < end:
    tag, pos = _varint(data, pos)
    field, wire = tag >> 3, tag & 7
    if wire == 0:
      value, pos = _varint(data, pos)
    elif wire == 2:
      length, pos = _varint(data, pos)
      if pos + length > end:
        raise TileFormatError("truncated field")
      value, pos = view[pos:pos + length], pos + length
    elif wire == 1:
      value, pos = view[pos:pos + 8], pos + 8
    elif wire == 5:
      value, pos = view[pos:pos + 4], pos + 4
    else:
      raise TileFormatError("unsupported wire type")
    if pos > end:
      raise TileFormatError("truncated field")
    yield field, wire, value


def _packed(data) -> list[int]:
  data = bytes(data)
  values, pos = [], 0
  while pos < len(data):
    value, pos = _varint(data, pos)
    values.append(value)
  return values


def _lines(geometry: list[int]) -> list[list[tuple[int, int]]]:
  """LineString parts from MVT geometry commands (zigzag deltas)."""
  lines: list[list[tuple[int, int]]] = []
  current: list[tuple[int, int]] = []
  x = y = i = 0
  while i < len(geometry):
    command, count = geometry[i] & 7, geometry[i] >> 3
    i += 1
    if command == 7:
      continue
    if command not in (1, 2) or i + 2 * count > len(geometry):
      raise TileFormatError("bad geometry command")
    for _ in range(count):
      dx, dy = geometry[i], geometry[i + 1]
      i += 2
      x += (dx >> 1) ^ -(dx & 1)
      y += (dy >> 1) ^ -(dy & 1)
      if command == 1:
        if len(current) >= 2:
          lines.append(current)
        current = [(x, y)]
      else:
        current.append((x, y))
  if len(current) >= 2:
    lines.append(current)
  return lines


def decode_mvt_roads(data: bytes) -> dict[int, list[np.ndarray]]:
  """Road lines by class from a Mapbox Streets vector tile, in 0..EXTENT tile units."""
  if data[:2] == b"\x1f\x8b":
    inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
      data = inflater.decompress(data, 4 * MAX_DOWNLOAD_BYTES)
    except zlib.error as error:
      raise TileFormatError("corrupt gzip tile") from error
    if inflater.unconsumed_tail:
      raise TileFormatError("vector tile too large")
  roads: dict[int, list[np.ndarray]] = {}
  for field, wire, layer in _fields(data):
    if field != 3 or wire != 2:
      continue
    layer = bytes(layer)
    name, keys, values, features, extent = "", [], [], [], EXTENT
    for lf, lw, value in _fields(layer):
      if lf == 1 and lw == 2:
        name = bytes(value).decode("utf-8", "replace")
        if name != "road":
          break
      elif lf == 2 and lw == 2:
        features.append(value)
      elif lf == 3 and lw == 2:
        keys.append(bytes(value).decode("utf-8", "replace"))
      elif lf == 4 and lw == 2:
        text = None
        for vf, vw, item in _fields(bytes(value)):
          if vf == 1 and vw == 2:
            text = bytes(item).decode("utf-8", "replace")
        values.append(text)
      elif lf == 5 and lw == 0:
        extent = value
    if name != "road" or extent <= 0:
      continue
    scale = EXTENT / extent
    class_key = keys.index("class") if "class" in keys else -1
    for feature in features:
      tags, kind, geometry = [], 0, []
      for ff, fw, value in _fields(bytes(feature)):
        if ff == 2 and fw == 2:
          tags = _packed(value)
        elif ff == 3 and fw == 0:
          kind = value
        elif ff == 4 and fw == 2:
          geometry = _packed(value)
      if kind != 2 or class_key < 0:
        continue
      road_class = None
      for k in range(0, len(tags) - 1, 2):
        if tags[k] == class_key and tags[k + 1] < len(values):
          road_class = _CLASS_OF.get(values[tags[k + 1]] or "")
          break
      if road_class is None:
        continue
      for line in _lines(geometry):
        points = np.asarray(line, dtype=np.float64)
        if scale != 1.0:
          points *= scale
        roads.setdefault(road_class, []).append(points)
  return roads


# ---------------------------------------------------------------- compact storage

def encode_road_tile(roads: Mapping[int, Iterable[np.ndarray]]) -> bytes:
  """Delta-coded int16 polylines per class, zlib-compressed."""
  body = bytearray()
  classes = 0
  for road_class in sorted(roads):
    lines = [np.clip(np.rint(line), -_COORD_LIMIT, _COORD_LIMIT).astype(np.int32) for line in roads[road_class]]
    lines = [line for line in lines if len(line) >= 2]
    if not lines:
      continue
    lengths = np.array([min(len(line), 65535) for line in lines], dtype=np.uint16)
    coords = np.concatenate([line[:65535] for line in lines])
    deltas = coords.copy()
    deltas[1:] -= coords[:-1]
    body += _CLASS_HEADER.pack(road_class, len(lines), len(coords))
    body += lengths.tobytes()
    body += np.clip(deltas, -65535, 65535).astype(np.int32).astype("<i4").tobytes()
    classes += 1
  return _HEADER.pack(MAGIC, VERSION, classes) + zlib.compress(bytes(body), 6)


@dataclass(frozen=True)
class RoadTile:
  key: TileKey
  # class -> (points float32 (N, 2) in tile units, line start offsets int32 (L + 1,))
  lines: dict[int, tuple[np.ndarray, np.ndarray]]

  @property
  def empty(self) -> bool:
    return not self.lines


def decode_road_tile(key: TileKey, raw: bytes) -> RoadTile:
  if len(raw) < _HEADER.size or len(raw) > MAX_STORED_BYTES:
    raise TileFormatError("bad road tile size")
  magic, version, classes = _HEADER.unpack_from(raw)
  if magic != MAGIC or version != VERSION or classes > len(CLASS_NAMES):
    raise TileFormatError("not a road tile")
  inflater = zlib.decompressobj()
  try:
    body = inflater.decompress(raw[_HEADER.size:], 32 * MAX_STORED_BYTES)
  except zlib.error as error:
    raise TileFormatError("corrupt road tile") from error
  if not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
    raise TileFormatError("truncated, oversized or padded road tile")
  pos, lines = 0, {}
  for _ in range(classes):
    if pos + _CLASS_HEADER.size > len(body):
      raise TileFormatError("truncated road tile")
    road_class, count, total = _CLASS_HEADER.unpack_from(body, pos)
    pos += _CLASS_HEADER.size
    need = count * 2 + total * 8
    if road_class >= len(CLASS_NAMES) or road_class in lines or pos + need > len(body):
      raise TileFormatError("bad road tile class")
    lengths = np.frombuffer(body, dtype="<u2", count=count, offset=pos).astype(np.int32)
    pos += count * 2
    deltas = np.frombuffer(body, dtype="<i4", count=total * 2, offset=pos).reshape(total, 2)
    pos += total * 8
    if int(lengths.sum()) != total or (count and int(lengths.min()) < 2):
      raise TileFormatError("bad road tile lengths")
    offsets = np.zeros(count + 1, dtype=np.int32)
    np.cumsum(lengths, out=offsets[1:])
    lines[road_class] = (np.cumsum(deltas, axis=0).astype(np.float32), offsets)
  if pos != len(body):
    raise TileFormatError("trailing road tile data")
  return RoadTile(key, lines)
