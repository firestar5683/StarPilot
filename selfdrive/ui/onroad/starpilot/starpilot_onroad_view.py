import pyray as rl
import time
from msgq.visionipc import VisionStreamType
from openpilot.common.params import Params
from openpilot.selfdrive.ui.onroad.augmented_road_view import AugmentedRoadView
from openpilot.selfdrive.ui.onroad.starpilot.starpilot_border import render_behind, render_overlay, render_background_effects
from openpilot.selfdrive.ui.onroad.starpilot.path import render_adjacent_lanes, render_path_edges
from openpilot.selfdrive.ui.onroad.starpilot.personality_button import PersonalityButton, BTN_SIZE
from openpilot.selfdrive.ui.onroad.starpilot.slc_speed_limit import (
  render_speed_limit, handle_slc_click, SET_SPEED_X_OFFSET, SET_SPEED_Y_OFFSET,
  SET_SPEED_WIDTH_IMP, SET_SPEED_WIDTH_MET, SET_SPEED_HEIGHT, SIGN_MARGIN,
)
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.onroad.starpilot.aethergauge import AetherGauge
from openpilot.selfdrive.ui.lib.starpilot_status import (
    get_screen_edge_color, ENGAGED_COLOR,
    EXPERIMENTAL_COLOR, TRAFFIC_COLOR,
)
from openpilot.system.ui.lib.application import MousePos, gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached


class StarPilotOnroadView(AugmentedRoadView):
  def __init__(self, stream_type: VisionStreamType = VisionStreamType.VISION_STREAM_ROAD):
    super().__init__(stream_type)
    self._params = Params()

    self._personality_button = PersonalityButton()
    self._font_bold = gui_app.font(FontWeight.BOLD)
    self._font_medium = gui_app.font(FontWeight.MEDIUM)
    self._standstill_started_at = 0.0
    self._aethergauge = AetherGauge()

  def _render(self, rect: rl.Rectangle):
    self._position_personality_button()
    border_width = self._get_border_width()
    border_color = get_screen_edge_color(ui_state)
    rl.draw_rectangle_rounded(rect, 0.12, 10, border_color)
    render_background_effects(rect, border_width)
    super()._render(rect)

    if not ui_state.started:
      return

    self._render_slc()
    self._render_overlays()
    self._render_path_features(rect)

  def _render_slc(self):
    rl.begin_scissor_mode(
      int(self._content_rect.x), int(self._content_rect.y),
      int(self._content_rect.width), int(self._content_rect.height),
    )
    render_speed_limit(self._content_rect)
    rl.end_scissor_mode()

  def _render_overlays(self):
    self._position_personality_button()
    self._personality_button.render()
    self._render_standstill_timer()
    self._render_developer_metrics()
    dm = self.driver_state_renderer
    if dm and dm.is_visible and dm.position_x != 0.0:
      dm_top = dm.position_y - 96  # top of DM icon
      self._aethergauge.render(
        self._content_rect, self._font_bold, self._font_medium,
        current_speed=self._hud_renderer.speed,
        cx=dm.position_x, bottom=dm_top - 105
      )
    else:
      self._aethergauge.render(self._content_rect, self._font_bold, self._font_medium, current_speed=self._hud_renderer.speed)
    self._render_bottom_row_widgets()
    self._render_pedals()

  def _render_path_features(self, rect: rl.Rectangle):
    """Render path-related features (adjacent paths, blind spot, path edges)."""
    mr = self.model_renderer

    # Only render if we have path data
    if not mr._path.projected_points.size:
      return

    rl.begin_scissor_mode(
      int(self._content_rect.x), int(self._content_rect.y),
      int(self._content_rect.width), int(self._content_rect.height),
    )

    # Path edges (always rendered if track_edge_vertices exist)
    if mr._track_edge_vertices.size >= 4:
      render_path_edges(mr)

    # Render adjacent lanes (incorporates both adjacent path and blind spot warnings)
    render_adjacent_lanes(mr)

    # Render stopping point atop the path
    from openpilot.selfdrive.ui.onroad.starpilot.stopping_point import render_stopping_point
    render_stopping_point(mr, self._font_bold)

    rl.end_scissor_mode()

  def _position_personality_button(self):
    dm = self.driver_state_renderer
    toggle_on = self._params.get_bool("OnroadDistanceButton")
    GAP = 10

    if dm and dm.position_x != 0.0:
      unshifted = dm.position_x - dm.x_shift
      y = dm.position_y - BTN_SIZE / 2

      if dm.is_rhd:
        x = dm.position_x - BTN_SIZE * 2
      else:
        x = unshifted - BTN_SIZE // 2
        dm.x_shift = BTN_SIZE + GAP if (dm.is_visible and toggle_on) else 0.0

      self._personality_button.set_position(x, y)

    if not dm or not dm.is_visible or not toggle_on:
      self._personality_button.set_visible(False)
      if dm and not dm.is_rhd:
        dm.x_shift = 0.0
      return

    self._personality_button.set_visible(
      lambda: ui_state.started and ui_state.has_longitudinal_control
    )

  def _render_standstill_timer(self):
    if not self._params.get_bool("stopped_timer"):
      self._standstill_started_at = 0.0
      return
    if not ui_state.sm.valid.get("carState", False):
      return

    car_state = ui_state.sm["carState"]
    if getattr(car_state, "standstill", False):
      if self._standstill_started_at == 0.0:
        self._standstill_started_at = time.monotonic()
    else:
      self._standstill_started_at = 0.0
      return

    if self._standstill_started_at == 0.0:
      return

    duration = int(time.monotonic() - self._standstill_started_at)
    if duration < 60:
      return

    minutes = duration // 60
    seconds = duration % 60
    minute_text = f"{minutes} minute{'s' if minutes != 1 else ''}"
    second_text = f"{seconds} second{'s' if seconds != 1 else ''}"
    minute_size = measure_text_cached(self._font_bold, minute_text, 176)
    second_size = measure_text_cached(self._font_medium, second_text, 66)

    import numpy as np

    def blend_colors(start: rl.Color, end: rl.Color, transition: float) -> rl.Color:
      transition = float(np.clip(transition, 0.0, 1.0))
      return rl.Color(
        int(start.r + transition * (end.r - start.r)),
        int(start.g + transition * (end.g - start.g)),
        int(start.b + transition * (end.b - start.b)),
        255,
      )

    if duration < 150:
      transition = (duration - 60) / 90.0
      duration_color = blend_colors(ENGAGED_COLOR, EXPERIMENTAL_COLOR, transition)
    elif duration < 300:
      transition = (duration - 150) / 150.0
      duration_color = blend_colors(EXPERIMENTAL_COLOR, TRAFFIC_COLOR, transition)
    else:
      duration_color = TRAFFIC_COLOR

    x = gui_app.width / 2
    rl.draw_text_ex(
      self._font_bold,
      minute_text,
      rl.Vector2(x - minute_size.x / 2, 210 - minute_size.y / 2),
      176,
      0,
      duration_color,
    )
    rl.draw_text_ex(
      self._font_medium,
      second_text,
      rl.Vector2(x - second_size.x / 2, 290 - second_size.y / 2),
      66,
      0,
      rl.Color(255, 255, 255, 242),
    )

  def _draw_border(self, rect: rl.Rectangle):
    border_width = self._get_border_width()
    rl.draw_rectangle_rounded_lines_ex(rect, 0.12, 10, border_width, rl.BLACK)
    border_rect = rl.Rectangle(rect.x + border_width, rect.y + border_width,
                                rect.width - 2 * border_width, rect.height - 2 * border_width)

    render_behind(border_rect, border_width)

    render_overlay(border_rect, border_width)

  def _handle_mouse_press(self, mouse_pos: MousePos):
    border_width = self._get_border_width()
    content_rect = rl.Rectangle(
      border_width, border_width,
      gui_app.width - 2 * border_width, gui_app.height - 2 * border_width,
    )
    ss_width = SET_SPEED_WIDTH_MET if ui_state.is_metric else SET_SPEED_WIDTH_IMP
    ss_x = content_rect.x + SET_SPEED_X_OFFSET + (SET_SPEED_WIDTH_IMP - ss_width) // 2
    sign_x = ss_x + SIGN_MARGIN
    sign_y = content_rect.y + SET_SPEED_Y_OFFSET + SET_SPEED_HEIGHT + SIGN_MARGIN
    sign_width = ss_width - 2 * SIGN_MARGIN
    handle_slc_click(mouse_pos, sign_x, sign_y, sign_width)

    if self._personality_button.is_interacting:
      return
    super()._handle_mouse_press(mouse_pos)

  def _render_developer_metrics(self):
    if not self._params.get_bool("ShowFPS"):
      return

    # Track FPS
    fps = rl.get_fps()
    if not hasattr(self, "_min_fps"):
      self._min_fps = 99.9
      self._max_fps = 0.0
      self._avg_fps = 0.0

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
    temp_val = 0
    mem_val = 0
    mem_gb = 0.0
    if device_state:
      cpu_list = list(device_state.cpuUsagePercent)
      cpu_val = int(sum(cpu_list) / len(cpu_list)) if cpu_list else 0
      temp_val = int(device_state.maxTempC)
      mem_val = int(device_state.memoryUsagePercent)
      mem_gb = 8.0 * mem_val / 100.0

    # Format text lines for top-right developer metrics overlay
    text_lines = [
      f"FPS: {round(fps)}",
      f"CPU: {cpu_val}%",
      f"TEMP: {temp_val}°C",
      f"RAM: {mem_gb:.1f} GB ({mem_val}%)"
    ]

    # Helper function for outlined text drawing
    font = self._font_medium
    font_size = 24
    line_height = font_size + 4

    def draw_text_with_outline(text, pos_x, pos_y, color):
      pos = rl.Vector2(pos_x, pos_y)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x - 1, pos.y - 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x + 1, pos.y - 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x - 1, pos.y + 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, rl.Vector2(pos.x + 1, pos.y + 1), font_size, 0, rl.BLACK)
      rl.draw_text_ex(font, text, pos, font_size, 0, color)

    # 1. Render top-right developer metrics block
    x = self._content_rect.x + self._content_rect.width - 30
    y = self._content_rect.y + 40
    for i, line in enumerate(text_lines):
      sz = measure_text_cached(font, line, font_size)
      draw_text_with_outline(line, x - sz.x, y + i * line_height, rl.WHITE)

    # 2. Render bottom-center detailed FPS tracker string (min/max/avg)
    fps_str = f"FPS: {round(fps)} | Min: {round(self._min_fps)} | Max: {round(self._max_fps)} | Avg: {round(self._avg_fps)}"
    sz = measure_text_cached(font, fps_str, font_size)
    bx = self._content_rect.x + (self._content_rect.width - sz.x) / 2
    by = self._content_rect.y + self._content_rect.height - sz.y - 10
    draw_text_with_outline(fps_str, bx, by, rl.WHITE)


  def _render_bottom_row_widgets(self):
    # Hide if alerts are active
    from cereal import log
    AlertSize = log.SelfdriveState.AlertSize
    if ui_state.sm["selfdriveState"].alertSize != AlertSize.none:
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
        from openpilot.selfdrive.ui.onroad.starpilot.pause_indicators import render_lateral_paused
        render_lateral_paused(badge_rect)
      elif badge == "longitudinal_paused":
        from openpilot.selfdrive.ui.onroad.starpilot.pause_indicators import render_longitudinal_paused
        render_longitudinal_paused(badge_rect)

    # 2. Render Compass & Weather (on the opposite side of DM icon)
    # Dimensions
    compass_w = 120
    compass_h = 120
    weather_w = 120
    weather_h = 120

    # Determine compass position
    if not dm.is_rhd:
      # LHD: Compass on the far right
      cx = self._content_rect.x + self._content_rect.width - 30 - compass_w
    else:
      # RHD: Compass on the far left
      cx = self._content_rect.x + 30

    cy = dm.position_y - compass_h / 2
    compass_rect = rl.Rectangle(cx, cy, compass_w, compass_h)

    # Render Compass
    from openpilot.selfdrive.ui.onroad.starpilot.compass import render_compass
    render_compass(compass_rect, self._font_medium)

    # Render Weather next to Compass
    plan = ui_state.sm["starpilotPlan"] if ui_state.sm.valid.get("starpilotPlan", False) else None
    if plan and plan.weatherId != 0:
      if not dm.is_rhd:
        # LHD: Weather to the left of Compass
        wx = cx - spacing - weather_w
      else:
        # RHD: Weather to the right of Compass
        wx = cx + compass_w + spacing

      weather_rect = rl.Rectangle(wx, cy, weather_w, weather_h)
      from openpilot.selfdrive.ui.onroad.starpilot.weather_icon import render_weather_icon
      render_weather_icon(weather_rect)

  def _render_pedals(self):
    from cereal import log
    AlertSize = log.SelfdriveState.AlertSize
    if ui_state.sm["selfdriveState"].alertSize != AlertSize.none:
      return

    dm = self.driver_state_renderer
    if not dm or dm.position_x == 0.0:
      return

    anchor = dm.position_x if dm.is_rhd else dm.position_x - dm.x_shift
    start_x = anchor - 96
    start_y = dm.position_y - 198

    from openpilot.selfdrive.ui.onroad.starpilot.pedal_icons import render_pedal_icons
    render_pedal_icons(start_x, start_y, self._font_bold)

