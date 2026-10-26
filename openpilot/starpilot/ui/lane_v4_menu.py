"""Galaxy-only presentation; the native lane page keeps its existing five rows."""
from dataclasses import replace
import math
from openpilot.starpilot.lateral.lane_tuning import NUMBERS, PREFIX, PAIRS, DEFAULTS, GEOMETRY_KEYS, STOCK_CORRECTION, BEND_KEYS, ADAPTATION
from openpilot.starpilot.ui.feature_settings_state import FeatureRow

SECTIONS = {
  "lane/activation": ("Activation Conditions", "Choose when lane centering can operate, including minimum speed, lane width, clearance, and which detected lane lines and road edges it can use."),
  "lane/activation/geometry": ("Geometry", "Set your car’s width, the clearances used between two boundaries or beside a single boundary, and the maximum lane width allowed for centring."),
  "lane/activation/acceptance": ("Line and edge acceptance", "Set confidence and position-uncertainty limits for accepting lane lines and road edges."),
  "lane/activation/acceptance/higher_confidence": ("Higher-confidence lane lines", "Lines at or above the confidence threshold set here must pass the uncertainty limit set here. Lines below this confidence threshold are checked using the Lower-confidence lane lines settings instead."),
  "lane/activation/acceptance/lower_confidence": ("Lower-confidence lane lines", "Lines below the higher-confidence threshold can still be accepted if they meet the minimum confidence and maximum uncertainty set here. Lines below this minimum confidence are ignored."),
  "lane/preferences": ("Driving Preferences", "Adjust correction strength, limits, smoothing, model preference and curve adaptation."),
  "lane/preferences/curves": ("Curve adaptation", "Set the bend radii where curve adaptation starts and reaches full effect."),
  "lane/preferences/smoothing": ("Smoothing", "Adjust how smoothly boundary positions and lane-centering correction change."),
}
PAGES = tuple(SECTIONS)
SPECS = {PREFIX + row[0]: row for row in NUMBERS.values()}
E2E_MAX = "LaneCenteringE2EAuthority"
OFFSET = "LaneCenterOffset"
CHECK_KEYS = SPECS.keys() | {E2E_MAX, OFFSET}
# Display grids stay within the controller's SI bounds. Unit changes never write a tune.
IMPERIAL = {
  "MinSpeed": (1 / .44704, "mph", 0, 45, 1),
  "CarWidth": (1 / .0254, "in", 40, 118, 1),
  "MaxWidth": (1 / .3048, "ft", 7, 32, .5),
  "HighStd": (1 / .3048, "ft", 0, 9.5, .25),
  "LowStd": (1 / .3048, "ft", 0, 9.5, .25),
  "EdgeStd": (1 / .3048, "ft", 0, 9.5, .25),
  "Clearance": (1 / .0254, "in", 0, 39, .5),
  "SingleClearance": (1 / .0254, "in", 0, 39, .5),
  "SmoothingDistance": (1 / .0254, "in", 0, 19.5, .5),
  "SingleDeadband": (1 / .0254, "in", 0, 5.75, .25),
  "OverrideStart": (1 / .0254, "in", 0, 39, .5),
  "OverrideFull": (1 / .0254, "in", 0, 39, .5),
  "CurveFullRadius": (1 / .3048, "ft", 100, 3250, 50),
  "CurveStartRadius": (1 / .3048, "ft", 350, 9800, 50),
}
DISTANCE_KEYS = {key for key, spec in SPECS.items() if spec[5] in ("m", "cm", "speed")} | {OFFSET}


def display_grid(key, metric):
  if key == OFFSET:
    return (100, "cm", -30, 30, 1) if metric else (1 / .0254, "in", -11.5, 11.5, .25)
  if key == E2E_MAX:
    return 100, "%", 0, 100, 5
  spec = SPECS[key]
  if not metric and spec[0] in IMPERIAL:
    return IMPERIAL[spec[0]]
  if spec[5] == "speed":
    return 3.6, "km/h", 0, 70, 1
  scale = 100 / STOCK_CORRECTION if spec[5] == "% of stock" else 100 if spec[5] in ("%", "cm") else 1
  return scale, spec[5], spec[2] * scale, spec[3] * scale, spec[4] * scale


def unit_help(text, unit):
  if unit in ("in", "ft"):
    name = "inches" if unit == "in" else "feet"
    return text.replace("centimetres", name).replace("metres", name)
  return text


def present(owner, row, metric):
  """Clamp edit ranges to peer settings on a clean display grid, never the saved value."""
  key = row.key
  scale, unit, origin, end, step = display_grid(key, metric)
  low, high = origin, end
  try:
    if key in PAIRS or key in LIMIT_PAIRS:
      peer_key, lower = (PAIRS[key], key.endswith("MinConfidence")) if key in PAIRS else LIMIT_PAIRS[key]
      peer = float(owner._value(peer_key)[0]) * scale
      strict = "Radius" in key or "Override" in key
      if lower:
        high = min(high, peer - (1e-7 if strict else 0))
      else:
        low = max(low, peer + (1e-7 if strict else 0))
    if key in GEOMETRY_KEYS:
      width, clearance, maximum = (float(owner._value(PREFIX + k)[0]) for k in ("CarWidth", "Clearance", "MaxWidth"))
      if key.endswith("MaxWidth"):
        low = max(low, (width + 2 * clearance) * scale + 1e-7)
      else:
        high = min(high, ((maximum - width) / 2 if key.endswith("Clearance") else maximum - 2 * clearance) * scale - 1e-7)
    low = round(origin + math.ceil((low - origin) / step - 1e-9) * step, 8)
    high = round(origin + math.floor((high - origin) / step + 1e-9) * step, 8)
    valid = math.isfinite(low) and math.isfinite(high) and low <= high
  except (ValueError, TypeError, OverflowError):
    valid = False
  value = owner._value(key)[0]
  try:
    value = str(round(float(value) * scale, 3)) if row.step else row.value
    default = str(float(owner._default(key)) * scale)
    # Reset must not cross a peer, and must restore the exact SI default (not a rounded display step).
    if not valid or not low <= float(default) <= high:
      default = None
  except (ValueError, TypeError):
    default = None
  return replace(row, value=value, minimum=low if valid else origin, maximum=high if valid else end,
                 step=step if row.step else 0, unit=unit, display_unit=unit,
                 available=row.available and valid, default_value=default,
                 dependencies=dependencies(owner, key), reason=unit_help(row.reason, unit))

LIMIT_PAIRS = {PREFIX + "ResponseMin": (PREFIX + "ResponseTime", True),
               PREFIX + "ResponseTime": (PREFIX + "ResponseMin", False),
               PREFIX + "E2EMin": (E2E_MAX, True), E2E_MAX: (PREFIX + "E2EMin", False),
               PREFIX + "CurveFullRadius": (PREFIX + "CurveStartRadius", True),
               PREFIX + "CurveStartRadius": (PREFIX + "CurveFullRadius", False),
               PREFIX + "OverrideStart": (PREFIX + "OverrideFull", True),
               PREFIX + "OverrideFull": (PREFIX + "OverrideStart", False)}
CURVE_HELP = "Allows the correction response time and model path preference to change based on how tight a bend is. On straight roads, lane centering has less authority to override the model, allowing it to move around parked cars, cones and other hazards if the model is able to. As bends tighten, the model has less authority, and the correction response time is reduced to allow faster reactions to changes."

def dependencies(owner, key):
  names = ([name for name in GEOMETRY_KEYS if name != key] if key in GEOMETRY_KEYS else
           [PAIRS[key]] if key in PAIRS else []) + (["IsMetric"] if key in DISTANCE_KEYS else [])
  if key in LIMIT_PAIRS:
    names.append(LIMIT_PAIRS[key][0])
  if key in BEND_KEYS or key in (PREFIX + "ResponseTime", E2E_MAX):
    names.append(ADAPTATION)
  return tuple((name, owner._raw(name)) for name in names)

def stored_number(request):
  value = float(request.value)
  if request.key == E2E_MAX:
    return value / 100
  if request.key in DISTANCE_KEYS:
    scales = {"mph": .44704, "km/h": 1 / 3.6, "cm": .01, "m": 1, "in": .0254, "ft": .3048}
    return value * scales[request.display_unit]
  spec = SPECS[request.key]
  if spec[5] == "% of stock":
    return value * STOCK_CORRECTION / 100
  return value / 100 if spec[5] == "%" else value

def edit_error(owner, request):
  import math
  try:
    value = stored_number(request)
    spec = SPECS.get(request.key)
    low, high = (spec[2], spec[3]) if spec else (-.3, .3) if request.key == OFFSET else (0., 1.)
    if not math.isfinite(value) or not low <= value <= high:
      return "Value outside setting range"
    if request.dependencies != dependencies(owner, request.key):
      return "Related settings changed; refresh settings"
    if request.key in BEND_KEYS and owner._value(ADAPTATION)[0] != "1":
      return "Turn on Curve adaptation to edit bend settings"
    if request.key in LIMIT_PAIRS:
      peer_key, is_lower = LIMIT_PAIRS[request.key]
      peer = float(owner._value(peer_key)[0])
      lower, upper = (value, peer) if is_lower else (peer, value)
      strict = "Radius" in request.key or "Override" in request.key
      if not math.isfinite(peer) or lower > upper or strict and lower == upper:
        return ("Start model override must be below Full model override" if "Override" in request.key else
                "Minimum corner radius must be below Maximum corner radius" if strict else
                "Minimum correction response time cannot exceed Maximum correction response time" if "Response" in request.key else
                "Minimum model path preference cannot exceed Maximum model path preference")
    if request.key in DISTANCE_KEYS:
      expected_unit = display_grid(request.key, owner._value("IsMetric")[0] == "1")[1]
      if request.display_unit != expected_unit:
        return "Units changed; refresh settings"
    if request.key in GEOMETRY_KEYS:
      geometry = {key: value if key == request.key else float(owner._value(key)[0]) for key in GEOMETRY_KEYS}
      if (not all(math.isfinite(v) for v in geometry.values()) or
          geometry[PREFIX + "CarWidth"] + 2 * geometry[PREFIX + "Clearance"] >= geometry[PREFIX + "MaxWidth"]):
        return "Body width + twice Two-boundary minimum clearance must be below maximum lane width"
    if request.key in PAIRS:
      peer = float(owner._value(PAIRS[request.key])[0])
      lower, upper = (value, peer) if request.key.endswith("MinConfidence") else (peer, value)
      if not math.isfinite(peer) or lower > upper:
        return "Minimum confidence for Lower-confidence lane lines cannot exceed Minimum confidence for Higher-confidence lane lines"
    return ""
  except (ValueError, TypeError, KeyError, OSError):
    return "Invalid lane setting or related saved value"

RANGE_PAIRS = {
  PREFIX + "OverrideStart": ("override", "min", "Model override thresholds"),
  PREFIX + "OverrideFull": ("override", "max", "Model override thresholds"),
  PREFIX + "ResponseMin": ("response", "min", "Correction response time"),
  PREFIX + "ResponseTime": ("response", "max", "Correction response time"),
  PREFIX + "E2EMin": ("preference", "min", "Model path preference"),
  E2E_MAX: ("preference", "max", "Model path preference"),
  PREFIX + "CurveFullRadius": ("radius", "min", "Corner radius"),
  PREFIX + "CurveStartRadius": ("radius", "max", "Corner radius"),
}
RANGE_HELP = {
  "override": "Set how far the model path must differ from the lane target before a confident model reduces lane correction. Min starts the reduction; Max reaches the full reduction allowed by the current Model path preference. Lower distances allow reduction sooner; higher distances keep centering stronger. With Model path preference at 0%, these thresholds have no effect. Min must be below Max. Measured in centimetres.",
  "response": "Set how quickly lane centering follows changes in the correction it requests. Lower values respond faster; higher values smooth changes more gradually. This controls response speed, not correction strength. With Curve adaptation on, Max applies on straight roads and Min applies to the tightest bends. Measured in seconds.",
  "preference": "Control how much a confident model path can reduce lane-centering correction when it differs from the lane target. Higher values allow more reduction; 0% prevents it. With Curve adaptation on, Max applies on straight roads and Min applies to the tightest bends.",
  "radius": "Set how tight a bend must be for Curve adaptation to respond. As the bend’s radius falls below Max, model path preference and correction response time gradually decrease. At Min or below, both use their minimum settings. Larger radius values make adaptation respond to gentler bends; smaller values require tighter bends. Radius is measured in metres.",
}

def range_descriptor(row):
  pair = RANGE_PAIRS.get(row.key)
  if pair is None:
    return None
  group, end, label = pair
  enabled = dict(row.dependencies).get(ADAPTATION) in (None, b"1")
  return dict(group=group, end=end, label=label, help=unit_help(RANGE_HELP[group], row.unit), enabled=enabled)


def menu(owner, page, rows, allowed, metric):
  root_keys = {"LaneCentering", "LaneCenteringPauseOnSignal", "LaneCenterOffset"}
  if page == "lane":
    rows = [row for row in rows if row.key in root_keys]
    descriptions = {"LaneCentering": "Use detected lane lines and road edges to help guide the model path.",
                    "LaneCenteringPauseOnSignal": "Fade lane correction and clear boundary history while a turn signal is active.",
                    "LaneCenterOffset": "Shift the centre target when centring between two boundaries. Negative is left; positive is right. Keeping away from a single boundary ignores this offset."}
    rows = [replace(row, reason=descriptions[row.key] if row.available else row.reason) for row in rows]
  elif page == "lane/preferences":
    rows = [row for row in rows if row.key not in root_keys]
  else:
    rows = []
  adaptive = owner._value(ADAPTATION)[0] == "1"
  if page == "lane":
    toggle = owner._bool_row(ADAPTATION, "Curve adaptation", allowed, reason=CURVE_HELP)
    pause_index = next(i for i, row in enumerate(rows) if row.key == "LaneCenteringPauseOnSignal")
    rows.insert(pause_index + 1, toggle)
  if page == "lane/preferences":
    rows = [replace(row, label="Maximum model path preference", dependencies=dependencies(owner, row.key),
                    reason="Normal model preference, also used with Curve adaptation off. Greater percentages allow more confidence-dependent reduction of lane correction; tighter bends reduce this toward the minimum. Does not remove the model path.")
            if row.key == E2E_MAX else row for row in rows]
  group = page.rsplit("/", 1)[-1]
  for key, spec in SPECS.items():
    if spec[8] != group:
      continue
    row = owner._number_row(key, spec[6], allowed and (adaptive or key not in BEND_KEYS))
    reason = spec[7]
    if not metric and key == PREFIX + "LookaheadTime":
      reason = reason.replace("8-35 metres", "approximately 26-115 feet")
    row = replace(row, reason=reason + (" Turn on Curve adaptation to edit." if key in BEND_KEYS and not adaptive else "") if allowed else row.reason)
    rows.append(present(owner, row, metric))
  # Keep each minimum immediately beside its ordinary maximum.
  for lower, upper in ((PREFIX + "ResponseMin", PREFIX + "ResponseTime"), (PREFIX + "E2EMin", E2E_MAX)):
    child = next((row for row in rows if row.key == lower), None)
    if child is not None:
      rows.remove(child)
      rows.insert(next(i for i, row in enumerate(rows) if row.key == upper) + 1, child)
  if page == "lane/preferences":
    order = ["LaneCenteringStrength", PREFIX + "MaxCorrection", PREFIX + "SingleDeadband", PREFIX + "LookaheadTime",
             E2E_MAX, PREFIX + "E2EMin", PREFIX + "OverrideStart", PREFIX + "OverrideFull"]
    rows.sort(key=lambda row: order.index(row.key) if row.key in order else len(order))
  if page.endswith("/smoothing"):
    boundary_keys = {PREFIX + "SmoothingTime", PREFIX + "SmoothingDistance"}
    rows = [row for row in rows if row.key not in boundary_keys] + [row for row in rows if row.key in boundary_keys]
  rows.extend(FeatureRow("", title, description, page=child, available=True)
              for child, (title, description) in SECTIONS.items() if child.rsplit("/", 1)[0] == page)
  if page == "lane/activation/acceptance":
    rows = [row for row in rows if row.page] + [row for row in rows if not row.page]
  return SECTIONS[page][0] if page in SECTIONS else "Lane Centering", rows
