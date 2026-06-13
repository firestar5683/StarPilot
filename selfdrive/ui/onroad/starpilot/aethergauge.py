from dataclasses import dataclass
from enum import Enum
import math
import pyray as rl
from openpilot.common.constants import CV
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.selfdrive.ui.onroad.starpilot.starpilot_border import _csc_state, _intensity, _glow_color


# --- Scale factor (single knob for all pixel-space dimensions) ---

SCALE = 1.5


# --- Named constants ---

X_MIN = 3.0
X_MAX = 60.0
PATH_Y_FAR_SCALE = 1800.0
PERSPECTIVE_GAIN = 0.35
PERSPECTIVE_MAX_OFFSET = 26.0 * SCALE
PERSPECTIVE_EXPONENT = 1.8

ROAD_HEIGHT = 80.0 * SCALE
ROAD_SEGMENTS = 24
ROAD_W_BOTTOM = 22.0 * SCALE
ROAD_W_TOP = 14.0 * SCALE
ROAD_THICKNESS = 4.0 * SCALE
ROAD_HALF_SIZE = 40.0 * SCALE
ROAD_EDGE_INSET = 2.0 * SCALE
FILL_ALPHA = 35

MIN_SPEED_FOR_TIME = 0.3
MAX_TIME_DISPLAY = 99.0
TIME_FACTOR = 2.0

STOP_SNAP_THRESHOLD = 0.5
STOP_LERP_RATE = 0.25
STOP_DISTANCE_MAX = 60.0

CHEVRON_COUNT = 6
CHEVRON_SPACING = 0.3
CHEVRON_STEP = 0.05

CEM_STATUS_CURVE = 3
CEM_STATUS_LEAD = 4
CEM_STATUS_STOP_LIGHT = 8

LEAD_STOPPED_SPEED_THRESHOLD = 1.0

COLOR_FORCE_STOP = rl.Color(255, 30, 60, 255)
COLOR_LEAD_STOPPED = rl.Color(255, 60, 60, 255)
COLOR_LEAD_SLOWER = rl.Color(255, 191, 0, 255)
COLOR_SHADOW = rl.Color(0, 0, 0, 100)
COLOR_STOP_SIGN = rl.Color(196, 30, 58, 255)
COLOR_STOP_SIGN_OUTLINE = rl.Color(255, 255, 255, 255)
COLOR_STOP_LINE_GLOW = rl.Color(255, 30, 60, 255)
COLOR_STOP_LINE_CORE = rl.Color(255, 200, 200, 255)

# Set to True to force test-cycle mode (flip back to False before pushing)
TEST_CYCLE = False


# --- Conversion helpers ---

def _speed_conversion() -> float:
  return CV.MS_TO_KPH if ui_state.is_metric else CV.MS_TO_MPH

def _speed_unit() -> str:
  return "km/h" if ui_state.is_metric else "mph"

def _to_display_speed(val: float) -> tuple[int, str]:
  return int(round(val * _speed_conversion())), _speed_unit()

def _get_val(msg: str, attr: str, default=None):
  return getattr(ui_state.sm[msg], attr, default) if _sm_valid(msg) else default


# --- Shared helpers ---

def _sm_valid(key: str) -> bool:
  return key in ui_state.sm.valid and ui_state.sm.valid[key]

def _time_to_stop(distance: float, v_ego: float) -> str:
  if v_ego > MIN_SPEED_FOR_TIME:
    t = max(0.0, min(MAX_TIME_DISPLAY, TIME_FACTOR * distance / v_ego))
    return f"{t:.1f}"
  return "0.0"

def _calc_reduction(v_cruise: float, target: float) -> int:
  if v_cruise > 0.1 and target > 0.1 and target < v_cruise:
    return int(round((v_cruise - target) * _speed_conversion()))
  return 0

def _with_alpha(color: rl.Color, a: int) -> rl.Color:
  return rl.Color(color.r, color.g, color.b, max(0, min(255, a)))

def _pulse(freq: float) -> float:
  return 0.5 + 0.5 * math.sin(rl.get_time() * freq)

def _get_road_height(data: 'AetherGaugeData | None') -> float:
  is_curve = data.indicator_type == IndicatorType.ROAD_CURVE if data else False
  return ROAD_HEIGHT if is_curve else (45.0 * SCALE)

def _road_xy(distance: float, icx: float, bottom: float, data: 'AetherGaugeData') -> tuple[float, float, float]:
  t = max(0.0, min(1.0, _get_t_from_x(distance)))
  offset = _get_perspective_offset(t, data)
  return t, icx + offset, bottom - t * _get_road_height(data)

def _get_t_from_x(x: float) -> float:
  x_clamped = max(X_MIN, min(X_MAX, x))
  return (1.0 - X_MIN / x_clamped) / (1.0 - X_MIN / X_MAX)

def _get_perspective_offset(t: float, data: 'AetherGaugeData | None') -> float:
  curvature = 0.0
  if data and data.indicator_type == IndicatorType.ROAD_CURVE:
    curvature = data.indicator_value

  path_y_far = PATH_Y_FAR_SCALE * curvature
  max_offset_top = math.tanh(path_y_far * PERSPECTIVE_GAIN) * PERSPECTIVE_MAX_OFFSET
  return max_offset_top * (t ** PERSPECTIVE_EXPONENT)

def _draw_text_with_shadow(font: rl.Font, text: str, pos: rl.Vector2, size: int, color: rl.Color):
  for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
    rl.draw_text_ex(font, text, rl.Vector2(pos.x + dx, pos.y + dy), size, 0, rl.BLACK)
  rl.draw_text_ex(font, text, pos, size, 0, color)


# --- Data model ---

class IndicatorType(Enum):
  NONE = "none"
  ROAD_CURVE = "road_curve"
  FORCE_STOP = "force_stop"
  STOP_LIGHT = "stop_light"
  LEAD = "lead"


@dataclass
class AetherGaugeData:
  text: str
  unit: str = ""
  color: rl.Color = rl.WHITE
  indicator_type: IndicatorType = IndicatorType.NONE
  indicator_value: float = 0.0
  indicator_extra: str = ""
  reduction_text: str = ""
  is_numeric: bool = False


# --- Source functions (replaces class-based sources) ---

def _build_curve_gauge_data(curvature: float, target_speed: float, v_cruise: float) -> AetherGaugeData:
  v_ego = _get_val("carState", "vEgo", 0.0)
  display_speed, unit = _to_display_speed(min(v_ego, target_speed) if target_speed > 0.1 else v_ego)
  reduction = _calc_reduction(v_cruise, target_speed)
  intensity = _intensity(curvature)

  return AetherGaugeData(
    text=str(display_speed),
    unit=unit,
    color=_glow_color(intensity),
    indicator_type=IndicatorType.ROAD_CURVE,
    indicator_value=curvature,
    reduction_text=f"-{reduction}" if reduction > 0 else "",
    is_numeric=True,
  )


# --- Force stop ---

def _is_force_stop() -> bool:
  return _get_val("starpilotPlan", "forcingStop", False) and not _get_val("starpilotPlan", "redLight", False)

def _force_stop_data() -> AetherGaugeData:
  v_ego = _get_val("carState", "vEgo", 0.0)
  dist = _get_val("starpilotPlan", "forcingStopLength", 0.0)
  return AetherGaugeData(
    text=_time_to_stop(dist, v_ego), unit="s", color=COLOR_FORCE_STOP,
    indicator_type=IndicatorType.FORCE_STOP, indicator_value=dist, is_numeric=True,
  )


# --- CEM: Stop light / stop sign ---

def _is_stop_light() -> bool:
  return _get_val("starpilotPlan", "experimentalMode", False) and _get_val("starpilotPlan", "redLight", False)

def _stop_light_data() -> AetherGaugeData:
  dist = 0.0
  if _sm_valid("modelV2"):
    model = ui_state.sm["modelV2"]
    if len(model.position.x) > 0:
      dist = model.position.x[min(32, len(model.position.x) - 1)]
  if dist == 0.0:
    dist = _get_val("starpilotPlan", "forcingStopLength", 0.0)
  v_ego = _get_val("carState", "vEgo", 0.0)
  return AetherGaugeData(
    text=_time_to_stop(dist, v_ego), unit="s", color=COLOR_FORCE_STOP,
    indicator_type=IndicatorType.STOP_LIGHT, indicator_value=dist,
    indicator_extra="red", is_numeric=True,
  )


# --- Curve speed source (CSC active) ---

def _is_curve_speed() -> bool:
  state = _csc_state()
  return state is not None and state['active']

def _curve_speed_data() -> AetherGaugeData:
  state = _csc_state()
  if state is None:
    return AetherGaugeData(text="")
  csc_speed = _get_val("starpilotPlan", "cscSpeed", 0.0)
  v_cruise = _get_val("starpilotPlan", "vCruise", 0.0)
  return _build_curve_gauge_data(state['curvature'], csc_speed, v_cruise)


# --- CEM: Curvature (non-CSC) ---

def _is_curvature() -> bool:
  return _get_val("starpilotPlan", "experimentalMode", False) and abs(_get_val("starpilotPlan", "roadCurvature", 0.0)) > 0.0012

def _curvature_data() -> AetherGaugeData:
  csc_speed = _get_val("starpilotPlan", "cscSpeed", 0.0)
  v_ego = _get_val("carState", "vEgo", 0.0)
  v_cruise = _get_val("starpilotPlan", "vCruise", v_ego)
  target_speed = csc_speed if csc_speed > 0.1 else v_cruise
  road_curvature = _get_val("starpilotPlan", "roadCurvature", 0.0)
  return _build_curve_gauge_data(road_curvature, target_speed, v_cruise)


# --- CEM: Lead vehicle (graphic only, no numeric) ---

def _is_lead() -> bool:
  return (_get_val("starpilotPlan", "experimentalMode", False)
          and _get_val("starpilotPlan", "trackingLead", False)
          and _sm_valid("radarState")
          and ui_state.sm["radarState"].leadOne.status)

def _lead_data() -> AetherGaugeData:
  lead = ui_state.sm["radarState"].leadOne
  is_stopped = lead.vLead < LEAD_STOPPED_SPEED_THRESHOLD
  return AetherGaugeData(
    text="STOPPED" if is_stopped else "SLOW",
    color=COLOR_LEAD_STOPPED if is_stopped else COLOR_LEAD_SLOWER,
    indicator_type=IndicatorType.LEAD, indicator_value=lead.dRel,
    indicator_extra="stopped" if is_stopped else "slower",
  )








# --- Test cycle source (debug only, module-level state) ---

_TEST_STATES = [
  (IndicatorType.ROAD_CURVE, "45", rl.Color(0, 255, 100, 255), 0.005, "", "-20"),
  (IndicatorType.STOP_LIGHT, "", COLOR_FORCE_STOP, 35.0, "red", ""),
  (IndicatorType.LEAD, "", COLOR_LEAD_SLOWER, 25.0, "slower", ""),
  (IndicatorType.LEAD, "", COLOR_LEAD_SLOWER, 15.0, "stopped", ""),
  (IndicatorType.FORCE_STOP, "", COLOR_FORCE_STOP, 12.0, "", ""),
]
_TEST_CYCLE_SEC = 6.0

def _test_cycle_active() -> bool:
  return rl.get_time() > 3.0

def _test_cycle_data() -> AetherGaugeData:
  now = rl.get_time()
  elapsed = (now - 3.0) % _TEST_CYCLE_SEC
  idx = int((now - 3.0) / _TEST_CYCLE_SEC) % len(_TEST_STATES)
  ind_type, text, color, base_val, extra, reduction = _TEST_STATES[idx]
  anim_t = elapsed / max(0.001, _TEST_CYCLE_SEC - 0.5)

  if ind_type in (IndicatorType.STOP_LIGHT, IndicatorType.FORCE_STOP):
    ind_val = max(5.0, 60.0 - anim_t * 55.0)
    text = f"{max(0.0, (_TEST_CYCLE_SEC - 0.5) - elapsed):.1f}"
    return AetherGaugeData(text=text, unit="s", color=color,
      indicator_type=ind_type, indicator_value=ind_val,
      indicator_extra=extra, reduction_text=reduction, is_numeric=True)

  if ind_type == IndicatorType.LEAD:
    ind_val = max(3.0, 60.0 - anim_t * 57.0)
    is_stopped = extra == "stopped"
    text = "STOPPED" if is_stopped else "SLOW"
    color = COLOR_LEAD_STOPPED if is_stopped else COLOR_LEAD_SLOWER
    return AetherGaugeData(text=text, color=color,
      indicator_type=ind_type, indicator_value=ind_val,
      indicator_extra=extra, reduction_text=reduction)

  return AetherGaugeData(text=text, unit=_speed_unit(), color=color,
    indicator_type=ind_type, indicator_value=base_val,
    indicator_extra=extra, reduction_text=reduction, is_numeric=True)


# --- Main widget ---

class AetherGauge:
  def __init__(self):
    self._sources = [
      (_is_force_stop, _force_stop_data),
      (_is_stop_light, _stop_light_data),
      (_is_curve_speed, _curve_speed_data),
      (_is_curvature, _curvature_data),
      (_is_lead, _lead_data),
    ]
    if TEST_CYCLE:
      self._sources.insert(0, (_test_cycle_active, _test_cycle_data))
    self._chevron_accum = 0.0
    self._lead_chevron_accum = 0.0

  def get_active_data(self) -> AetherGaugeData | None:
    for is_active, get_data in self._sources:
      if is_active():
        return get_data()
    return None

  def render(self, rect: rl.Rectangle, font_bold: rl.Font, font_medium: rl.Font, current_speed: float, cx: float | None = None, bottom: float | None = None):
    data = self.get_active_data()
    if not data:
      return

    if cx is None or bottom is None:
      base_cx = rect.x + rect.width / 2
      cy_speed = rect.y + 180 * SCALE
      speed_text = str(round(current_speed))
      speed_text_size = measure_text_cached(font_bold, speed_text, int(176 * SCALE))
      icx = base_cx - speed_text_size.x / 2 - 70.0 * SCALE
      icy = cy_speed - 39.5 * SCALE
    else:
      icx = cx
      icy = bottom - ROAD_HALF_SIZE

    if data.indicator_type in (IndicatorType.ROAD_CURVE, IndicatorType.FORCE_STOP, IndicatorType.LEAD, IndicatorType.STOP_LIGHT):
      self._render_unified_road(rect, icx, icy, data, font_bold, font_medium)

  def _render_unified_road(self, rect, icx, icy, data, font_bold, font_medium):
    bottom = icy + ROAD_HALF_SIZE

    if data.indicator_type in (IndicatorType.FORCE_STOP, IndicatorType.STOP_LIGHT):
      distance = 15.0
    else:
      distance = data.indicator_value

    points_left = []
    points_right = []
    road_h = _get_road_height(data)

    for i in range(ROAD_SEGMENTS + 1):
      t = i / ROAD_SEGMENTS
      offset = _get_perspective_offset(t, data)
      cx_t = icx + offset
      y_t = bottom - t * road_h
      w_t = ROAD_W_BOTTOM - t * (ROAD_W_BOTTOM - ROAD_W_TOP)

      points_left.append(rl.Vector2(cx_t - w_t, y_t))
      points_right.append(rl.Vector2(cx_t + w_t, y_t))

    fill_color = _with_alpha(data.color, FILL_ALPHA)
    for i in range(ROAD_SEGMENTS):
      rl.draw_triangle(points_left[i], points_right[i], points_left[i+1], fill_color)
      rl.draw_triangle(points_right[i], points_right[i+1], points_left[i+1], fill_color)
      rl.draw_line_ex(points_left[i], points_left[i+1], ROAD_THICKNESS, COLOR_SHADOW)
      rl.draw_line_ex(points_right[i], points_right[i+1], ROAD_THICKNESS, COLOR_SHADOW)
      rl.draw_line_ex(points_left[i], points_left[i+1], ROAD_THICKNESS, data.color)
      rl.draw_line_ex(points_right[i], points_right[i+1], ROAD_THICKNESS, data.color)

    it = data.indicator_type

    if it in (IndicatorType.STOP_LIGHT, IndicatorType.FORCE_STOP):
      self._draw_stop_line(icx, bottom, distance, data)

    if it == IndicatorType.LEAD:
      self._draw_lead_car(icx, bottom, data)

    if it in (IndicatorType.ROAD_CURVE, IndicatorType.FORCE_STOP, IndicatorType.STOP_LIGHT):
      self._draw_standard_chevrons(icx, bottom, distance, data)

    if it == IndicatorType.STOP_LIGHT:
      self._draw_traffic_light(icx, icy, distance, data)

    if it == IndicatorType.FORCE_STOP:
      self._draw_approaching_stop_sign(icx, icy, bottom, distance, data, font_bold)

    self._draw_mini_cradle(icx, bottom, data, font_bold, font_medium)

  def _draw_stop_line(self, icx, bottom, distance, data):
    t, cx_line, cy_line = _road_xy(distance, icx, bottom, data)
    w_line = ROAD_W_BOTTOM - t * (ROAD_W_BOTTOM - ROAD_W_TOP)

    p_left = rl.Vector2(cx_line - w_line + ROAD_EDGE_INSET, cy_line)
    p_right = rl.Vector2(cx_line + w_line - ROAD_EDGE_INSET, cy_line)

    fade = 1.0 - t * 0.5
    glow_a = int(150 * fade)

    rl.draw_line_ex(p_left, p_right, max(3.0 * SCALE, 7.0 * SCALE * fade), _with_alpha(COLOR_STOP_LINE_GLOW, glow_a))
    rl.draw_line_ex(p_left, p_right, max(1.5 * SCALE, 3.5 * SCALE * fade), COLOR_STOP_LINE_CORE)

  def _draw_lead_car(self, icx, bottom, data):
    t_lead, cx_lead, cy_lead = _road_xy(6.5, icx, bottom, data)
    t_lead = max(0.15, min(0.85, t_lead))

    car_scale = 0.45 + (1.0 - t_lead) * 0.55
    W = 30.0 * SCALE * car_scale
    H = 18.0 * SCALE * car_scale

    is_stopped = data.indicator_extra == "stopped"
    is_slower = data.indicator_extra == "slower"

    if is_stopped:
      border_color = COLOR_LEAD_STOPPED
    elif is_slower:
      border_color = _with_alpha(data.color, int(160 + 95 * _pulse(1.2)))
    else:
      border_color = data.color

    # Car body: cabin and main body
    for rect_args, corner_r, fill in [
      ((cx_lead - W * 0.3, cy_lead - H, W * 0.6, H * 0.45), 0.5, rl.Color(15, 15, 15, 240)),
      ((cx_lead - W / 2, cy_lead - H * 0.65, W, H * 0.55), 0.3, rl.Color(20, 20, 20, 240)),
    ]:
      r = rl.Rectangle(*rect_args)
      rl.draw_rectangle_rounded(r, corner_r, 4, fill)
      rl.draw_rectangle_rounded_lines_ex(r, corner_r, 4, 1.5, border_color)

    # Tail lights with glow
    tl_w = W * 0.15
    tl_h = H * 0.12
    tl_y = int(cy_lead - H * 0.55)
    glow_y = int(cy_lead - H * 0.5)
    for tl_x, glow_x in [(int(cx_lead - W * 0.45), int(cx_lead - W * 0.38)),
                          (int(cx_lead + W * 0.3), int(cx_lead + W * 0.38))]:
      if is_stopped:
        pulse = _pulse(2.5)
        r_glow = int(W * 0.08 * (1.0 + 0.4 * pulse))
        rl.draw_circle(glow_x, glow_y, r_glow, rl.Color(255, 30, 60, int(150 + 105 * pulse)))
        c_tl = rl.Color(255, 220, 220, 255)
      elif is_slower:
        pulse = _pulse(1.2)
        r_glow = int(W * 0.06 * (1.0 + 0.2 * pulse))
        rl.draw_circle(glow_x, glow_y, r_glow, rl.Color(255, 140, 30, int(100 + 80 * pulse)))
        c_tl = rl.Color(255, 160, 60, int(180 + 75 * pulse))
      else:
        c_tl = COLOR_FORCE_STOP
      rl.draw_rectangle(tl_x, tl_y, int(tl_w), int(tl_h), c_tl)

    # Wheels
    wheel_y = int(cy_lead - H * 0.1)
    wheel_w = int(W * 0.12)
    wheel_h = int(H * 0.1)
    wheel_c = rl.Color(10, 10, 10, 255)
    rl.draw_rectangle(int(cx_lead - W * 0.4), wheel_y, wheel_w, wheel_h, wheel_c)
    rl.draw_rectangle(int(cx_lead + W * 0.28), wheel_y, wheel_w, wheel_h, wheel_c)

    # Following chevrons (from lead car back toward viewer)
    dt = rl.get_frame_time()
    v_ego = _get_val("carState", "vEgo", 0.0)
    flow_speed_factor = min(1.8, v_ego * 0.08)
    self._lead_chevron_accum = (self._lead_chevron_accum + dt * flow_speed_factor * 1.8) % 1.0
    progress = self._lead_chevron_accum
    for i in range(2):
      t = t_lead * (1.0 - ((i + progress) / 2) % 1.0)

      cx_t = icx + _get_perspective_offset(t, data)
      road_h = _get_road_height(data)
      cy_t = bottom - t * road_h

      chevron_w = 12.0 * SCALE - t * 5.0 * SCALE
      chevron_thick = max(1.5 * SCALE, 3.5 * SCALE - t * 1.5 * SCALE)
      lx = cx_t - chevron_w
      rx = cx_t + chevron_w

      alpha = max(0, min(255, int(data.color.a * (1.0 - t / t_lead) * math.sin(t / t_lead * math.pi))))
      c_color = _with_alpha(data.color, alpha)

      rl.draw_line_ex(rl.Vector2(lx, cy_t - chevron_w * 0.5), rl.Vector2(cx_t, cy_t), chevron_thick, c_color)
      rl.draw_line_ex(rl.Vector2(rx, cy_t - chevron_w * 0.5), rl.Vector2(cx_t, cy_t), chevron_thick, c_color)

  def _draw_standard_chevrons(self, icx, bottom, distance, data):
    is_stop = data.indicator_type in (IndicatorType.FORCE_STOP, IndicatorType.STOP_LIGHT)
    dt = rl.get_frame_time()
    v_ego = _get_val("carState", "vEgo", 0.0)
    flow_speed_factor = min(1.5, v_ego * 0.08)
    self._chevron_accum = (self._chevron_accum + dt * flow_speed_factor * 1.5) % 1.0
    progress = self._chevron_accum
    t_stop = max(0.05, min(1.0, distance / STOP_DISTANCE_MAX)) if is_stop else 1.0
    max_t = t_stop if is_stop else 1.0

    for i in range(CHEVRON_COUNT):
      t = max_t - (i + progress) * CHEVRON_SPACING
      if t < 0.0 or t > max_t:
        continue

      t_next = min(max_t, t + CHEVRON_STEP)
      cx_t = icx + _get_perspective_offset(t, data)
      cx_next = icx + _get_perspective_offset(t_next, data)

      road_h = _get_road_height(data)
      cy_t = bottom - t * road_h
      cy_next = bottom - t_next * road_h

      dx = cx_next - cx_t
      dy = cy_next - cy_t
      len_v = math.hypot(dx, dy)
      dir_up_x, dir_up_y = (dx / len_v, dy / len_v) if len_v > 0.001 else (0.0, -1.0)

      dir_right_x = -dir_up_y
      dir_right_y = dir_up_x

      chevron_w = max(2.0 * SCALE, 14.0 * SCALE - t * 6.0 * SCALE)
      chevron_h = chevron_w * 0.6
      chevron_thick = max(2.0 * SCALE, 4.0 * SCALE - t * 2.0 * SCALE)

      lx = cx_t - dir_right_x * chevron_w + dir_up_x * chevron_h
      ly = cy_t - dir_right_y * chevron_w + dir_up_y * chevron_h
      rx = cx_t + dir_right_x * chevron_w + dir_up_x * chevron_h
      ry = cy_t + dir_right_y * chevron_w + dir_up_y * chevron_h

      alpha_factor = math.sin((t / max_t) * math.pi) if max_t > 0.01 else 0.0
      alpha = max(0, min(255, int(data.color.a * alpha_factor)))
      chev_color = _with_alpha(data.color, alpha)
      chev_shadow = rl.Color(0, 0, 0, int(alpha * 0.5))

      rl.draw_line_ex(rl.Vector2(lx, ly + 1.5), rl.Vector2(cx_t, cy_t + 1.5), chevron_thick, chev_shadow)
      rl.draw_line_ex(rl.Vector2(rx, ry + 1.5), rl.Vector2(cx_t, cy_t + 1.5), chevron_thick, chev_shadow)
      rl.draw_line_ex(rl.Vector2(lx, ly), rl.Vector2(cx_t, cy_t), chevron_thick, chev_color)
      rl.draw_line_ex(rl.Vector2(rx, ry), rl.Vector2(cx_t, cy_t), chevron_thick, chev_color)

  def _draw_traffic_light(self, icx, icy, distance, data):
    t_light, cx_light, cy_road = _road_xy(distance, icx, icy + ROAD_HALF_SIZE, data)
    s_light = 1.0 - t_light

    scale_light = 0.6 + (s_light ** 2.0) * 1.4
    cy_light = cy_road - 35.0 * SCALE * s_light
    width = 11.0 * SCALE * scale_light
    height = 27.0 * SCALE * scale_light

    rl.draw_rectangle_rounded(rl.Rectangle(cx_light - width/2, cy_light - height/2 + 1.5, width, height), 0.2, 4, rl.Color(0, 0, 0, 120))
    rect_housing = rl.Rectangle(cx_light - width/2, cy_light - height/2, width, height)
    rl.draw_rectangle_rounded(rect_housing, 0.2, 4, rl.Color(22, 22, 22, 255))
    rl.draw_rectangle_rounded_lines_ex(rect_housing, 0.2, 4, 1.0, rl.Color(80, 80, 80, 255))

    r_bulb = 2.2 * SCALE * scale_light
    active_light = data.indicator_extra if data.indicator_extra in ("red", "yellow", "green") else "red"

    bulbs = [
      (cy_light - 7.5 * SCALE * scale_light, "red", rl.Color(255, 30, 60, 255), rl.Color(50, 10, 15, 255)),
      (cy_light, "yellow", rl.Color(255, 200, 0, 255), rl.Color(50, 40, 0, 255)),
      (cy_light + 7.5 * SCALE * scale_light, "green", rl.Color(0, 255, 100, 255), rl.Color(0, 40, 15, 255)),
    ]
    for y, name, active_c, inactive_c in bulbs:
      if name == "red" and active_light == "red":
        glow_pulse = _pulse(1.5)
        rl.draw_circle_v(rl.Vector2(cx_light, y), r_bulb + 3.0 * SCALE * glow_pulse, rl.Color(255, 30, 60, 45))
        rl.draw_circle_v(rl.Vector2(cx_light, y), r_bulb + 6.0 * SCALE * glow_pulse, rl.Color(255, 30, 60, 15))
      c = active_c if active_light == name else inactive_c
      rl.draw_circle_v(rl.Vector2(cx_light, y), r_bulb, c)

  def _draw_approaching_stop_sign(self, cx, icy, bottom, smoothed_distance, data, font_bold):
    t_stop_gauge = _get_t_from_x(smoothed_distance)
    smoothed_s = max(0.0, min(1.0, 1.0 - (smoothed_distance / STOP_DISTANCE_MAX)))

    offset_stop = _get_perspective_offset(t_stop_gauge, data) if data else 0.0
    cx_stop = cx + offset_stop

    road_h = _get_road_height(data)
    cy_road = bottom - t_stop_gauge * road_h
    y_sign = cy_road - 25.0 * SCALE * smoothed_s

    r_min = 6.0 * SCALE
    r_max = 20.0 * SCALE
    r_sign = r_min + (smoothed_s ** 2.0) * (r_max - r_min)

    shadow_alpha = int(min(120, r_sign * 12))
    rl.draw_poly(rl.Vector2(cx_stop, y_sign + 2.0), 8, r_sign, 22.5, rl.Color(0, 0, 0, shadow_alpha))
    rl.draw_poly(rl.Vector2(cx_stop, y_sign), 8, r_sign, 22.5, COLOR_STOP_SIGN)

    outline_t = max(0.8, min(1.5, r_sign * 0.07))
    outline_a = int(max(0, min(200, (r_sign - 5.0) * 20)))
    if outline_a > 20:
      for i in range(8):
        a1 = math.radians(22.5 + i * 45.0)
        a2 = math.radians(22.5 + ((i + 1) % 8) * 45.0)
        p1 = rl.Vector2(cx_stop + r_sign * math.cos(a1), y_sign + r_sign * math.sin(a1))
        p2 = rl.Vector2(cx_stop + r_sign * math.cos(a2), y_sign + r_sign * math.sin(a2))
        rl.draw_line_ex(p1, p2, outline_t, _with_alpha(COLOR_STOP_SIGN_OUTLINE, outline_a))

    stop_font_size = max(4, int(r_sign * 0.7))
    stop_txt_size = measure_text_cached(font_bold, "STOP", stop_font_size)
    rl.draw_text_ex(font_bold, "STOP", rl.Vector2(cx_stop - stop_txt_size.x / 2, y_sign - stop_txt_size.y / 2), stop_font_size, 0, rl.WHITE)

  def _draw_mini_cradle(self, cx, bottom, data, font_bold, font_medium):
    if not data.text:
      return

    if data.is_numeric:
      val_size = measure_text_cached(font_bold, data.text, int(48 * SCALE))
      val_pos = rl.Vector2(int(cx - val_size.x / 2), int(bottom + 12 * SCALE))
      _draw_text_with_shadow(font_bold, data.text, val_pos, int(48 * SCALE), data.color)

      if data.reduction_text:
        red_size = measure_text_cached(font_medium, data.reduction_text, int(20 * SCALE))
        red_pos = rl.Vector2(int(cx + val_size.x / 2 + 8 * SCALE), int(bottom + 12 * SCALE + val_size.y / 2 - red_size.y / 2))
        _draw_text_with_shadow(font_medium, data.reduction_text, red_pos, int(20 * SCALE), rl.Color(255, 255, 255, 160))

      if data.unit:
        unit_size = measure_text_cached(font_medium, data.unit, int(16 * SCALE))
        unit_pos = rl.Vector2(int(cx - unit_size.x / 2), int(bottom + 12 * SCALE + val_size.y + 4 * SCALE))
        _draw_text_with_shadow(font_medium, data.unit, unit_pos, int(16 * SCALE), rl.Color(255, 255, 255, 160))
    else:
      val_size = measure_text_cached(font_bold, data.text, int(24 * SCALE))
      val_pos = rl.Vector2(int(cx - val_size.x / 2), int(bottom + 16 * SCALE))
      _draw_text_with_shadow(font_bold, data.text, val_pos, int(24 * SCALE), data.color)
