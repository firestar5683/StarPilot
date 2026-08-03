import pyray as rl
import time
import re
import json
from cereal import car
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight, FONT_SCALE
from openpilot.system.ui.lib.text_measure import measure_text_cached

SIDEBAR_WIDTH = 300
METRIC_HEIGHT = 126
METRIC_WIDTH = 275
METRIC_MARGIN = 12
FONT_SIZE = 35
METER_TO_FOOT = 3.28084
_WHITE_DIM = rl.Color(255, 255, 255, 85)
_LOCKED_VALUE_COLOR = rl.Color(34, 197, 94, 255)
_AUTO_TUNE_COLOR = rl.Color(59, 130, 246, 255)
_FLM_OVERRIDE_COLOR = rl.Color(239, 68, 68, 255)

def parse_hex_color(hex_str: str, default_color=rl.WHITE) -> rl.Color:
  if not hex_str:
    return default_color
  hex_str = hex_str.lstrip('#')
  try:
    if len(hex_str) == 6:
      r = int(hex_str[0:2], 16)
      g = int(hex_str[2:4], 16)
      b = int(hex_str[4:6], 16)
      return rl.Color(r, g, b, 255)
    elif len(hex_str) == 8:
      r = int(hex_str[0:2], 16)
      g = int(hex_str[2:4], 16)
      b = int(hex_str[4:6], 16)
      a = int(hex_str[6:8], 16)
      return rl.Color(r, g, b, a)
  except ValueError:
    pass
  return default_color


def resolve_effective_torque_value(custom_enabled: bool, custom_value: float,
                                   live_enabled: bool, live_value: float,
                                   stock_value: float, configured_value: float) -> float:
  """Mirror controlsd torque-param precedence for the onroad diagnostics."""
  if custom_enabled:
    return custom_value
  if live_enabled:
    return live_value
  return stock_value if stock_value != 0.0 else configured_value


def _safe_float(value, default: float = 0.0) -> float:
  try:
    return float(value)
  except (TypeError, ValueError):
    return default


def _setting_changed(value: float, reference: float) -> bool:
  return round(value, 2) != round(reference, 2)


class DeveloperSidebar:
  def __init__(self):
    self._params = ui_state.ui_params
    self._font_bold = gui_app.font(FontWeight.SEMI_BOLD)
    self._last_toggles_check = 0.0
    self._cached_metrics = [0] * 7
    self._cached_force_auto_tune_off = False
    self._cached_force_auto_tune = False
    self._cached_flm_trial_applied = False
    self._cached_use_auto_steer_delay = True
    self._cached_delay_stock = 0.0
    self._cached_delay = 0.0
    self._cached_friction_stock = 0.0
    self._cached_friction = 0.0
    self._cached_lat_stock = 0.0
    self._cached_lat = 0.0
    self._cached_ratio_stock = 0.0
    self._cached_ratio = 0.0
    self._flm_generic_param_keys: set[str] = set()

    self.lateral_engagement_time = 0
    self.longitudinal_engagement_time = 0
    self.total_engagement_time = 0
    self.max_acceleration = 0.0
    self.max_steer_angle = 0
    self.max_torque = 0
    self.torque_timer_start = 0.0

    self._visible = False
    self._metric_color = rl.WHITE
    self._active_ids: list[int] = []
    self._metric_colors: dict[int, rl.Color] = {}
    self._metrics: dict[int, tuple[str, str]] = {}

  @property
  def visible(self) -> bool:
    return self._visible

  def reset_variables(self):
    self.lateral_engagement_time = 0
    self.longitudinal_engagement_time = 0
    self.total_engagement_time = 0
    self.max_acceleration = 0.0
    self.max_steer_angle = 0
    self.max_torque = 0
    self.torque_timer_start = 0.0

  def _refresh_cache(self):
    now = time.monotonic()
    if now - self._last_toggles_check < 1.0:
      return
    self._last_toggles_check = now
    self._cached_metrics = [self._params.get_int(f"DeveloperSidebarMetric{i}") for i in range(1, 8)]
    self._cached_force_auto_tune_off = self._params.get_bool("ForceAutoTuneOff")
    self._cached_force_auto_tune = self._params.get_bool("ForceAutoTune")
    self._cached_flm_trial_applied = self._params.get_bool("FLMTrialApplied")
    self._cached_use_auto_steer_delay = self._params.get_bool("UseAutoSteerDelay", default=True)
    self._cached_delay_stock = self._params.get_float("SteerDelayStock")
    self._cached_delay = self._params.get_float("SteerDelay")
    self._cached_friction_stock = self._params.get_float("SteerFrictionStock")
    self._cached_friction = self._params.get_float("SteerFriction")
    self._cached_lat_stock = self._params.get_float("SteerLatAccelStock")
    self._cached_lat = self._params.get_float("SteerLatAccel")
    self._cached_ratio_stock = self._params.get_float("SteerRatioStock")
    self._cached_ratio = self._params.get_float("SteerRatio")
    self._flm_generic_param_keys = self._read_flm_generic_param_keys() if self._cached_flm_trial_applied else set()

  def _read_flm_generic_param_keys(self) -> set[str]:
    try:
      raw = self._params.get("FLMTrialBaseline", encoding="utf-8") or "{}"
      snapshot = raw if isinstance(raw, dict) else json.loads(raw)
      applied = snapshot.get("appliedGenericParams", {}) if isinstance(snapshot, dict) else {}
      return set(applied.keys()) if isinstance(applied, dict) else set()
    except Exception:
      return set()

  @staticmethod
  def _toggle_bool(toggles: dict, key: str, fallback: bool = False) -> bool:
    return bool(toggles[key]) if key in toggles else fallback

  @staticmethod
  def _toggle_float(toggles: dict, key: str, fallback: float = 0.0) -> float:
    return _safe_float(toggles.get(key, fallback), fallback)

  def _flm_changed(self, *keys: str) -> bool:
    return self._cached_flm_trial_applied and any(key in self._flm_generic_param_keys for key in keys)

  def _tuning_color(self, *, auto: bool = False, flm: bool = False) -> rl.Color:
    if flm:
      return _FLM_OVERRIDE_COLOR
    return _AUTO_TUNE_COLOR if auto else _LOCKED_VALUE_COLOR

  def _draw_metric(self, sidebar_rect: rl.Rectangle, label_first: str, label_second: str, color: rl.Color, y: float):
    card_x = int(sidebar_rect.x + sidebar_rect.width) - METRIC_MARGIN - METRIC_WIDTH
    metric_rect = rl.Rectangle(card_x, y, METRIC_WIDTH, METRIC_HEIGHT)

    edge_rect = rl.Rectangle(metric_rect.x + METRIC_WIDTH - 4 - 100, metric_rect.y + 4, 100, 118)
    rl.begin_scissor_mode(
      int(metric_rect.x + METRIC_WIDTH - 4 - 18),
      int(metric_rect.y),
      18,
      int(metric_rect.height)
    )
    rl.draw_rectangle_rounded(edge_rect, 0.3, 10, color)
    rl.end_scissor_mode()

    rl.draw_rectangle_rounded_lines_ex(metric_rect, 0.3, 10, 2, _WHITE_DIM)

    if label_second == "":
      text_size = measure_text_cached(self._font_bold, label_first, FONT_SIZE)
      text_pos = rl.Vector2(
        metric_rect.x + (metric_rect.width - 22 - text_size.x) / 2,
        metric_rect.y + (metric_rect.height - text_size.y) / 2
      )
      rl.draw_text_ex(self._font_bold, label_first, text_pos, FONT_SIZE, 0, rl.WHITE)
    else:
      labels = [label_first, label_second]
      text_y = metric_rect.y + (metric_rect.height / 2 - len(labels) * FONT_SIZE * FONT_SCALE)
      for text in labels:
        text_size = measure_text_cached(self._font_bold, text, FONT_SIZE)
        text_y += text_size.y
        text_pos = rl.Vector2(
          metric_rect.x + (metric_rect.width - 22 - text_size.x) / 2,
          text_y
        )
        rl.draw_text_ex(self._font_bold, text, text_pos, FONT_SIZE, 0, rl.WHITE)

  def update(self):
    self._refresh_cache()

    # ---- PC REPLAY FALLBACK (remove the next line when replay gets toggle bridge) ----
    # self._visible = ui_state.starpilot_toggles.get("developer_sidebar", False)
    # ---- replace the line below with the one above ---->
    self._visible = self._params.get_bool("DeveloperSidebar") or ui_state.starpilot_toggles.get("developer_sidebar", False)
    if not self._visible:
      return

    if ui_state.sm.frame < ui_state.started_frame + 2:
      self.reset_variables()

    assignments = []
    for i, val in enumerate(self._cached_metrics):
      if val == 0:
        val = ui_state.starpilot_toggles.get(f"developer_sidebar_metric{i + 1}", 0)
      assignments.append(val)

    color_str = ui_state.starpilot_toggles.get("sidebar_color1", "#FFFFFFFF")
    self._metric_color = parse_hex_color(color_str)

    self._active_ids = [m for m in assignments if m > 0]
    if len(self._active_ids) == 0:
      return

    sm = ui_state.sm
    car_state = sm["carState"] if sm.valid.get("carState", False) else None
    car_control = sm["carControl"] if sm.valid.get("carControl", False) else None
    starpilot_plan = sm["starpilotPlan"] if sm.valid.get("starpilotPlan", False) else None
    live_delay = sm["liveDelay"] if sm.valid.get("liveDelay", False) else None
    live_parameters = sm["liveParameters"] if sm.valid.get("liveParameters", False) else None
    live_torque_parameters = sm["liveTorqueParameters"] if sm.valid.get("liveTorqueParameters", False) else None

    is_metric = ui_state.is_metric
    use_si = ui_state.starpilot_toggles.get("use_si_metrics", False)
    accel_unit = " m/s²" if (is_metric or use_si) else " ft/s²"
    accel_conv = 1.0 if (is_metric or use_si) else METER_TO_FOOT

    a_ego = car_state.aEgo if car_state else 0.0
    accel_val = a_ego * accel_conv
    gas_pressed = car_state.gasPressed if car_state else False
    if not gas_pressed:
      self.max_acceleration = max(self.max_acceleration, accel_val)

    lat_active = car_control.latActive if car_control else False
    long_active = car_control.longActive if car_control else False
    standstill = car_state.standstill if car_state else False
    reverse = car_state.gearShifter == car.CarState.GearShifter.reverse if car_state else False

    self.lateral_engagement_time += 1 if (lat_active and not standstill and not reverse) else 0
    self.longitudinal_engagement_time += 1 if (long_active and not standstill and not reverse) else 0
    self.total_engagement_time += 1 if ((not standstill and not reverse) or self.total_engagement_time == 0) else 0

    curr_steer = int(abs(car_state.steeringAngleDeg)) if car_state else 0
    curr_torque = int(abs(car_control.actuators.torque * 100)) if (car_control and hasattr(car_control.actuators, 'torque')) else 0

    now = time.monotonic()
    if curr_torque >= 50:
      self.max_steer_angle = max(self.max_steer_angle, curr_steer)
      self.max_torque = max(self.max_torque, curr_torque)
      self.torque_timer_start = now
    elif self.torque_timer_start > 0.0 and (now - self.torque_timer_start >= 10.0):
      self.max_torque = 0
      self.max_steer_angle = 0
      self.torque_timer_start = 0.0

    steer_label = f"{curr_steer}°"
    torque_label = f"{curr_torque}%"
    if curr_torque >= 50 or self.torque_timer_start > 0.0:
      steer_label += f" - ({self.max_steer_angle}°)"
      torque_label += f" - ({self.max_torque}%)"

    toggles = ui_state.starpilot_toggles
    force_auto_tune_off = self._toggle_bool(toggles, "force_auto_tune_off", self._cached_force_auto_tune_off)
    force_auto_tune = self._toggle_bool(toggles, "force_auto_tune", self._cached_force_auto_tune)
    use_params = live_torque_parameters.useParams if (live_torque_parameters and hasattr(live_torque_parameters, 'useParams')) else False
    using_live_torque = live_torque_parameters is not None and not force_auto_tune_off and (use_params or force_auto_tune)
    live_friction = live_torque_parameters.frictionCoefficientFiltered if (live_torque_parameters and hasattr(live_torque_parameters, 'frictionCoefficientFiltered')) else 0.0
    live_lat_factor = live_torque_parameters.latAccelFactorFiltered if (live_torque_parameters and hasattr(live_torque_parameters, 'latAccelFactorFiltered')) else 0.0
    custom_friction = self._toggle_float(toggles, "friction", self._cached_friction)
    custom_lat_factor = self._toggle_float(toggles, "latAccelFactor", self._cached_lat)
    fallback_use_custom_friction = force_auto_tune_off or (_setting_changed(self._cached_friction, self._cached_friction_stock) and not force_auto_tune)
    fallback_use_custom_lat_factor = force_auto_tune_off or (_setting_changed(self._cached_lat, self._cached_lat_stock) and not force_auto_tune)
    use_custom_friction = self._toggle_bool(toggles, "use_custom_friction", fallback_use_custom_friction)
    use_custom_lat_factor = self._toggle_bool(toggles, "use_custom_latAccelFactor", fallback_use_custom_lat_factor)

    friction_coeff = resolve_effective_torque_value(
      use_custom_friction,
      custom_friction,
      using_live_torque,
      live_friction,
      self._cached_friction_stock,
      self._cached_friction,
    )
    lat_factor = resolve_effective_torque_value(
      use_custom_lat_factor,
      custom_lat_factor,
      using_live_torque,
      live_lat_factor,
      self._cached_lat_stock,
      self._cached_lat,
    )

    use_auto_steer_delay = self._toggle_bool(toggles, "use_auto_steer_delay", self._cached_use_auto_steer_delay)
    use_custom_delay = self._toggle_bool(toggles, "use_custom_steerActuatorDelay", not use_auto_steer_delay)
    custom_delay = self._toggle_float(toggles, "steerActuatorDelay", self._cached_delay)
    if use_custom_delay:
      lat_delay = custom_delay
    elif live_delay:
      lat_delay = live_delay.lateralDelay
    else:
      lat_delay = self._cached_delay_stock if self._cached_delay_stock != 0.0 else self._cached_delay

    tot_time = max(1, self.total_engagement_time)
    lat_pct = (self.lateral_engagement_time / tot_time) * 100.0
    long_pct = (self.longitudinal_engagement_time / tot_time) * 100.0

    accel_jerk = starpilot_plan.accelerationJerk if starpilot_plan else 0.0
    act_accel = (car_control.actuators.accel if (car_control and hasattr(car_control.actuators, 'accel')) else 0.0) * accel_conv
    danger_factor = (starpilot_plan.dangerFactor if starpilot_plan else 0.0) * 100.0
    danger_jerk = starpilot_plan.dangerJerk if starpilot_plan else 0.0
    speed_jerk = starpilot_plan.speedJerk if starpilot_plan else 0.0

    fallback_use_custom_steer_ratio = force_auto_tune_off or (_setting_changed(self._cached_ratio, self._cached_ratio_stock) and not force_auto_tune)
    use_custom_steer_ratio = self._toggle_bool(toggles, "use_custom_steerRatio", fallback_use_custom_steer_ratio)
    custom_steer_ratio = self._toggle_float(toggles, "steerRatio", self._cached_ratio)
    if use_custom_steer_ratio:
      steer_ratio = custom_steer_ratio
    elif live_parameters:
      steer_ratio = live_parameters.steerRatio
    else:
      steer_ratio = self._cached_ratio_stock if self._cached_ratio_stock != 0.0 else self._cached_ratio
    stiff_factor = 1.0 if force_auto_tune_off else (live_parameters.stiffnessFactor if live_parameters else 1.0)

    force_auto_tune_flm = self._flm_changed("ForceAutoTune", "ForceAutoTuneOff")
    self._metric_colors = {
      3: self._tuning_color(
        auto=not use_custom_delay and live_delay is not None,
        flm=self._flm_changed("SteerDelay", "UseAutoSteerDelay"),
      ),
      4: self._tuning_color(
        auto=using_live_torque and not use_custom_friction,
        flm=self._flm_changed("SteerFriction") or (force_auto_tune_flm and (using_live_torque or use_custom_friction)),
      ),
      5: self._tuning_color(
        auto=using_live_torque and not use_custom_lat_factor,
        flm=self._flm_changed("SteerLatAccel") or (force_auto_tune_flm and (using_live_torque or use_custom_lat_factor)),
      ),
      6: self._tuning_color(
        auto=live_parameters is not None and not use_custom_steer_ratio,
        flm=self._flm_changed("SteerRatio") or (force_auto_tune_flm and use_custom_steer_ratio),
      ),
      7: self._tuning_color(
        auto=live_parameters is not None and not force_auto_tune_off,
        flm=force_auto_tune_flm and force_auto_tune_off,
      ),
    }

    model_name = ui_state.starpilot_toggles.get("model_name", "N/A")
    model_name = re.sub(r'\(.*\)', '', model_name)
    model_name = re.sub(r'[^a-zA-Z0-9 \-\.:]', '', model_name).strip()

    self._metrics = {
      1: ("ACCEL", f"{accel_val:.2f}{accel_unit}"),
      2: ("MAX ACCEL", f"{self.max_acceleration:.2f}{accel_unit}"),
      3: ("STEER DELAY", f"{lat_delay:.5f}"),
      4: ("FRICTION", f"{friction_coeff:.5f}"),
      5: ("LAT ACCEL", f"{lat_factor:.5f}"),
      6: ("STEER RATIO", f"{steer_ratio:.5f}"),
      7: ("STEER STIFF", f"{stiff_factor:.5f}"),
      8: ("LATERAL %", f"{lat_pct:.2f}%"),
      9: ("LONG %", f"{long_pct:.2f}%"),
      10: ("STEER ANGLE", steer_label),
      11: ("TORQUE %", torque_label),
      12: ("ACT ACCEL", f"{act_accel:.2f}{accel_unit}"),
      13: ("DANGER %", f"{danger_factor:.2f}%"),
      14: ("ACCEL JERK", f"{accel_jerk}"),
      15: ("DANGER JERK", f"{danger_jerk}"),
      16: ("SPEED JERK", f"{speed_jerk}"),
      17: (model_name, "")
    }

  def render(self, sidebar_rect: rl.Rectangle):
    if not self._visible:
      return

    count = len(self._active_ids)
    if count == 0:
      return

    rl.draw_rectangle_rec(sidebar_rect, rl.BLACK)

    spacing = max(1, (int(sidebar_rect.height) - (count * METRIC_HEIGHT)) // max(1, (count + 1)))
    y = sidebar_rect.y + spacing

    for metric_id in self._active_ids:
      if metric_id <= 0 or metric_id not in self._metrics:
        continue
      label_first, label_second = self._metrics[metric_id]
      self._draw_metric(sidebar_rect, label_first, label_second, self._metric_colors.get(metric_id, self._metric_color), y)
      y += METRIC_HEIGHT + spacing
