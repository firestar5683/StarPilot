"""Validated onroad colors and independent logical-pixel layouts."""

import copy
import json
import math
import re
from functools import lru_cache
from typing import Any, NotRequired, TypedDict

from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.ui.onroad_torque_geometry import maximum_footprint

PARAM_KEY = "OnroadCustomizations"
MAX_BYTES = 16384
PALETTE = {"cardFill": "#000000A6", "cardBorder": "#C4CDD0B4", "text": "#FFFFFFFF"}
ROAD_COLORS = {"path": "#30FF9CFF", "pathEdge": "#00FF40FF", "laneLines": "#FFFFFFFF"}
PATH_MODES = ("default", "color", "rainbow", "acceleration")
WHEEL_SIZES = {"large": (144, 192, 240), "compact": (40, 50, 70)}


class Bounds(TypedDict):
  x: float
  y: float
  width: float
  height: float


class WidgetPlacement(TypedDict):
  x: float
  y: float
  enabled: bool


class Widget(TypedDict):
  label: str
  kind: str
  width: float
  height: float
  default: WidgetPlacement
  bounds: NotRequired[Bounds]
  visualInsetTop: NotRequired[float]
  layer: NotRequired[str]
  note: NotRequired[str]
  defaultAnchor: NotRequired[str]
  colors: NotRequired[dict[str, str | None]]
  resizable: NotRequired[dict[str, int]]


class LayoutProfile(TypedDict):
  label: str
  width: float
  height: float
  bounds: Bounds
  widgets: dict[str, Widget]
  reservedZones: list[Bounds]
  protectedWidget: NotRequired[str]
  inputZones: NotRequired[list[dict[str, Any]]]
  inputZonePriority: NotRequired[str]


def _widget(label: str, kind: str, width: float, height: float, x: float, y: float) -> Widget:
  return {"label": label, "kind": kind, "width": width, "height": height,
          "default": {"x": x, "y": y, "enabled": True}}


PROFILES: dict[str, LayoutProfile] = {
  "large": {"label": "Large UI", "width": 2160, "height": 1080,
            "bounds": {"x": 30, "y": 30, "width": 1800, "height": 1020},
            "reservedZones": [],
            "widgets": {
              "current_speed": _widget("Current speed", "current_speed", 580, 300, 640, 30),
              "cruise_limits": _widget("Cruise and speed limit", "cruise_limits", 176, 483, 88, 75),
              "speed_limit_actions": _widget("Speed limit actions", "speed_limit_actions", 176, 58, 88, 500),
              "steering_wheel": _widget("Steering wheel", "steering_wheel", 192, 192, 1588, 75),
              "driver_monitor": _widget("Driver monitoring", "driver_monitor", 192, 192, 88, 808)}},
  "compact": {"label": "Small UI", "width": 536, "height": 240,
              "bounds": {"x": 0, "y": 0, "width": 476, "height": 240},
              "protectedWidget": "speed_limit_actions",
              "reservedZones": [],
              "widgets": {
                "max_speed": _widget("Maximum speed", "max_speed", 162, 162, 0, 0),
                "speed_limit": _widget("Speed limit", "speed_limit", 118, 132, 330, 20),
                "speed_limit_actions": _widget("Speed limit actions", "speed_limit_actions", 282, 54, 174, 180),
                "steering_wheel": _widget("Steering wheel", "steering_wheel", 50, 50, 21, 176),
                "driver_monitor": _widget("Driver monitoring", "driver_monitor", 60, 60, 16, 10)}}}

# Coordinates remain anchored at the buttons, preserving saved v4 placements.
PROFILES["compact"]["widgets"]["speed_limit_actions"]["visualInsetTop"] = 32

LEGACY_WIDGETS = {"large": {"current_speed", "cruise_limits", "steering_wheel"},
                  "compact": {"max_speed", "speed_limit", "steering_wheel"}}
DM_WIDGETS = {profile: keys | {"driver_monitor"} for profile, keys in LEGACY_WIDGETS.items()}
for _profile, _data in PROFILES.items():
  _bounds = _data["bounds"]
  _x, _y, _width, _height = maximum_footprint(_bounds["x"], _bounds["y"], _bounds["width"], _bounds["height"], _data["width"])
  _data["widgets"]["torque_bar"] = {
    **_widget("Torque bar", "torque_bar", _width, _height, _x, _y), "layer": "underlay",
    "note": "Torque output, or steering-effort estimate on angle-controlled vehicles"}
ACTIONLESS_WIDGETS = {profile: set(data["widgets"]) - {"speed_limit_actions"} for profile, data in PROFILES.items()}

RAILLESS_WIDGETS = {profile: set(data["widgets"]) for profile, data in PROFILES.items()}
RAIL_WIDGETS = ("model_confidence", "conditional_mode", "following_distance")
for _index, (_key, _label) in enumerate(zip(RAIL_WIDGETS, ("Model confidence", "CEM and driving mode", "Following distance"), strict=True)):
  PROFILES["compact"]["widgets"][_key] = {
    **_widget(_label, _key, 60, 80, 476, _index * 80),
    "bounds": {"x": 0, "y": 0, "width": 536, "height": 240},
  }

# Keep layouts saved before camera widgets valid when the registry grows.
CAMERALESS_WIDGETS = {profile: set(data["widgets"]) for profile, data in PROFILES.items()}
CAMERA_WIDGETS = ("pip_left", "pip_right")
for _profile, (_size, _margin) in {"large": (600, 24), "compact": (80, 16)}.items():
  _bounds = PROFILES[_profile]["bounds"]
  for _side, _key in zip(("left", "right"), CAMERA_WIDGETS, strict=True):
    _x = _bounds["x"] + (_margin if _side == "left" else _bounds["width"] - _margin - _size)
    _y = _bounds["y"] + _bounds["height"] - _margin - _size
    PROFILES[_profile]["widgets"][_key] = {
      **_widget(f"PiP {_side} side camera", "pip_camera", _size, _size, _x, _y), "layer": "underlay"}

MODE_WIDGET = "driving_mode_descriptions"
for _profile, _geometry in {"large": (580, 68, 640, 344), "compact": (168, 60, 162, 22)}.items():
  _mode_widget = _widget("Driving Mode Descriptions", MODE_WIDGET, *_geometry)
  _mode_widget["default"]["enabled"] = False
  PROFILES[_profile]["widgets"][MODE_WIDGET] = _mode_widget

# It starts disabled so an upgrade never adds a new onroad element without the
# driver's choice; validation below adds the placement to older documents.
CLOCK_WIDGET = "clock"
for _profile, _geometry in {"large": (300, 72, 780, 430), "compact": (140, 44, 168, 92)}.items():
  _clock_widget = _widget("Clock", CLOCK_WIDGET, *_geometry)
  _clock_widget["default"]["enabled"] = False
  PROFILES[_profile]["widgets"][CLOCK_WIDGET] = _clock_widget

_FRAME_COLORS = {"cardFill": "#00000000", "cardBorder": "#00000000"}
_ACTION_COLORS = {"cardFill": "#0C1820EB", "cardBorder": "#A6DFBEFF", "text": "#FFFFFFFF"}
WIDGET_COLORS = {
  "large": {
    MODE_WIDGET: {"text": "#FFFFFFFF"},
    CLOCK_WIDGET: {"text": "#FFFFFFFF"},
    "current_speed": {"text": None},
    "cruise_limits": {"cardFill": None, "cardBorder": None, "text": None},
    "speed_limit_actions": _ACTION_COLORS,
    "steering_wheel": {"cardFill": None, "cardBorder": "#00000000"},
    "driver_monitor": _FRAME_COLORS,
  },
  "compact": {
    MODE_WIDGET: {"text": "#FFFFFFFF"},
    CLOCK_WIDGET: {"text": "#FFFFFFFF"},
    "max_speed": {"text": None},
    "speed_limit_actions": _ACTION_COLORS,
    "driver_monitor": _FRAME_COLORS,
    "model_confidence": _FRAME_COLORS,
    "conditional_mode": _FRAME_COLORS,
    "following_distance": {**_FRAME_COLORS, "text": "#FFFFFFFF"},
  },
}


# Back-to-front order used when a layout first opts into custom layers.
DEFAULT_WIDGET_ORDER = {
  "large": ("pip_left", "pip_right", "cruise_limits", "speed_limit_actions", "current_speed",
            "steering_wheel", "torque_bar", "driver_monitor", MODE_WIDGET, CLOCK_WIDGET),
  "compact": ("pip_left", "pip_right", "speed_limit", "max_speed", "steering_wheel", "torque_bar",
              "speed_limit_actions", "driver_monitor", *RAIL_WIDGETS, MODE_WIDGET, CLOCK_WIDGET),
}


def validate_widget_order(order, widgets):
  if (type(order) is not list or any(type(key) is not str for key in order) or
      len(order) != len(widgets) or set(order) != set(widgets)):
    raise ValueError("Invalid widget layer order")
  return list(order)


def widget_order(document, profile):
  return document.get("widgetOrder", {}).get(str(profile), DEFAULT_WIDGET_ORDER[str(profile)])


def widget_bounds(profile, widget):
  return PROFILES[profile]["widgets"][widget].get("bounds", PROFILES[profile]["bounds"])


def customization_metadata():
  profiles = copy.deepcopy(PROFILES)
  profiles["large"]["widgets"]["driver_monitor"]["defaultAnchor"] = "driver_side"
  profiles["large"]["inputZones"] = [{"id": "favorites_drawer", "label": "Quick Select drawer",
                                       "x": 30, "y": 900, "width": 150, "height": 150}]
  profiles["compact"]["inputZones"] = [
    {"id": f"favorite_{index + 1}", "label": f"Quick Select {index + 1}",
     "x": index * 476 / 3, "y": 0, "width": 476 / 3, "height": 240} for index in range(3)]
  for profile in profiles.values():
    profile["inputZonePriority"] = "Enabled Quick Select slots; speed-limit controls and steering wheel take priority"
  for name, profile in profiles.items():
    for key, widget in profile["widgets"].items():
      widget["colors"] = dict(WIDGET_COLORS[name].get(key, {}))
    profile["widgets"]["steering_wheel"]["resizable"] = {
      "min": WHEEL_SIZES[name][0], "default": WHEEL_SIZES[name][1], "max": WHEEL_SIZES[name][2]}
  for profile, data in profiles.items():
    data["widgetOrder"] = list(DEFAULT_WIDGET_ORDER[profile])
  return {"profiles": profiles, "roadColorFields": [
    {"id": key, "label": label, "default": ROAD_COLORS[key]}
    for key, label in (("path", "Path"), ("pathEdge", "Path edges"), ("laneLines", "Outer lane lines"))], "paletteFields": [
    {"id": key, "label": label, "default": PALETTE[key]}
    for key, label in (("cardFill", "Card fill"), ("cardBorder", "Card border"), ("text", "Text"))]}


def default_document():
  return {"version": 4, "clock24Hour": False, "palette": dict(PALETTE), "roadColors": {profile: {} for profile in PROFILES},
          "widgetColors": {profile: {} for profile in PROFILES}, "layouts": {
    profile: {key: {**widget["default"], **({"size": WHEEL_SIZES[profile][1]} if key == "steering_wheel" else {})}
              for key, widget in data["widgets"].items()}
    for profile, data in PROFILES.items()}}


def validate_document(value):
  if type(value) is not dict or type(value.get("version")) is not int or value["version"] not in (1, 2, 3, 4):
    raise ValueError("Invalid customization version")
  fields = {"version", "palette", "layouts"} | ({"widgetColors"} if value["version"] >= 2 else set())
  if value["version"] >= 3:
    fields.add("roadColors")
  if value['version'] == 4 and 'speedSources' in value:
    fields.add('speedSources')
    if type(value['speedSources']) is not bool:
      raise ValueError('Invalid speed source drawer preference')
  if value['version'] == 4 and 'widgetOrder' in value:
    fields.add('widgetOrder')
  if 'clock24Hour' in value:
    fields.add('clock24Hour')
    if type(value['clock24Hour']) is not bool:
      raise ValueError('Invalid clock format preference')
  if set(value) != fields:
    raise ValueError("Invalid customization fields")
  palette, layouts = value["palette"], value["layouts"]
  if type(palette) is not dict or set(palette) != set(PALETTE) or type(layouts) is not dict or set(layouts) != set(PROFILES):
    raise ValueError("Invalid customization fields")
  if any(all(type(layouts[profile]) is dict and
             (set(layouts[profile]) - {"vasm", MODE_WIDGET, CLOCK_WIDGET, *CAMERA_WIDGETS}) == keys
             for profile, keys in shape.items())
         for shape in (LEGACY_WIDGETS, DM_WIDGETS, ACTIONLESS_WIDGETS)):
    layouts = copy.deepcopy(layouts)
    cruise = layouts["large"]["cruise_limits"]
    if (type(cruise) is not dict or set(cruise) != {"x", "y", "enabled"} or type(cruise["enabled"]) is not bool or
        any(type(cruise[axis]) not in (int, float) for axis in ("x", "y"))):
      raise ValueError("Invalid widget placement")
    try:
      if not all(math.isfinite(cruise[axis]) for axis in ("x", "y")):
        raise ValueError("Invalid widget placement")
    except OverflowError as exc:
      raise ValueError("Invalid widget placement") from exc
    cruise_default = PROFILES["large"]["widgets"]["cruise_limits"]["default"]
    actions_default = PROFILES["large"]["widgets"]["speed_limit_actions"]["default"]
    layouts["large"]["speed_limit_actions"] = {
      "x": actions_default["x"] + cruise["x"] - cruise_default["x"],
      "y": actions_default["y"] + cruise["y"] - cruise_default["y"],
      "enabled": cruise["enabled"],
    }
    for profile in PROFILES:
      for key in ("driver_monitor", "torque_bar", "speed_limit_actions"):
        layouts[profile].setdefault(key, dict(PROFILES[profile]["widgets"][key]["default"]))
  if all(type(layouts[profile]) is dict and (set(layouts[profile]) - {"vasm", MODE_WIDGET, CLOCK_WIDGET, *CAMERA_WIDGETS}) == keys
         for profile, keys in RAILLESS_WIDGETS.items()):
    layouts = copy.deepcopy(layouts)
    for key in RAIL_WIDGETS:
      layouts["compact"][key] = dict(PROFILES["compact"]["widgets"][key]["default"])
  if all(type(layouts[profile]) is dict and (set(layouts[profile]) - {"vasm", MODE_WIDGET, CLOCK_WIDGET}) == keys
         for profile, keys in CAMERALESS_WIDGETS.items()):
    layouts = copy.deepcopy(layouts)
    for profile in PROFILES:
      has_legacy = "vasm" in layouts[profile]
      legacy = layouts[profile].pop("vasm", None)
      if has_legacy and (type(legacy) is not dict or set(legacy) != {"x", "y", "enabled"} or
                                 type(legacy["enabled"]) is not bool or
                                 any(type(legacy[axis]) not in (int, float) or not math.isfinite(legacy[axis]) for axis in ("x", "y"))):
        raise ValueError("Invalid legacy camera placement")
      for side, key in enumerate(CAMERA_WIDGETS):
        widget = PROFILES[profile]["widgets"][key]
        position = dict(widget["default"])
        if legacy is not None:
          bounds = widget_bounds(profile, key)
          position.update(enabled=legacy["enabled"],
                          x=max(bounds["x"], min(legacy["x"], bounds["x"] + bounds["width"] - 2 * widget["width"])) + side * widget["width"],
                          y=max(bounds["y"], min(legacy["y"], bounds["y"] + bounds["height"] - widget["height"])))
        layouts[profile][key] = position
  layouts = copy.deepcopy(layouts)
  for profile, data in PROFILES.items():
    if type(layouts[profile]) is dict:
      missing = set(data["widgets"]) - set(layouts[profile])
      if missing and missing <= {MODE_WIDGET, CLOCK_WIDGET}:
        for optional in missing:
          layouts[profile][optional] = dict(data["widgets"][optional]["default"])
  result = default_document()
  for key, color in palette.items():
    if type(color) is not str or re.fullmatch(r"#[0-9a-fA-F]{8}", color) is None:
      raise ValueError("Colors must be #RRGGBBAA")
    result["palette"][key] = color.upper()
  if value["version"] >= 2:
    colors = value["widgetColors"]
    if type(colors) is not dict or set(colors) != set(PROFILES):
      raise ValueError("Invalid widget color profiles")
    for profile, widgets in colors.items():
      if type(widgets) is not dict or not widgets.keys() <= WIDGET_COLORS[profile].keys():
        raise ValueError("Invalid widget color IDs")
      for key, overrides in widgets.items():
        if type(overrides) is not dict or not overrides.keys() <= WIDGET_COLORS[profile][key].keys():
          raise ValueError("Invalid widget color fields")
        if any(type(color) is not str or re.fullmatch(r"#[0-9a-fA-F]{8}", color) is None for color in overrides.values()):
          raise ValueError("Colors must be #RRGGBBAA")
        if overrides:
          result["widgetColors"][profile][key] = {field: color.upper() for field, color in overrides.items()}
  if value["version"] >= 3:
    colors = value["roadColors"]
    if type(colors) is not dict or set(colors) != set(PROFILES):
      raise ValueError("Invalid road color profiles")
    for profile, overrides in colors.items():
      if type(overrides) is not dict or not overrides.keys() <= ROAD_COLORS.keys() | {"pathMode"}:
        raise ValueError("Invalid road color fields")
      for key, color in overrides.items():
        if key == "pathMode":
          if type(color) is not str or color not in PATH_MODES:
            raise ValueError("Invalid path color mode")
        elif type(color) is not str or re.fullmatch(r"#[0-9a-fA-F]{8}", color) is None:
          raise ValueError("Colors must be #RRGGBBAA")
        result["roadColors"][profile][key] = color if key == "pathMode" else color.upper()
  for profile, data in PROFILES.items():
    layout = layouts[profile]
    if type(layout) is not dict or set(layout) != set(data["widgets"]):
      raise ValueError("Invalid widget IDs")
    for key, widget in data["widgets"].items():
      placement = layout[key]
      bounds = widget_bounds(profile, key)
      expected = {"x", "y", "enabled"} | ({"size"} if key == "steering_wheel" and value["version"] == 4 else set())
      if type(placement) is not dict or set(placement) != expected or type(placement["enabled"]) is not bool:
        raise ValueError("Invalid widget placement")
      size = WHEEL_SIZES[profile][1]
      if key == "steering_wheel" and value["version"] == 4:
        size = placement["size"]
        minimum, _, maximum = WHEEL_SIZES[profile]
        if type(size) is not int or not minimum <= size <= maximum:
          raise ValueError("Invalid steering wheel size")
      for axis, extent in (("x", "width"), ("y", "height")):
        number = placement[axis]
        dimension = size if key == "steering_wheel" else widget[extent]
        if type(number) not in (int, float) or not math.isfinite(number) or not bounds[axis] <= number <= bounds[axis] + bounds[extent] - dimension:
          raise ValueError("Widget outside profile bounds")
      result["layouts"][profile][key] = {**placement, **({"size": size} if key == "steering_wheel" else {})}
    if profile == "compact":
      actions = result["layouts"][profile]["speed_limit_actions"]
      area = data["widgets"]["speed_limit_actions"]
      for key, widget in data["widgets"].items():
        if key in ("speed_limit_actions", "speed_limit") or widget.get("layer") == "underlay":
          continue
        placement = result["layouts"][profile][key]
        if key in (MODE_WIDGET, CLOCK_WIDGET) and not placement["enabled"]:
          continue
        width, height = ((placement["size"],) * 2 if key == "steering_wheel" else
                         (widget["width"], widget["height"]))
        if (placement["x"] < actions["x"] + area["width"] and placement["x"] + width > actions["x"] and
            placement["y"] < actions["y"] + area["height"] and placement["y"] + height > actions["y"]):
          raise ValueError("Widget overlaps protected speed limit actions")
  if 'widgetOrder' in value:
    orders = value['widgetOrder']
    if type(orders) is not dict or not orders.keys() <= PROFILES.keys():
      raise ValueError("Invalid widget layer profiles")
    result['widgetOrder'] = {}
    for profile, order in orders.items():
      if type(order) is list:
        order = [*order, *(key for key in (MODE_WIDGET, CLOCK_WIDGET) if key not in order)]
      result['widgetOrder'][profile] = validate_widget_order(order, PROFILES[profile]['widgets'])
  if 'speedSources' in value:
    result['speedSources'] = value['speedSources']
  if 'clock24Hour' in value:
    result['clock24Hour'] = value['clock24Hour']
  if len(json.dumps(result, separators=(",", ":")).encode()) > MAX_BYTES:
    raise ValueError("Customization too large")
  return result


def _unique_object(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError("Duplicate customization field")
    result[key] = value
  return result


def decode_document(raw):
  return validate_document(json.loads(raw, object_pairs_hook=_unique_object))


def read_customization(params):
  try:
    raw, readable = read_saved(params, PARAM_KEY, MAX_BYTES)
    return decode_document(raw) if readable and raw is not None else default_document()
  except (AttributeError, OSError, TypeError, ValueError, UnicodeError, RecursionError):
    return default_document()


def placement(document, profile, widget):
  return document["layouts"][str(profile)][widget]


def widget_size(document, profile, widget):
  default = PROFILES[str(profile)]["widgets"][widget]
  position = placement(document, profile, widget)
  return (position.get("size", WHEEL_SIZES[str(profile)][1]),) * 2 if widget == "steering_wheel" else (default["width"], default["height"])


def offset(document, profile, widget):
  position = placement(document, profile, widget)
  default = PROFILES[str(profile)]["widgets"][widget]["default"]
  return position["x"] - default["x"], position["y"] - default["y"]


def widget_palette(document, profile, widget):
  defaults = WIDGET_COLORS[str(profile)].get(widget, {})
  colors = {key: document["palette"][key] if value is None else value for key, value in defaults.items()}
  colors.update(document.get("widgetColors", {}).get(str(profile), {}).get(widget, {}))
  return colors


def rgba(document, key, profile=None, widget=None):
  if profile is None:
    color = document["palette"][key]
  else:
    assert widget is not None
    default = WIDGET_COLORS[str(profile)][widget][key]
    color = document.get("widgetColors", {}).get(str(profile), {}).get(widget, {}).get(key, default or document["palette"][key])
  return _rgba_value(color)


@lru_cache(maxsize=256)
def _rgba_value(color):
  return tuple(int(color[index:index + 2], 16) for index in (1, 3, 5, 7))


def set_speed_sources(params, opened):
  """Change only a valid saved document; display fallback is not write authority."""
  if type(opened) is not bool:
    raise ValueError('Invalid speed source drawer preference')
  raw, readable = read_saved(params, PARAM_KEY, MAX_BYTES)
  if not readable:
    raise ValueError('Saved layout is unreadable')
  document = decode_document(raw) if raw is not None else default_document()
  document['speedSources'] = opened
  params.put(PARAM_KEY, json.dumps(validate_document(document), separators=(',', ':')))
