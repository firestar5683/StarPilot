"""Uniform projection geometry inside receiver-advertised margins."""
from dataclasses import dataclass


# Landscape 3:2 is a composition fallback only. It is not an advertised video
# mode and cannot replace a missing/invalid negotiated FrameRequest.
FALLBACK_VIEWPORT = (1860, 1240)


@dataclass(frozen=True)
class ProjectionGeometry:
  width: int
  height: int
  logical_width: int
  logical_height: int
  scale: float


def projection_geometry(width: int, height: int, margin_w: int = 0, margin_h: int = 0) -> ProjectionGeometry:
  if not 0 <= margin_w < width or not 0 <= margin_h < height:
    raise ValueError("No visible car display area")
  visible_w, visible_h = width - margin_w, height - margin_h
  # Expand the scene, never crop the original 1860x1080 road/HUD canvas.
  scale = min(visible_w / 1860, visible_h / 1080)
  logical_w, logical_h = round(visible_w / scale), round(visible_h / scale)
  # Bound the intermediate GPU texture to 4096x2160 (about 34 MiB RGBA).
  # Extreme valid margins still retain the protocol frame; contain the requested
  # 3:2 fallback scene rather than allocate an unbounded logical texture.
  if logical_w > 4096 or logical_h > 2160:
    logical_w, logical_h = FALLBACK_VIEWPORT
  scale = min(visible_w / logical_w, visible_h / logical_h)
  return ProjectionGeometry(visible_w, visible_h, logical_w, logical_h, scale)
