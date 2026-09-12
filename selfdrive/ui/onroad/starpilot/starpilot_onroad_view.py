import math

import pyray as rl
from msgq.visionipc import VisionStreamType
from openpilot.selfdrive.ui.onroad.augmented_road_view import AugmentedRoadView
from openpilot.selfdrive.ui.onroad.starpilot.starpilot_border import render_behind, render_overlay, render_background_effects
from openpilot.selfdrive.ui.onroad.starpilot.path import render_adjacent_lanes, render_path_edges
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.onroad.starpilot.torque_bar import TorqueBar
from openpilot.selfdrive.ui.onroad.starpilot.rivian_lateral_mode import rivian_lateral_mode
from openpilot.selfdrive.ui.onroad.starpilot.widget_layout_manager import WidgetLayoutManager
from openpilot.selfdrive.ui.onroad.starpilot.widgets import (
  SetSpeedWidget, SpeedLimitWidget, PedalIconsWidget,
  AetherGaugeWidget, PersonalityButtonWidget, DriverMonitorWidget,
  SteeringWheelWidget, StoppedTimerWidget, ModelSourceWidget
)
from openpilot.selfdrive.ui.onroad.starpilot.stopping_point import render_stopping_point
from openpilot.selfdrive.ui.onroad.starpilot.pause_indicators import render_lateral_paused, render_longitudinal_paused
from openpilot.selfdrive.ui.onroad.starpilot.pulse_glide import get_pulse_glide_border_color, render_pulse_glide
from openpilot.selfdrive.ui.onroad.starpilot.pip_sidecam import PipSideCamera
from openpilot.selfdrive.ui.onroad.starpilot.favorite_radial_menu import FavoriteRadialMenu
from openpilot.selfdrive.ui.onroad.starpilot.weather_icon import render_weather_icon
from openpilot.selfdrive.ui.onroad.starpilot.developer_metrics import build_developer_metric_parts, external_gpu_temperature_metric, external_gpu_memory_metric, system_memory_total_gib
from openpilot.selfdrive.ui.lib.starpilot_status import (
  get_screen_edge_color,
)
from openpilot.selfdrive.ui.lib.starpilot_visuals import get_border_roundness
from openpilot.starpilot.common.favorite_slots import (
  build_favorite_slot_options,
  filter_favorite_slot_options,
  favorite_key_is_valid,
  is_bool_param,
)

from openpilot.system.ui.lib.application import MousePos, gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import draw_text_with_shadow, measure_text_cached

from cereal import log
AlertSize = log.SelfdriveState.AlertSize


class StarPilotOnroadView(AugmentedRoadView):
  def __init__(self, stream_type: VisionStreamType = VisionStreamType.VISION_STREAM_ROAD):
    super().__init__(stream_type)
    self._params = ui_state.ui_params

    self._font_bold = gui_app.font(FontWeight.BOLD)
    self._font_medium = gui_app.font(FontWeight.MEDIUM)
    self._torque_bar = TorqueBar()
    self._min_fps = 99.9
    self._max_fps = 0.0
    self._avg_fps = 0.0
    self._memory_total_gib = system_memory_total_gib()

    self._pip_sidecam = self._child(PipSideCamera())
    self._favorite_radial_menu = FavoriteRadialMenu(
      ui_state.ui_params,
      ui_state.params_memory,
      self._favorite_slot_options,
    )
    self._favorite_input_consumed = False

    self.layout_manager = WidgetLayoutManager(self._content_rect)

    # Disable parent rendering calls — layout manager draws at computed bounds
    self._draw_driver_state = False
    self._hud_renderer.draw_set_speed = False
    self._hud_renderer.draw_exp_button = False

    # Initialize layout widgets
    self._set_speed_widget = SetSpeedWidget(self._hud_renderer)
    self._speed_limit_widget = SpeedLimitWidget()
    self._aethergauge_widget = AetherGaugeWidget(self._hud_renderer)
    self._steering_wheel_widget = SteeringWheelWidget(self._hud_renderer._exp_button)
    self._pedals_widget = PedalIconsWidget()
    self._personality_button_widget = PersonalityButtonWidget()
    self._driver_monitor_widget = DriverMonitorWidget(self.driver_state_renderer)
    self._model_source_widget = ModelSourceWidget()
    self._stopped_timer_widget = StoppedTimerWidget(self.is_in_reverse)

    # Register to layout zones
    self.layout_manager.register_widget("left", self._set_speed_widget)
    self.layout_manager.register_widget("left", self._speed_limit_widget)
    self.layout_manager.register_widget("left", self._aethergauge_widget)
    self.layout_manager.register_widget("right", self._steering_wheel_widget)
    self.layout_manager.register_widget("right", self._pedals_widget)
    self.layout_manager.register_widget("right_center", self._model_source_widget)
    self.layout_manager.register_widget("bottom", self._personality_button_widget)
    self.layout_manager.register_widget("bottom", self._driver_monitor_widget)

    # Register as child widgets for click propagation
    self._child(self._set_speed_widget)
    self._child(self._speed_limit_widget)
    self._child(self._aethergauge_widget)
    self._child(self._steering_wheel_widget)
    self._child(self._pedals_widget)
    self._child(self._personality_button_widget)
    self._child(self._driver_monitor_widget)
    self._child(self._model_source_widget)
    self._child(self._stopped_timer_widget)

  def _update_state(self) -> None:
    rivian_lateral_mode.update()
    self._hud_renderer._exp_button.wheel_tint = rivian_lateral_mode.wheel_tint

  def _render(self, rect: rl.Rectangle):
    border_width = self._get_border_width()
    border_roundness = get_border_roundness(rect, border_width)
    border_color = get_pulse_glide_border_color(ui_state.sm, get_screen_edge_color(ui_state))
    rl.draw_rectangle_rounded(rect, border_roundness, 10, border_color)
    render_background_effects(rect, border_width)

    # The favorite menu has first claim on the lower-left gesture. Filtering
    # its events before the inherited HUD/widgets render prevents a corner tap
    # from also activating a background on-road control.
    original_events = list(gui_app.mouse_events)
    self._favorite_input_consumed = False
    if ui_state.started:
      anticipated_content_rect = rl.Rectangle(
        rect.x + border_width,
        rect.y + border_width,
        rect.width - 2 * border_width,
        rect.height - 2 * border_width,
      )
      self._favorite_input_consumed = self._favorite_radial_menu.process_mouse_events(
        original_events, anticipated_content_rect,
      )
      if self._favorite_input_consumed:
        gui_app.mouse_events[:] = []

    try:
      self._hud_renderer.draw_current_speed = (
        ui_state.started and not self._stopped_timer_widget.replaces_current_speed
      )
      super()._render(rect)

      if not ui_state.started:
        self._favorite_radial_menu.collapse()
        return

      if self._draw_hud_controls:
        dm = self.driver_state_renderer
        self.layout_manager.update_layout(self._content_rect, is_rhd=dm.is_rhd if dm else False)
        self._render_slc()
        self._render_overlays()
        self._render_road_name()

      self._pip_sidecam.render(self._content_rect)

      # The picker is an app-drawer modal, so it intentionally draws above
      # PiP and other on-road overlays while active.
      if self._draw_hud_controls and not self._full_alert_showing():
        rl.begin_scissor_mode(
          int(round(self._content_rect.x)), int(round(self._content_rect.y)),
          int(round(self._content_rect.width)), int(round(self._content_rect.height)),
        )
        try:
          self._favorite_radial_menu.render(self._content_rect)
        finally:
          rl.end_scissor_mode()
      else:
        self._favorite_radial_menu.collapse()
    finally:
      gui_app.mouse_events[:] = original_events

  def _draw_border(self, rect: rl.Rectangle):
    border_width = self._get_border_width()
    border_roundness = get_border_roundness(rect, border_width)
    rl.draw_rectangle_rounded_lines_ex(rect, border_roundness, 10, border_width, rl.BLACK)
    border_rect = rl.Rectangle(rect.x + border_width, rect.y + border_width,
                                rect.width - 2 * border_width, rect.height - 2 * border_width)
    render_overlay(border_rect, border_width)

  def _render_slc(self):
    if self._full_alert_showing():
      return
    if self._speed_limit_widget.is_visible:
      self._speed_limit_widget.render(self._speed_limit_widget.rect)
    if self._set_speed_widget.is_visible:
      self._set_speed_widget.render(self._set_speed_widget.rect)

  def _render_overlays(self):
    alert_showing, _ = self.alert_renderer.will_render()
    if alert_showing is not None and alert_showing.size == AlertSize.full:
      return

    self._stopped_timer_widget.render(self._content_rect)
    if alert_showing is not None:
      return

    self._render_developer_metrics()

    self.layout_manager.render_widgets(exclude={"speed_limit", "set_speed"})

    self._render_torque_bar()
    self._render_bottom_row_widgets()

  def _render_torque_bar(self) -> None:
    """Draw the curved torque-utilization indicator at the bottom of the screen."""
    if not self._params.get_bool("EnableTorqueBarWidget", default=True):
      return
    rl.begin_scissor_mode(
      int(round(self._content_rect.x)), int(round(self._content_rect.y)),
      int(round(self._content_rect.width)), int(round(self._content_rect.height)),
    )
    self._torque_bar.render(self._content_rect)
    rl.end_scissor_mode()

  def _render_extra_road_overlays(self, rect: rl.Rectangle) -> None:
    """Render path features in the parent's clipped road-overlay layer."""
    mr = self.model_renderer

    if mr._path.projected_points.size:
      # Path edges (always rendered if track_edge_vertices exist)
      if mr._track_edge_vertices.size >= 4:
        render_path_edges(mr)

      # Render adjacent lanes (incorporates both adjacent path and blind spot warnings)
      render_adjacent_lanes(mr)

      # Render stopping point atop the path
      render_stopping_point(mr, self._font_bold)

    # Keep the CSC glow above the camera/model/path layers, but below the HUD.
    render_behind(rect, self._get_border_width())

  def _full_alert_showing(self) -> bool:
    alert_showing, _ = self.alert_renderer.will_render()
    return alert_showing is not None and alert_showing.size == AlertSize.full

  def _handle_mouse_press(self, mouse_pos: MousePos):
    if self._favorite_input_consumed or self._favorite_radial_menu.blocks_pointer(mouse_pos):
      return

    # Check if click maps to any of the layout widgets
    for zone in self.layout_manager.zones.values():
      for widget in zone:
        if widget.is_visible and widget.blocks_pointer and rl.check_collision_point_rec(mouse_pos, widget.rect):
          return
    super()._handle_mouse_press(mouse_pos)

  def _favorite_slot_options(self):
    cp = ui_state.CP
    return filter_favorite_slot_options(
      build_favorite_slot_options(
        lambda key: favorite_key_is_valid(self._params, key),
        alpha_longitudinal_available=bool(getattr(cp, "alphaLongitudinalAvailable", False)),
      ),
      {
        # This matches Galaxy's capability gate without importing its web
        # server (or duplicating its option metadata) into the on-road UI.
        "HasRivianAngleHarness": (
          getattr(cp, "brand", "") == "rivian" and bool(int(getattr(cp, "flags", 0)) & (1 << 0))
        ),
      },
    )

  def _render_developer_metrics(self):
    toggles = ui_state.starpilot_toggles
    debug_mode = bool(toggles.get("debug_mode", self._params.get_bool("DebugMode")))
    developer_metrics = (
      bool(toggles.get("developer_ui", self._params.get_bool("DeveloperUI"))) and
      self._params.get_bool("DeveloperMetrics")
    ) or debug_mode

    def metric_enabled(toggle_key: str, param_key: str, debug_override: bool = False) -> bool:
      if debug_mode and debug_override:
        return True
      if developer_metrics and toggle_key in toggles:
        return bool(toggles.get(toggle_key))
      if developer_metrics:
        return self._params.get_bool(param_key)
      return False

    show_fps = metric_enabled("show_fps", "FPSCounter", debug_override=True)
    show_cpu = metric_enabled("cpu_metrics", "ShowCPU", debug_override=True)
    show_gpu = metric_enabled("gpu_metrics", "ShowGPU")
    show_temp = metric_enabled("numerical_temp", "NumericalTemp", debug_override=True)
    show_memory = metric_enabled("memory_metrics", "ShowMemoryUsage", debug_override=True)

    if not any((show_fps, show_cpu, show_gpu, show_temp, show_memory)):
      return

    # Track FPS
    fps = rl.get_fps()

    if math.isfinite(fps) and fps > 0:
      self._min_fps = min(self._min_fps, fps)
      self._max_fps = max(self._max_fps, fps)
      alpha = 1.0 / (60.0 * 5.0)
      if self._avg_fps == 0.0:
        self._avg_fps = fps
      else:
        self._avg_fps = alpha * fps + (1.0 - alpha) * self._avg_fps

    # Gather device stats
    sm = ui_state.sm
    device_state = sm["deviceState"] if sm.valid.get("deviceState", False) and sm.alive.get("deviceState", False) else None
    cpu_usage = []
    cpu_temps = []
    gpu_usage = 0
    gpu_temps = []
    max_temp = 0.0
    memory_usage = 0
    if device_state:
      cpu_usage = list(device_state.cpuUsagePercent)
      cpu_temps = list(device_state.cpuTempC)
      gpu_usage = device_state.gpuUsagePercent
      gpu_temps = list(device_state.gpuTempC)
      max_temp = device_state.maxTempC
      memory_usage = device_state.memoryUsagePercent

    font = self._font_medium
    font_size = 24

    def draw_text_with_outline(text, pos_x, pos_y, color):
      pos = rl.Vector2(pos_x, pos_y)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x - 1, pos.y - 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x + 1, pos.y - 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x - 1, pos.y + 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x + 1, pos.y + 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, pos, font_size, 0, color)

    parts = build_developer_metric_parts(
      show_fps=show_fps,
      show_cpu=show_cpu,
      show_gpu=show_gpu,
      show_temp=show_temp,
      show_memory=show_memory,
      fps=fps,
      min_fps=self._min_fps,
      max_fps=self._max_fps,
      avg_fps=self._avg_fps,
      cpu_usage_percent=cpu_usage,
      cpu_temp_c=cpu_temps,
      gpu_usage_percent=gpu_usage,
      gpu_temp_c=gpu_temps,
      max_temp_c=max_temp,
      memory_usage_percent=memory_usage,
      memory_total_gib=self._memory_total_gib,
    )

    if device_state is None:
      # FPS comes from the renderer; device metrics require a live sample.
      parts = [part if part.startswith(("FPS:", "Min:", "Max:", "Avg:")) else part.split(":", 1)[0] + ": --" for part in parts]

    if show_gpu:
      parts.append(external_gpu_temperature_metric(ui_state.sm))
      parts.append(external_gpu_memory_metric(ui_state.sm))
    lines = []
    available_width = self._content_rect.width - 24
    for part in parts:
      candidate = f"{lines[-1]} | {part}" if lines else part
      if lines and measure_text_cached(font, candidate, font_size).x <= available_width:
        lines[-1] = candidate
      else:
        lines.append(part)
    border_width = self._get_border_width()
    for index, line in enumerate(lines):
      sz = measure_text_cached(font, line, font_size)
      bx = self._content_rect.x + (self._content_rect.width - sz.x) / 2
      by = self._content_rect.y + self._content_rect.height + (border_width - sz.y) // 2
      by -= (len(lines) - index - 1) * (font_size + 4)
      draw_text_with_outline(line, bx, by, rl.WHITE)


  def _render_bottom_row_widgets(self):
    # Hide if any alert (stock or StarPilot) is active
    alert_showing, _ = self.alert_renderer.will_render()
    if alert_showing is not None:
      return

    dm = self.driver_state_renderer
    # Ensure DM position has been initialized/calculated
    if not dm or dm.position_x == 0.0:
      return

    # Check pause/CEM states
    starpilot_car_state = ui_state.sm["starpilotCarState"] if ui_state.sm.valid.get("starpilotCarState", False) else None
    plan = ui_state.sm["starpilotPlan"] if ui_state.sm.valid.get("starpilotPlan", False) else None
    lateral_paused = starpilot_car_state.pauseLateral if starpilot_car_state else False
    longitudinal_paused = (starpilot_car_state.pauseLongitudinal or starpilot_car_state.forceCoast) if starpilot_car_state else False

    # Build the list of active left-side (DM-adjacent) badges in order of priority:
    # 1. Lateral Paused, 2. Longitudinal Paused
    active_badges = []
    if lateral_paused:
      active_badges.append("lateral_paused")
    if longitudinal_paused:
      active_badges.append("longitudinal_paused")
    if starpilot_car_state and starpilot_car_state.pulseAndGlide:
      active_badges.append("pulse_glide")

    # Dimensions
    badge_w = 120
    badge_h = 72
    spacing = 20

    # DM button size is 192 (radius 96)
    dm_r = 96

    # Render DM-adjacent badges sequentially
    for i, badge in enumerate(active_badges):
      if not dm.is_rhd:
        # LHD: grow to the right
        bx = dm.position_x + dm_r + spacing + i * (badge_w + spacing)
      else:
        # RHD: grow to the left
        bx = dm.position_x - dm_r - spacing - badge_w - i * (badge_w + spacing)

      by = dm.position_y - badge_h / 2
      badge_rect = rl.Rectangle(bx, by, badge_w, badge_h)

      if badge == "lateral_paused":
        render_lateral_paused(badge_rect)
      elif badge == "longitudinal_paused":
        render_longitudinal_paused(badge_rect)
      elif badge == "pulse_glide":
        pulse_glide_coasting = bool(getattr(plan, "pulseGlideCoasting", False)) if plan else False
        render_pulse_glide(badge_rect, pulse_glide_coasting)

    # 2. Render Weather (on the opposite side of DM icon)
    if plan and plan.weatherId != 0:
      weather_w = 120
      weather_h = 120
      if not dm.is_rhd:
        # LHD: Weather on the far right
        wx = self._content_rect.x + self._content_rect.width - 30 - weather_w
      else:
        # RHD: Weather on the far left
        wx = self._content_rect.x + 30

      cy = dm.position_y - weather_h / 2
      weather_rect = rl.Rectangle(wx, cy, weather_w, weather_h)
      render_weather_icon(weather_rect)

  def _render_road_name(self):
    if self._full_alert_showing():
      return

    toggles = ui_state.starpilot_toggles
    road_name_on = bool(toggles.get("road_name_ui", self._params.get_bool("RoadNameUI")))
    if not road_name_on:
      return

    mapd = ui_state.sm["mapdOut"] if ui_state.sm.valid.get("mapdOut", False) else None
    if mapd is None:
      return
    road_name = str(mapd.roadName or "")
    if not road_name:
      return

    font = self._font_bold
    font_size = 40
    sz = measure_text_cached(font, road_name, font_size)

    cx = self._content_rect.x + self._content_rect.width / 2
    text_pos = rl.Vector2(
      round(cx - sz.x / 2),
      round(self._content_rect.y + self._content_rect.height - sz.y - 5),
    )
    draw_text_with_shadow(font, road_name, text_pos, font_size, rl.WHITE)
