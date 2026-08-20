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
  SteeringWheelWidget, StoppedTimerWidget
)
from openpilot.selfdrive.ui.onroad.starpilot.stopping_point import render_stopping_point
from openpilot.selfdrive.ui.onroad.starpilot.pause_indicators import render_lateral_paused, render_longitudinal_paused
from openpilot.selfdrive.ui.onroad.starpilot.pip_sidecam import PipSideCamera
from openpilot.selfdrive.ui.onroad.starpilot.weather_icon import render_weather_icon
from openpilot.selfdrive.ui.lib.starpilot_status import (
  get_screen_edge_color,
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

    self._pip_sidecam = self._child(PipSideCamera())

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
    self._stopped_timer_widget = StoppedTimerWidget(self.is_in_reverse)

    # Register to layout zones
    self.layout_manager.register_widget("left", self._set_speed_widget)
    self.layout_manager.register_widget("left", self._speed_limit_widget)
    self.layout_manager.register_widget("left", self._aethergauge_widget)
    self.layout_manager.register_widget("right", self._steering_wheel_widget)
    self.layout_manager.register_widget("right", self._pedals_widget)
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
    self._child(self._stopped_timer_widget)

  def _update_state(self) -> None:
    rivian_lateral_mode.update()
    self._hud_renderer._exp_button.wheel_tint = rivian_lateral_mode.wheel_tint

  def _render(self, rect: rl.Rectangle):
    border_width = self._get_border_width()
    border_color = get_screen_edge_color(ui_state)
    rl.draw_rectangle_rounded(rect, 0.12, 10, border_color)
    render_background_effects(rect, border_width)

    self._hud_renderer.draw_current_speed = (
      ui_state.started and not self._stopped_timer_widget.replaces_current_speed
    )
    super()._render(rect)

    if not ui_state.started:
      return

    if self._draw_hud_controls:
      dm = self.driver_state_renderer
      self.layout_manager.update_layout(self._content_rect, is_rhd=dm.is_rhd if dm else False)
      self._render_slc()
      self._render_overlays()
      self._render_road_name()

    # PiP renders last so it always sits on top of every other on-road overlay.
    self._pip_sidecam.render(self._content_rect)

  def _draw_border(self, rect: rl.Rectangle):
    border_width = self._get_border_width()
    rl.draw_rectangle_rounded_lines_ex(rect, 0.12, 10, border_width, rl.BLACK)
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
    # Check if click maps to any of the layout widgets
    for zone in self.layout_manager.zones.values():
      for widget in zone:
        if widget.is_visible and rl.check_collision_point_rec(mouse_pos, widget.rect):
          return
    super()._handle_mouse_press(mouse_pos)

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

    if fps > 0:
      self._min_fps = min(self._min_fps, fps)
      self._max_fps = max(self._max_fps, fps)
      alpha = 1.0 / (60.0 * 5.0)
      if self._avg_fps == 0.0:
        self._avg_fps = fps
      else:
        self._avg_fps = alpha * fps + (1.0 - alpha) * self._avg_fps

    # Gather device stats
    device_state = ui_state.sm["deviceState"] if ui_state.sm.valid.get("deviceState", False) else None
    cpu_val = 0
    gpu_val = 0
    temp_val = 0
    mem_val = 0
    mem_gb = 0.0
    if device_state:
      cpu_list = list(device_state.cpuUsagePercent)
      cpu_val = int(sum(cpu_list) / len(cpu_list)) if cpu_list else 0
      gpu_val = int(device_state.gpuUsagePercent)
      temp_val = int(device_state.maxTempC)
      mem_val = int(device_state.memoryUsagePercent)
      mem_gb = 8.0 * mem_val / 100.0

    font = self._font_medium
    font_size = 24

    def draw_text_with_outline(text, pos_x, pos_y, color):
      pos = rl.Vector2(pos_x, pos_y)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x - 1, pos.y - 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x + 1, pos.y - 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x - 1, pos.y + 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x + 1, pos.y + 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, pos, font_size, 0, color)

    parts = []
    if show_cpu:
      parts.append(f"CPU: {cpu_val}%")
    if show_gpu:
      parts.append(f"GPU: {gpu_val}%")
    if show_temp:
      parts.append(f"TEMP: {temp_val}°C")
    if show_memory:
      parts.append(f"RAM: {mem_gb:.1f} GB ({mem_val}%)")
    if show_fps:
      parts += [f"FPS: {round(fps)}", f"Min: {round(self._min_fps)}",
                f"Max: {round(self._max_fps)}", f"Avg: {round(self._avg_fps)}"]

    line = " | ".join(parts)
    sz = measure_text_cached(font, line, font_size)
    bx = self._content_rect.x + (self._content_rect.width - sz.x) / 2
    border_width = self._get_border_width()
    by = self._content_rect.y + self._content_rect.height + (border_width - sz.y) // 2
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
    lateral_paused = starpilot_car_state.pauseLateral if starpilot_car_state else False
    longitudinal_paused = (starpilot_car_state.pauseLongitudinal or starpilot_car_state.forceCoast) if starpilot_car_state else False

    # Build the list of active left-side (DM-adjacent) badges in order of priority:
    # 1. Lateral Paused, 2. Longitudinal Paused
    active_badges = []
    if lateral_paused:
      active_badges.append("lateral_paused")
    if longitudinal_paused:
      active_badges.append("longitudinal_paused")

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

    # 2. Render Weather (on the opposite side of DM icon)
    plan = ui_state.sm["starpilotPlan"] if ui_state.sm.valid.get("starpilotPlan", False) else None
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
