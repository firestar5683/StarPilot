"""Pure camera-side V-ASM geometry and warning policy; no model or camera access."""

from collections.abc import Sequence
from dataclasses import dataclass
import json
import math

import numpy as np


MODEL_INPUT_SIZE = 352
STATE_TIMEOUT_SECONDS = 3.0
MAX_ANNOTATION_BYTES = 8192
MAX_POINTS = 32


def _number(value: object) -> float:
  if (type(value) is not int and type(value) is not float) or not math.isfinite(value):
    raise ValueError("Annotation coordinates must be finite numbers")
  return float(value)


def _unique(pairs: list[tuple[str, object]]) -> dict:
  result: dict = {}
  for key, value in pairs:
    if key in result:
      raise ValueError("Duplicate annotation field")
    result[key] = value
  return result


def _reject_constant(value: str):
  raise ValueError(f"Nonfinite annotation value: {value}")


def _orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
  return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(a: tuple[float, float], b: tuple[float, float],
                        c: tuple[float, float], d: tuple[float, float]) -> bool:
  ab_c, ab_d = _orientation(a, b, c), _orientation(a, b, d)
  cd_a, cd_b = _orientation(c, d, a), _orientation(c, d, b)
  epsilon = 1e-12
  def on_segment(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> bool:
    return min(p[0], r[0]) - epsilon <= q[0] <= max(p[0], r[0]) + epsilon and \
           min(p[1], r[1]) - epsilon <= q[1] <= max(p[1], r[1]) + epsilon
  if (abs(ab_c) <= epsilon and on_segment(a, c, b)) or (abs(ab_d) <= epsilon and on_segment(a, d, b)) or \
     (abs(cd_a) <= epsilon and on_segment(c, a, d)) or (abs(cd_b) <= epsilon and on_segment(c, b, d)):
    return True
  return (ab_c > epsilon) != (ab_d > epsilon) and (cd_a > epsilon) != (cd_b > epsilon)


def _polygon(points: object, width: int, height: int) -> tuple[tuple[float, float], ...]:
  if type(points) is not list or len(points) < 3 or len(points) > MAX_POINTS:
    raise ValueError("Each configured side needs 3–32 polygon points")
  pixels: list[tuple[float, float]] = []
  for point in points:
    if type(point) is not list or len(point) != 2:
      raise ValueError("Each polygon point needs x and y")
    x, y = _number(point[0]), _number(point[1])
    if not 0 <= x <= width or not 0 <= y <= height:
      raise ValueError("Polygon point is outside its annotated frame")
    pixels.append((x, y))
  normalized = tuple((x / width, y / height) for x, y in pixels)
  if len(set(normalized)) != len(normalized):
    raise ValueError("Polygon repeats a vertex")
  area_twice = sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(normalized, normalized[1:] + normalized[:1], strict=True))
  if abs(area_twice) <= 1e-9:
    raise ValueError("Polygon has no area")
  # Crossed annotations cannot define an unambiguous source mask. Adjacent
  # edges share a vertex and are intentionally omitted from this check.
  for i in range(len(normalized)):
    a, b = normalized[i], normalized[(i + 1) % len(normalized)]
    for j in range(i + 2, len(normalized)):
      if i == 0 and j == len(normalized) - 1:
        continue
      c, d = normalized[j], normalized[(j + 1) % len(normalized)]
      if _segments_intersect(a, b, c, d):
        raise ValueError("Polygon crosses or touches itself")
  return normalized


@dataclass(frozen=True)
class Annotation:
  width: int
  height: int
  camera_left: tuple[tuple[float, float], ...] | None
  camera_right: tuple[tuple[float, float], ...] | None
  camera_left_source: tuple[tuple[float, float], ...] | None = None
  camera_right_source: tuple[tuple[float, float], ...] | None = None

  @property
  def configured_sides(self) -> tuple[str, ...]:
    return tuple(side for side in ("left", "right") if getattr(self, f"camera_{side}") is not None)


def decode_annotation(raw: bytes | str) -> Annotation:
  if type(raw) not in (bytes, str) or len(raw) > MAX_ANNOTATION_BYTES:
    raise ValueError("Annotation is unavailable or oversized")
  try:
    value = json.loads(raw, object_pairs_hook=_unique, parse_constant=_reject_constant)
  except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
    raise ValueError("Invalid annotation JSON") from error
  if type(value) is not dict or set(value) != {"version", "width", "height", "poly_left", "poly_right"} or \
     type(value["version"]) is not int or value["version"] != 1:
    raise ValueError("Unexpected annotation fields")
  width, height = value["width"], value["height"]
  if type(width) is not int or type(height) is not int or not (32 <= width <= 8192 and 32 <= height <= 8192) or \
     width % 2 or height % 2:
    raise ValueError("Annotation dimensions must be bounded even camera dimensions")
  polygons = []
  source_polygons = []
  for side in ("left", "right"):
    points = value[f"poly_{side}"]
    polygons.append(None if points == [] else _polygon(points, width, height))
    source_polygons.append(None if points == [] else tuple((float(point[0]), float(point[1])) for point in points))
  if polygons == [None, None]:
    raise ValueError("At least one camera side must be annotated")
  return Annotation(width, height, *polygons, *source_polygons)


def encode_annotation(annotation: Annotation) -> bytes:
  if not annotation.configured_sides:
    raise ValueError("No camera side configured")
  value = {"version": 1, "width": annotation.width, "height": annotation.height}
  for side in ("left", "right"):
    polygon = getattr(annotation, f"camera_{side}_source")
    value[f"poly_{side}"] = [] if polygon is None else [list(point) for point in polygon]
  raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
  # The same decoder validates dimensions, self-intersection, and point bounds.
  decode_annotation(raw)
  return raw


@dataclass(frozen=True)
class Crop:
  x: int
  y: int
  width: int
  height: int
  model_width: int
  model_height: int
  pad_left: int
  pad_top: int


def polygon_pixels(annotation: Annotation, side: str, width: int, height: int) -> tuple[tuple[int, int], ...]:
  source = getattr(annotation, f"camera_{side}_source")
  if source is None:
    return ()
  # Scale raw float32 points before truncation; normalized-coordinate round trips
  # can shift the NV12 crop.
  points = np.array(source, dtype=np.float32)
  points[:, 0] *= width / float(annotation.width)
  points[:, 1] *= height / float(annotation.height)
  return tuple((int(x), int(y)) for x, y in points.astype(np.int32))


def crop_for_side(annotation: Annotation, side: str, frame_width: int, frame_height: int) -> Crop | None:
  if side not in ("left", "right") or type(frame_width) is not int or type(frame_height) is not int or \
     frame_width < 4 or frame_height < 4 or frame_width > 8192 or frame_height > 8192 or \
     frame_width % 2 or frame_height % 2:
    raise ValueError("Unsupported camera side or NV12 frame")
  polygon = getattr(annotation, f"camera_{side}")
  if polygon is None:
    return None
  # Bound integer-truncated points, then align the origin and extent to even NV12 pixels.
  pixels = polygon_pixels(annotation, side, frame_width, frame_height)
  min_x, min_y = min(x for x, _ in pixels), min(y for _, y in pixels)
  max_x, max_y = max(x for x, _ in pixels), max(y for _, y in pixels)
  raw_width, raw_height = max_x - min_x + 1, max_y - min_y + 1
  x = max(0, min((min_x // 2) * 2, frame_width - 2))
  y = max(0, min((min_y // 2) * 2, frame_height - 2))
  width = (max(2, min(((raw_width + 1) // 2) * 2, frame_width - x)) // 2) * 2
  height = (max(2, min(((raw_height + 1) // 2) * 2, frame_height - y)) // 2) * 2
  scale = MODEL_INPUT_SIZE / max(width, height)
  model_width, model_height = round(width * scale), round(height * scale)
  if model_width < 1 or model_height < 1:
    return None
  return Crop(x, y, width, height, model_width, model_height,
              (MODEL_INPUT_SIZE - model_width) // 2, (MODEL_INPUT_SIZE - model_height) // 2)


def _valid_scores(scores: object) -> bool:
  return ((type(scores) is list or type(scores) is tuple) and len(scores) in (2, 3) and
          all((type(score) is int or type(score) is float) and math.isfinite(score) and
              0 <= score <= 1 for score in scores))


def class_one_confidence(scores: Sequence[float] | None) -> float:
  # Class 1 is threat in both model variants; malformed output must not substitute class 0.
  if scores is None or not _valid_scores(scores):
    return 0.0
  return float(scores[1])


@dataclass(frozen=True)
class WarningState:
  display_left: bool
  display_right: bool
  display_left_confidence: float
  display_right_confidence: float


class WarningPolicy:
  def __init__(self, *, threshold: float = 0.94, smooth_seconds: float = 0.2):
    if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0.8 <= threshold <= 1.0 or \
       type(smooth_seconds) not in (int, float) or not math.isfinite(smooth_seconds) or not 0.01 <= smooth_seconds <= 0.5:
      raise ValueError("Invalid V-ASM warning settings")
    self.threshold = float(threshold)
    self.smooth_seconds = float(smooth_seconds)
    self.reset()

  def reset(self) -> None:
    self.score = {"left": 0.0, "right": 0.0}
    self.active = {"left": False, "right": False}
    self.confidence = {"left": 0.0, "right": 0.0}
    self.last_update: dict[str, float | None] = {"left": None, "right": None}
    self.last_now: float | None = None

  def update(self, side: str, scores: Sequence[float] | None, *, now: float, dt: float) -> WarningState:
    if side not in ("left", "right"):
      raise ValueError("Unknown camera side")
    previous = self.last_update[side]
    if type(now) not in (int, float) or type(dt) not in (int, float) or not math.isfinite(now) or \
       not math.isfinite(dt) or now < 0 or dt <= 0 or (previous is not None and now <= previous) or \
       (self.last_now is not None and now < self.last_now) or not _valid_scores(scores):
      self.reset()
      return self.state(now)
    self.last_now = now
    if previous is not None and now - previous > STATE_TIMEOUT_SECONDS:
      self.score[side] = 0.0
      self.active[side] = False
    raw = class_one_confidence(scores)
    alpha = min(1.0, dt / max(self.smooth_seconds, 0.001))
    self.score[side] = (1.0 - alpha) * self.score[side] + alpha * raw
    self.confidence[side] = raw
    if not self.active[side]:
      self.active[side] = self.score[side] >= self.threshold
    elif self.score[side] < max(0.0, self.threshold - 0.15):
      self.active[side] = False
    self.last_update[side] = now
    return self.state(now)

  def state(self, now: float) -> WarningState:
    if type(now) not in (int, float) or not math.isfinite(now) or now < 0 or \
       (self.last_now is not None and now < self.last_now):
      self.reset()
      return WarningState(False, False, 0.0, 0.0)
    self.last_now = now
    def fresh(side: str) -> bool:
      stamp = self.last_update[side]
      return stamp is not None and 0 <= now - stamp <= STATE_TIMEOUT_SECONDS
    # Camera-left maps to display-right and vice versa.
    return WarningState(self.active["right"] and fresh("right"), self.active["left"] and fresh("left"),
                        self.confidence["right"] if fresh("right") else 0.0,
                        self.confidence["left"] if fresh("left") else 0.0)
