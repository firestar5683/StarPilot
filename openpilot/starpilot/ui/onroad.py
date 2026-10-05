"""Two-profile native onroad composition over a caller-owned camera layer.

The host supplies state and, when a frame is available, the current camera/model
renderer as a callback. Offline previews create no camera or IPC resources.
The visual widgets retain the frozen StarPilot geometry under the adjacent
LICENSE, while the application owns all state and action transport.
"""

from collections.abc import Callable
from pathlib import Path
import hashlib
import json

import pyray as rl

from openpilot.starpilot.ui import clip
from openpilot.system.ui.lib.application import gui_app
from openpilot.starpilot.ui.onroad_customization import offset, placement, rgba
from openpilot.starpilot.ui.appearance_preferences import CameraViewChoice

from openpilot.starpilot.ui.onroad_alerts import AlertRenderer
from openpilot.starpilot.ui.onroad_border import render_compact_half_borders
from openpilot.starpilot.ui.onroad_compact_widgets import (CompactHudRenderer, MiciSidebarWidgets,
                                                           draw_curve_road_icon, draw_lead_icon, draw_stop_light_icon)
from openpilot.starpilot.ui.onroad_curve import controlling as curve_controlling, glow_color, intensity, render_glow, status_label
from openpilot.starpilot.ui.onroad_conditional import status as conditional_status, stop_active, reason as conditional_reason
from openpilot.starpilot.ui.onroad_corner import CornerHintCache, render_corner_hint
from openpilot.starpilot.ui.onroad_large_widgets import CurrentSpeedHud, UnifiedSpeedWidget, SteeringWheelWidget
from openpilot.starpilot.ui.live_developer_sidebar import render_sidebar as render_live_sidebar
from openpilot.starpilot.ui.onroad_state import AlertSize, OnroadState, slc_controls
from openpilot.starpilot.ui.onroad_stopped_timer import duration_color, duration_text
from openpilot.starpilot.ui.onroad_torque import TorqueBarWidget
from openpilot.starpilot.ui.onroad_navigation import NavigationCard
from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile
from openpilot.starpilot.conditional_mode.policy import ModeChoice


CameraLayer = Callable[[rl.Rectangle, OnroadState], None]
OverlayLayer = Callable[[rl.Rectangle, OnroadState], None]
PipLayer = Callable[[rl.Rectangle, OnroadState], None]


def axis_status_color(state: OnroadState) -> rl.Color:
  """Retain StarPilot's existing off, AOL, long-only, and combined edge colors."""
  if state.longitudinal_overridden:
    return rl.Color(145, 155, 149, 255)
  if state.lateral_active and state.switchback_mode:
    return rl.Color(139, 108, 197, 255)
  if stop_active(state):
    return rl.Color(218, 111, 37, 255)
  if state.longitudinal_active and state.traffic_mode:
    return rl.Color(201, 34, 49, 255)
  mode = state.conditional_effective if state.longitudinal_active else None
  if mode is not None and mode.reason == 'manual_chill':
    return rl.Color(255, 214, 0, 255)
  if mode is not None and mode.effective_experimental:
    return rl.Color(218, 111, 37, 255)
  if state.lateral_active and state.longitudinal_active:
    if state.experimental_enabled and state.conditional_configured in (None, ModeChoice.STOCK):
      return rl.Color(218, 111, 37, 255)
    return rl.Color(22, 127, 64, 255)
  if state.lateral_active:
    return rl.Color(10, 186, 181, 255)
  if state.longitudinal_active:
    return rl.Color(255, 105, 180, 255)
  return rl.Color(18, 40, 57, 255)


class OnroadView:
  def __init__(self, fonts: BitmapFonts, asset_directory: Path, *, camera_layer: CameraLayer | None = None,
               extra_overlays: OverlayLayer | None = None, pip_layer: PipLayer | None = None,
               background_layer: OverlayLayer | None = None, projection_viewport: tuple[float, float] | None = None):
    self.projection_viewport = projection_viewport
    self._corner_cache = CornerHintCache()
    gui_app.add_render_prepare(self._corner_cache.prepare, self._corner_cache.close)
    self.fonts = fonts
    self.camera_layer = camera_layer
    self.background_layer = background_layer
    self.extra_overlays = extra_overlays
    self.driver_monitor_layer: OverlayLayer | None = None
    self.pip_layer = pip_layer
    self.stock_confidence_layer: OverlayLayer | None = None
    self.stock_confidence_reset: Callable[[], None] | None = None
    self._stock_confidence_last_source_ns: int | None = None
    self._stock_confidence_last_drive_frame: int | None = None
    self.alert = AlertRenderer(fonts)
    self.navigation = NavigationCard(fonts)
    self.torque_bar = TorqueBarWidget()
    if fonts.profile == Profile.LARGE:
      self.unified_speed = UnifiedSpeedWidget(fonts)
      self.current_speed = CurrentSpeedHud(fonts)
      self.steering_wheel = SteeringWheelWidget(asset_directory)
    else:
      self.compact_hud = CompactHudRenderer(fonts, asset_directory)
      self.compact_sidebar = MiciSidebarWidgets(fonts)
      self._fade_path = asset_directory / "icons_mici/onroad/onroad_fade.png"
      self._fade: rl.Texture | None = None

  def _prepare_compact_fade(self) -> None:
    if self._fade is not None:
      return
    entry = next(item for item in json.loads(Path(__file__).with_name("onroad-assets.json").read_text())["files"]
                 if item["file"] == "icons_mici/onroad/onroad_fade.png")
    data = self._fade_path.read_bytes()
    if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
      raise ValueError("Unreviewed compact fade art")
    self._fade = rl.load_texture(str(self._fade_path))
    if not self._fade.id:
      raise RuntimeError("Unable to load compact fade art")

  def render(self, state: OnroadState) -> None:
    if state.camera_available and self.camera_layer is None:
      raise ValueError("Camera observation requires a camera renderer")
    if self.fonts.profile == Profile.LARGE:
      if state.alert.size == AlertSize.FULL or not placement(state.customization, "large", "cruise_limits")["enabled"]:
        self.unified_speed.collapse_sources()
      self._large(state)
    else:
      self._compact(state)

  def _slc_actions(self, state: OnroadState) -> None:
    controls = slc_controls(self.fonts.profile, state)
    if not controls:
      return
    if self.fonts.profile == Profile.COMPACT:
      pending = state.speed_limit.pending_speed_limit_mps
      if pending is not None:
        value = round(pending * (3.6 if state.metric else 2.2369362921))
        dx, dy = offset(state.customization, "compact", "speed_limit_actions")
        button_y = 180 + dy
        header_y = button_y - 32 if button_y >= 32 else button_y + 62
        self.fonts.draw(f'NEW LIMIT {value}', FontRole.SEMI_BOLD, 20, 180 + dx, header_y)
    for control in controls:
      left, top, right, bottom = control.bounds
      rect = rl.Rectangle(left, top, right - left, bottom - top)
      rl.draw_rectangle_rounded(rect, 0.22, 8, rl.Color(*rgba(state.customization, "cardFill", self.fonts.profile, "speed_limit_actions")))
      rl.draw_rectangle_rounded_lines_ex(rect, 0.22, 8, 2, rl.Color(*rgba(state.customization, "cardBorder", self.fonts.profile, "speed_limit_actions")))
      size = 25 if self.fonts.profile == Profile.LARGE else 20
      measured = self.fonts.measure(control.label, FontRole.SEMI_BOLD, size)
      self.fonts.draw(control.label, FontRole.SEMI_BOLD, size,
                      rect.x + (rect.width - measured.width) / 2,
                      rect.y + (rect.height - measured.height) / 2,
                      rl.Color(*rgba(state.customization, "text", self.fonts.profile, "speed_limit_actions")))

  def _preview_badge(self, state: OnroadState) -> None:
    """Keep synthetic replay visibly identified even over a full alert."""
    preview = state.visual_preview
    if preview is None:
      return
    flags = []
    if preview.cem_reason is not None:
      flags.append('CEM')
    if preview.curve_curvature is not None:
      flags.append('CSC')
    if not flags:
      return
    large = self.fonts.profile == Profile.LARGE
    panel = rl.Rectangle(65, 966, 570, 74) if large else rl.Rectangle(8, 194, 310, 40)
    rl.draw_rectangle_rounded(panel, 0.18, 6, rl.Color(12, 24, 32, 245))
    rl.draw_rectangle_rounded_lines_ex(panel, 0.18, 6, 2, rl.Color(112, 192, 216, 255))
    self.fonts.draw('SYNTHETIC REPLAY PREVIEW', FontRole.SEMI_BOLD,
                    22 if large else 14, panel.x + 12, panel.y + (8 if large else 4))
    self.fonts.draw(' + '.join(flags), FontRole.SEMI_BOLD,
                    18 if large else 11, panel.x + 12, panel.y + (39 if large else 23))

  def _traffic_badge(self, state: OnroadState, y: int) -> None:
    if state.traffic_display is None or state.alert.size == AlertSize.FULL:
      return
    traffic_color = (rl.Color(200, 32, 48, 255) if state.traffic_display.state == 'active' else
                     rl.Color(255, 155, 63, 255) if state.traffic_display.state in ('paused', 'unavailable_profile', 'unavailable_source') else
                     rl.Color(165, 175, 180, 255))
    x = 1390 + (self.projection_viewport[0] if self.projection_viewport else state.viewport_width) - 1860
    self.fonts.draw(state.traffic_display.label, FontRole.SEMI_BOLD, 25, x, y, traffic_color)

  def _large(self, state: OnroadState) -> None:
    width, height = self.projection_viewport or (state.viewport_width, 1080)
    right_shift = width - 1860
    frame = rl.Rectangle(0, 0, width, height)
    content = rl.Rectangle(30, 30, width - 60, height - 60)
    # Current CameraView's no-frame placeholder stays at the disengaged blue.
    color = rl.Color(18, 40, 57, 255)
    edge = axis_status_color(state)
    rl.draw_rectangle_rec(content, color)
    clip.begin_scissor_mode(30, 30, int(content.width), int(content.height))
    try:
      if self.camera_layer is not None and state.camera_available:
        self.camera_layer(content, state)
      elif self.background_layer is not None:
        self.background_layer(content, state)
      pip_layer = getattr(self, "pip_layer", None)
      if pip_layer is not None and state.camera_available:
        pip_layer(content, state)
      rl.draw_rectangle_gradient_v(30, 30, int(content.width), 300, rl.Color(0, 0, 0, 114), rl.BLANK)
      if state.alert.size != AlertSize.FULL:
        if placement(state.customization, "large", "cruise_limits")["enabled"]:
          self.unified_speed.render(content, state)
        self._slc_actions(state)
      if not state.appearance.hide_speed and placement(state.customization, "large", "current_speed")["enabled"]:
        speed_content = rl.Rectangle(content.x + right_shift / 2, content.y, content.width, content.height)
        self.current_speed.render(speed_content, state)
      if state.alert.size == AlertSize.NONE:
        if not state.appearance.hide_steering_wheel and placement(state.customization, "large", "steering_wheel")["enabled"]:
          self.steering_wheel.render(content, state)
        if state.appearance.show_torque_bar:
          self.torque_bar.render(content, state, width if self.projection_viewport else 2160)
      if self.extra_overlays is not None:
        self.extra_overlays(content, state)
      if monitor_layer := getattr(self, "driver_monitor_layer", None):
        monitor_layer(content, state)
      if self.projection_viewport:
        rl.rl_push_matrix()
        try:
          rl.rl_translatef(right_shift, 0, 0)
          self.navigation.render(state)
        finally:
          rl.rl_pop_matrix()
      else:
        self.navigation.render(state)
      self.alert.render(content, state.alert)
    finally:
      clip.end_scissor_mode()
    if not self.projection_viewport:
      render_live_sidebar(self.fonts, rl.Rectangle(width, 0, 300, height), state.developer_metrics)
    if state.alert.size != AlertSize.FULL:
      render_corner_hint(content, cache=self._corner_cache)
    label = status_label(state)
    if label is not None:
      preview = state.visual_preview
      curve_color = glow_color(intensity(preview.curve_curvature)) if preview is not None and preview.curve_curvature is not None else \
        glow_color(intensity(state.curve.road_curvature)) if curve_controlling(state) and state.curve is not None else \
        rl.Color(112, 192, 216, 255)
      self.fonts.draw(label, FontRole.SEMI_BOLD, 29, 1390 + right_shift, 56,
                      curve_color)
    mode = conditional_status(state)
    if mode is not None and state.alert.size != AlertSize.FULL:
      family, reason, mode_color = mode
      mode_y = 101 if label is not None else 56
      self.fonts.draw(f'{family} {reason}', FontRole.SEMI_BOLD, 25, 1390 + right_shift, mode_y, mode_color)
      preview_reason = state.visual_preview.cem_reason if state.visual_preview is not None else None
      live_reason = conditional_reason(state)
      icon_rect = rl.Rectangle(1310 + right_shift, mode_y - 26, 60, 80)
      if stop_active(state) or (family == 'CEM' and live_reason == 'cem_stop'):
        draw_stop_light_icon(icon_rect)
      elif family == 'CEM' and (preview_reason == 'CURVE' or live_reason == 'cem_curve'):
        draw_curve_road_icon(icon_rect)
      elif live_reason in ('cem_lead', 'ccm_lead'):
        draw_lead_icon(icon_rect)
    self._traffic_badge(state, 56 + 45 * (int(label is not None) + int(mode is not None)))
    render_glow(content, state, border_width=30, time_s=rl.get_time())
    rl.draw_rectangle_lines_ex(frame, 30, rl.BLACK)
    rl.draw_rectangle_rounded_lines_ex(content, 0.12, 10, 30, edge)
    self._preview_badge(state)

  def _compact(self, state: OnroadState) -> None:
    frame = rl.Rectangle(0, 0, 476, 240)
    driver_camera = state.appearance.camera_view == CameraViewChoice.DRIVER or state.reverse_driver_camera
    color = axis_status_color(state) if state.alert.size == AlertSize.NONE else rl.Color(18, 40, 57, 255)
    rl.draw_rectangle(0, 0, 536, 240, rl.BLACK)
    clip.begin_scissor_mode(0, 0, 476, 240)
    try:
      if self.camera_layer is not None and state.camera_available:
        self.camera_layer(frame, state)
      elif self.background_layer is not None:
        self.background_layer(frame, state)
      pip_layer = getattr(self, "pip_layer", None)
      if pip_layer is not None and state.camera_available and not driver_camera and \
         state.appearance.camera_view != CameraViewChoice.NONE:
        pip_layer(frame, state)
      self._prepare_compact_fade()
      rl.draw_texture_ex(self._fade, rl.Vector2(0, 0), 0, 1, rl.WHITE)
      if state.alert.size == AlertSize.NONE and not driver_camera:
        self.compact_hud.render(state)
        if state.appearance.show_torque_bar:
          self.torque_bar.render(frame, state, 536)
        self._slc_actions(state)
        if state.stopped_duration_s is not None:
          self._stopped_timer(state.stopped_duration_s)
      if self.extra_overlays is not None:
        self.extra_overlays(frame, state)
      if monitor_layer := getattr(self, "driver_monitor_layer", None):
        monitor_layer(frame, state)
      self.navigation.render(state)
      signals = state.border_signals
      direction = (-1 if signals.left_blinker else 1 if signals.right_blinker else 0) if signals else 0
      self.alert.render(frame, state.alert, signal_direction=direction)
    finally:
      clip.end_scissor_mode()
    self._preview_badge(state)
    stock_layer = getattr(self, "stock_confidence_layer", None)
    source_ns = state.stock_confidence_source_stamp_ns if state.stock_confidence_source_fresh else None
    use_stock = (not driver_camera and state.appearance.camera_view != CameraViewChoice.NONE and
                 state.appearance.show_stock_confidence_ball and source_ns is not None and stock_layer is not None)
    if use_stock:
      last_source_ns = getattr(self, "_stock_confidence_last_source_ns", None)
      last_drive_frame = getattr(self, "_stock_confidence_last_drive_frame", None)
      if (last_source_ns is None or last_drive_frame != state.stock_confidence_drive_frame or
          source_ns < last_source_ns or source_ns - last_source_ns > 200_000_000):
        reset = getattr(self, "stock_confidence_reset", None)
        if reset is not None:
          reset()
      self._stock_confidence_last_source_ns = source_ns
      self._stock_confidence_last_drive_frame = state.stock_confidence_drive_frame
    else:
      self._stock_confidence_last_source_ns = None
    if not driver_camera:
      rail = rl.Rectangle(0, 0, 536, 240)
      if use_stock:
        stock_layer(rail, state)
      else:
        self.compact_sidebar.render(rail, state)
    clip.begin_scissor_mode(0, 0, 476, 240)
    try:
      rl.draw_rectangle_rounded_lines_ex(rl.Rectangle(4, 4, 468, 232), 0.12, 16, 8, color)
    finally:
      clip.end_scissor_mode()
    render_compact_half_borders(state, rl.get_time())

  def _stopped_timer(self, seconds: int) -> None:
    minutes, remainder = duration_text(seconds)
    color = rl.Color(*duration_color(seconds), 255)
    for text, role, initial_size, minimum_size, center_y, tint in (
      (minutes, FontRole.BOLD, 78, 28, 101, color),
      (remainder, FontRole.MEDIUM, 35, 16, 149, rl.Color(255, 255, 255, 242)),
    ):
      size = initial_size
      while size > minimum_size and self.fonts.measure(text, role, size).width > 440:
        size -= 2
      measured = self.fonts.measure(text, role, size)
      x = (476 - measured.width) / 2
      y = center_y - measured.height / 2
      self.fonts.draw(text, role, size, x + 2, y + 2, rl.Color(0, 0, 0, 170))
      self.fonts.draw(text, role, size, x, y, tint)

  def close(self) -> None:
    gui_app.remove_render_prepare(self._corner_cache.prepare)
    self._corner_cache.close()
    self.navigation.close()
    if self.fonts.profile == Profile.LARGE:
      self.steering_wheel.close()
    else:
      self.compact_hud.close()
      if self._fade is not None and rl.is_window_ready():
        rl.unload_texture(self._fade)
      self._fade = None
