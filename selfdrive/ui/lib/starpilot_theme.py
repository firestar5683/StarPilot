from __future__ import annotations

import json
from pathlib import Path

import pyray as rl

from openpilot.common.basedir import BASEDIR
from openpilot.system.ui.lib.application import gui_app

ACTIVE_THEME_COLORS_PATH = Path(BASEDIR) / "starpilot/assets/active_theme/colors/colors.json"
STOCK_THEME_COLORS_PATH = Path(BASEDIR) / "starpilot/assets/stock_theme/colors/colors.json"

_FALLBACK_THEME_COLORS = {
  "LaneLines": (255, 255, 255, 178),
  "LeadMarker": (201, 34, 49, 255),
  "Path": (48, 255, 156, 255),
  "PathEdge": (38, 209, 125, 255),
  "Sidebar1": (255, 255, 255, 178),
  "Sidebar2": (255, 255, 255, 255),
  "Sidebar3": (255, 255, 255, 255),
}

_THEME_COLOR_CACHE: dict[str, object] = {
  "frame": None,
  "stamp": None,
  "colors": None,
}


def _as_color(value: object, fallback: tuple[int, int, int, int] = (255, 255, 255, 255)) -> rl.Color:
  if all(hasattr(value, channel) for channel in ("r", "g", "b", "a")):
    return rl.Color(
      _clamp_channel(getattr(value, "r"), fallback[0]),
      _clamp_channel(getattr(value, "g"), fallback[1]),
      _clamp_channel(getattr(value, "b"), fallback[2]),
      _clamp_channel(getattr(value, "a"), fallback[3]),
    )

  if isinstance(value, (tuple, list)):
    items = list(value)
    if len(items) == 3:
      items.append(fallback[3])
    if len(items) >= 4:
      return rl.Color(
        _clamp_channel(items[0], fallback[0]),
        _clamp_channel(items[1], fallback[1]),
        _clamp_channel(items[2], fallback[2]),
        _clamp_channel(items[3], fallback[3]),
      )

  return rl.Color(*fallback)


def _file_stamp(path: Path) -> tuple[str, int | None, int | None]:
  try:
    stat = path.stat()
    return (str(path), stat.st_mtime_ns, stat.st_size)
  except OSError:
    return (str(path), None, None)


def _clamp_channel(value: object, fallback: int) -> int:
  try:
    return max(0, min(255, int(value)))
  except (TypeError, ValueError):
    return fallback


def _load_color_map(path: Path) -> dict[str, dict[str, int]]:
  try:
    with path.open() as f:
      data = json.load(f)
    if isinstance(data, dict):
      return data
  except (OSError, ValueError, TypeError):
    pass
  return {}


def _build_color(entry: object, fallback: tuple[int, int, int, int]) -> rl.Color:
  if isinstance(entry, dict):
    red, green, blue, alpha = fallback
    return rl.Color(
      _clamp_channel(entry.get("red"), red),
      _clamp_channel(entry.get("green"), green),
      _clamp_channel(entry.get("blue"), blue),
      _clamp_channel(entry.get("alpha"), alpha),
    )
  return rl.Color(*fallback)


def _load_theme_colors() -> dict[str, rl.Color]:
  frame = gui_app.frame
  if frame == _THEME_COLOR_CACHE["frame"] and _THEME_COLOR_CACHE["colors"] is not None:
    return _THEME_COLOR_CACHE["colors"]  # type: ignore[return-value]

  stamp = (_file_stamp(STOCK_THEME_COLORS_PATH), _file_stamp(ACTIVE_THEME_COLORS_PATH))
  _THEME_COLOR_CACHE["frame"] = frame
  if stamp == _THEME_COLOR_CACHE["stamp"] and _THEME_COLOR_CACHE["colors"] is not None:
    return _THEME_COLOR_CACHE["colors"]  # type: ignore[return-value]

  stock_colors = _load_color_map(STOCK_THEME_COLORS_PATH)
  active_colors = _load_color_map(ACTIVE_THEME_COLORS_PATH)

  colors = {}
  for key, fallback in _FALLBACK_THEME_COLORS.items():
    colors[key] = _build_color(active_colors.get(key, stock_colors.get(key)), fallback)

  _THEME_COLOR_CACHE["stamp"] = stamp
  _THEME_COLOR_CACHE["colors"] = colors
  return colors


def get_theme_color(key: str, fallback: rl.Color | None = None) -> rl.Color:
  color = _load_theme_colors().get(key)
  if color is not None:
    return _as_color(color)
  return _as_color(fallback if fallback is not None else rl.WHITE)


def get_param_color(params, key: str, fallback_alpha: int = 255) -> rl.Color | None:
  value = params.get(key, encoding="utf-8") if params is not None else None
  if not value:
    return None

  color = value.strip()
  if not color or color.lower() == "stock":
    return None
  if color.startswith("#"):
    color = color[1:]

  if len(color) not in (6, 8):
    return None

  try:
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    alpha = int(color[6:8], 16) if len(color) == 8 else fallback_alpha
  except ValueError:
    return None

  return rl.Color(red, green, blue, alpha)


def is_stock_color_scheme(params) -> bool:
  if params is None:
    return True
  scheme = params.get("ColorScheme", encoding="utf-8", default="stock")
  return (scheme or "stock").lower() == "stock"


def get_visual_color(params, param_key: str, theme_key: str, fallback: rl.Color | None = None) -> rl.Color:
  base = _as_color(fallback if fallback is not None else rl.WHITE)
  override = get_param_color(params, param_key, base.a)
  if override is not None:
    return override
  return get_theme_color(theme_key, base)


def with_alpha(color: rl.Color, alpha: int) -> rl.Color:
  color = _as_color(color)
  return rl.Color(color.r, color.g, color.b, max(0, min(255, int(alpha))))
