import time
import numpy as np
import pyray as rl
from cereal import messaging, car, log
from opendbc.car import structs
from msgq.visionipc import VisionStreamType
from openpilot.common.constants import CV
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.mici.onroad import SIDE_PANEL_WIDTH
from openpilot.selfdrive.ui.mici.onroad.alert_renderer import AlertRenderer, ALERT_COLORS, AlertStatus
from openpilot.selfdrive.ui.mici.onroad.driver_state import DriverStateRenderer
from openpilot.selfdrive.ui.mici.onroad.hud_renderer import HudRenderer
from openpilot.selfdrive.ui.mici.onroad.model_renderer import ModelRenderer
from openpilot.selfdrive.ui.mici.onroad.confidence_ball import ConfidenceBall
from openpilot.selfdrive.ui.mici.onroad.starpilot_status import (
  ENGAGED_COLOR,
  EXPERIMENTAL_COLOR,
  TRAFFIC_COLOR,
  get_border_color,
)
from openpilot.selfdrive.ui.lib.starpilot_mode_banner import ModeTransitionBanner
from openpilot.selfdrive.ui.mici.onroad.cameraview import CameraView
from openpilot.selfdrive.ui.lib.starpilot_visuals import get_border_width
from openpilot.system.ui.lib.application import FontWeight, gui_app, MousePos, MouseEvent
from openpilot.system.ui.widgets.label import UnifiedLabel
from openpilot.system.ui.widgets import Widget
from openpilot.common.filter_simple import BounceFilter
from openpilot.common.transformations.camera import DEVICE_CAMERAS, DeviceCameraConfig, view_frame_from_device_frame
from openpilot.common.transformations.orientation import rot_from_euler
from enum import IntEnum

OpState = log.SelfdriveState.OpenpilotState
CALIBRATED = log.LiveCalibrationData.Status.calibrated
ROAD_CAM = VisionStreamType.VISION_STREAM_ROAD
WIDE_CAM = VisionStreamType.VISION_STREAM_WIDE_ROAD
DRIVER_CAM = VisionStreamType.VISION_STREAM_DRIVER
GEAR_SHIFTER_REVERSE = structs.CarState.GearShifter.reverse
DEFAULT_DEVICE_CAMERA = DEVICE_CAMERAS["tici", "ar0231"]

CAMERA_VIEW_AUTO = 0
CAMERA_VIEW_DRIVER = 1
CAMERA_VIEW_STANDARD = 2
CAMERA_VIEW_WIDE = 3


class BookmarkState(IntEnum):
  HIDDEN = 0
  DRAGGING = 1
  TRIGGERED = 2

WIDE_CAM_MAX_SPEED = 10.0  # m/s
ROAD_CAM_MIN_SPEED = 15.0  # m/s

CAM_Y_OFFSET = 20
REVERSE_DRIVER_CAMERA_DELAY_FRAMES = max(1, int(round(gui_app.target_fps * 0.5)))


class BookmarkIcon(Widget):
  PEEK_THRESHOLD = 50  # If icon peeks out this much, snap it fully visible
  FULL_VISIBLE_OFFSET = 200  # How far onscreen when fully visible
  HIDDEN_OFFSET = -50  # How far offscreen when hidden

  def __init__(self, bookmark_callback):
    super().__init__()
    self._bookmark_callback = bookmark_callback
    self._icon = gui_app.texture("icons_mici/onroad/bookmark.png", 180, 180)
    self._offset_filter = BounceFilter(0.0, 0.1, 1 / gui_app.target_fps)

    # State
    self._interacting = False
    self._state = BookmarkState.HIDDEN
    self._swipe_start_x = 0.0
    self._swipe_current_x = 0.0
    self._is_swiping = False
    self._is_swiping_left: bool = False
    self._triggered_time: float = 0.0

  def is_swiping_left(self) -> bool:
    """Check if currently swiping left (for scroller to disable)."""
    return self._is_swiping_left

  def interacting(self):
    interacting, self._interacting = self._interacting, False
    return interacting

  def _update_state(self):
    if self._state == BookmarkState.DRAGGING:
      # Allow pulling past activated position with rubber band effect
      swipe_offset = self._swipe_start_x - self._swipe_current_x
      swipe_offset = min(swipe_offset, self.FULL_VISIBLE_OFFSET + 50)
      self._offset_filter.update(swipe_offset)

    elif self._state == BookmarkState.TRIGGERED:
      # Continue animating to fully visible
      self._offset_filter.update(self.FULL_VISIBLE_OFFSET)
      # Stay in TRIGGERED state for 1 second
      if rl.get_time() - self._triggered_time >= 1.5:
        self._state = BookmarkState.HIDDEN

    elif self._state == BookmarkState.HIDDEN:
      self._offset_filter.update(self.HIDDEN_OFFSET)

      if self._offset_filter.x < 1e-3:
        self._interacting = False

  def _handle_mouse_event(self, mouse_event: MouseEvent):
    if not ui_state.started:
      return

    if mouse_event.left_pressed:
      # Store relative position within widget
      self._swipe_start_x = mouse_event.pos.x
      self._swipe_current_x = mouse_event.pos.x
      self._is_swiping = True
      self._is_swiping_left = False
      self._state = BookmarkState.DRAGGING

    elif mouse_event.left_down and self._is_swiping:
      self._swipe_current_x = mouse_event.pos.x
      swipe_offset = self._swipe_start_x - self._swipe_current_x
      self._is_swiping_left = swipe_offset > 0
      if self._is_swiping_left:
        self._interacting = True

    elif mouse_event.left_released:
      if self._is_swiping:
        swipe_distance = self._swipe_start_x - self._swipe_current_x

        # If peeking past threshold, transition to animating to fully visible and bookmark
        if swipe_distance > self.PEEK_THRESHOLD:
          self._state = BookmarkState.TRIGGERED
          self._triggered_time = rl.get_time()
          self._bookmark_callback()
        else:
          # Otherwise, transition back to hidden
          self._state = BookmarkState.HIDDEN

        # Reset swipe state
        self._is_swiping = False
        self._is_swiping_left = False

  def _render(self, _):
    """Render the bookmark icon."""
    if self._offset_filter.x > 0:
      icon_x = self.rect.x + self.rect.width - round(self._offset_filter.x)
      icon_y = self.rect.y + (self.rect.height - self._icon.height) / 2  # Vertically centered
      rl.draw_texture(self._icon, int(icon_x), int(icon_y), rl.WHITE)


class MinSteerSpeedBanner(Widget):
  """One-shot-per-drive banner shown for the full first below-min-steer interval."""

  def __init__(self):
    super().__init__()
    self._shown_this_drive = False
    self._showing_interval = False
    self._has_been_above_min = False
    self._was_under_min = False
    self._last_started_frame = -1
    self._label = UnifiedLabel(
      "",
      34,
      FontWeight.BOLD,
      text_color=rl.WHITE,
      alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER,
      alignment_vertical=rl.GuiTextAlignmentVertical.TEXT_ALIGN_MIDDLE,
    )

  def _reset(self):
    self._shown_this_drive = False
    self._showing_interval = False
    self._has_been_above_min = False
    self._was_under_min = False

  @staticmethod
  def _get_message(min_steer_speed: float) -> str:
    speed_units = CV.MS_TO_KPH if ui_state.is_metric else CV.MS_TO_MPH
    speed = int(round(min_steer_speed * speed_units))
    unit = "km/h" if ui_state.is_metric else "mph"
    return f"Steer Unavailable Under {speed} {unit}"

  def _update_state(self):
    if not ui_state.started:
      self._last_started_frame = -1
      self._reset()
      return

    if ui_state.started_frame != self._last_started_frame:
      self._last_started_frame = ui_state.started_frame
      self._reset()

    sm = ui_state.sm
    if sm.recv_frame["carParams"] < ui_state.started_frame or sm.recv_frame["carState"] < ui_state.started_frame:
      return

    min_steer_speed = float(sm["carParams"].minSteerSpeed)
    if min_steer_speed <= 0:
      self._showing_interval = False
      self._was_under_min = False
      return

    under_min = float(sm["carState"].vEgo) < min_steer_speed
    if not under_min:
      self._has_been_above_min = True

    crossed_below = under_min and not self._was_under_min
    if (not self._shown_this_drive) and crossed_below and self._has_been_above_min:
      self._showing_interval = True
      self._shown_this_drive = True

    if self._showing_interval and not under_min:
      self._showing_interval = False

    self._was_under_min = under_min
    if self._showing_interval:
      self._label.set_text(self._get_message(min_steer_speed))

  def _render(self, rect):
    self._update_state()
    if not self._showing_interval:
      return

    color = ALERT_COLORS[AlertStatus.userPrompt]
    color = rl.Color(color.r, color.g, color.b, int(255 * 0.9))
    translucent = rl.Color(color.r, color.g, color.b, 0)
    dropdown_height = min(170, int(rect.height * 0.7))
    solid_height = max(26, int(dropdown_height * 0.2))

    rl.draw_rectangle(int(rect.x), int(rect.y), int(rect.width), solid_height, color)
    rl.draw_rectangle_gradient_v(
      int(rect.x),
      int(rect.y + solid_height),
      int(rect.width),
      int(dropdown_height - solid_height),
      color,
      translucent,
    )

    text_rect = rl.Rectangle(rect.x + 26, rect.y - 2, rect.width - 52, dropdown_height)
    self._label.set_text_color(rl.Color(255, 255, 255, 242))
    self._label.render(text_rect)


class StandstillTimerOverlay:
  def __init__(self):
    self._last_started_frame = -1
    self._standstill_duration = 0
    self._standstill_started_at: float | None = None
    self._font_bold = gui_app.font(FontWeight.BOLD)
    self._font_medium = gui_app.font(FontWeight.MEDIUM)

  def _reset(self):
    self._standstill_duration = 0
    self._standstill_started_at = None

  @staticmethod
  def _blend_colors(start: rl.Color, end: rl.Color, transition: float) -> rl.Color:
    transition = float(np.clip(transition, 0.0, 1.0))
    return rl.Color(
      int(start.r + transition * (end.r - start.r)),
      int(start.g + transition * (end.g - start.g)),
      int(start.b + transition * (end.b - start.b)),
      255,
    )

  def _get_duration_color(self) -> rl.Color:
    if self._standstill_duration < 60:
      return ENGAGED_COLOR
    if self._standstill_duration < 150:
      transition = (self._standstill_duration - 60) / 90.0
      return self._blend_colors(ENGAGED_COLOR, EXPERIMENTAL_COLOR, transition)
    if self._standstill_duration < 300:
      transition = (self._standstill_duration - 150) / 150.0
      return self._blend_colors(EXPERIMENTAL_COLOR, TRAFFIC_COLOR, transition)
    return TRAFFIC_COLOR

  def _update_state(self, in_reverse: bool) -> None:
    if not ui_state.started:
      self._last_started_frame = -1
      self._reset()
      return

    if ui_state.started_frame != self._last_started_frame:
      self._last_started_frame = ui_state.started_frame
      self._reset()

    if ui_state.sm.recv_frame["carState"] < ui_state.started_frame:
      self._reset()
      return

    if in_reverse or not ui_state.params.get_bool("StoppedTimer"):
      self._reset()
      return

    if not ui_state.sm["carState"].standstill:
      self._reset()
      return

    now = time.monotonic()
    if self._standstill_started_at is None:
      self._standstill_started_at = now
      self._standstill_duration = 0
      return

    if now - ui_state.started_time < 60.0:
      self._standstill_duration = 0
      return

    self._standstill_duration = int(now - self._standstill_started_at)

  @staticmethod
  def _format_duration_text(total_seconds: int) -> tuple[str, str]:
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    minute_text = f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"
    second_text = f"{seconds} second" if seconds == 1 else f"{seconds} seconds"
    return minute_text, second_text

  def _draw_centered_text(self, rect: rl.Rectangle, text: str, y: float, font: rl.Font, font_size: int, color: rl.Color) -> None:
    text_size = rl.measure_text_ex(font, text, font_size, 0)
    text_pos = rl.Vector2(rect.x + rect.width / 2 - text_size.x / 2, rect.y + y - text_size.y / 2)
    shadow_pos = rl.Vector2(text_pos.x + 2, text_pos.y + 2)
    rl.draw_text_ex(font, text, shadow_pos, font_size, 0, rl.Color(0, 0, 0, 170))
    rl.draw_text_ex(font, text, text_pos, font_size, 0, color)

  @staticmethod
  def _fit_font_size(font: rl.Font, text: str, initial_size: int, max_width: float, minimum_size: int) -> int:
    font_size = max(initial_size, minimum_size)
    while font_size > minimum_size and rl.measure_text_ex(font, text, font_size, 0).x > max_width:
      font_size -= 2
    return font_size

  def render(self, rect: rl.Rectangle, in_reverse: bool) -> bool:
    self._update_state(in_reverse)
    if self._standstill_duration == 0:
      return False

    minute_text, second_text = self._format_duration_text(self._standstill_duration)
    duration_color = self._get_duration_color()
    max_text_width = max(rect.width - 36, 120)
    minute_font_size = self._fit_font_size(self._font_bold, minute_text, int(rect.height * 0.34), max_text_width, 28)
    second_font_size = self._fit_font_size(self._font_medium, second_text, int(rect.height * 0.15), max_text_width, 16)
    self._draw_centered_text(rect, minute_text, rect.height * 0.42, self._font_bold, minute_font_size, duration_color)
    self._draw_centered_text(rect, second_text, rect.height * 0.62, self._font_medium, second_font_size, rl.Color(255, 255, 255, 242))
    return True


class AugmentedRoadView(CameraView):
  def __init__(self, bookmark_callback=None, stream_type: VisionStreamType = VisionStreamType.VISION_STREAM_ROAD):
    super().__init__("camerad", stream_type)
    self._bookmark_callback = bookmark_callback
    self._set_placeholder_color(rl.BLACK)

    self.device_camera: DeviceCameraConfig | None = None
    self.view_from_calib = view_frame_from_device_frame.copy()
    self.view_from_wide_calib = view_frame_from_device_frame.copy()

    self._last_calib_time: float = 0
    self._last_rect_dims = (0.0, 0.0)
    self._last_stream_type = stream_type
    self._cached_matrix: np.ndarray | None = None
    self._content_rect = rl.Rectangle()
    self._last_click_time = 0.0
    self._reverse_driver_camera_frames = 0
    self._reverse_driver_camera_active = False

    # Bookmark icon with swipe gesture
    self._bookmark_icon = BookmarkIcon(bookmark_callback)

    self._model_renderer = ModelRenderer()
    self._hud_renderer = HudRenderer()
    self._alert_renderer = AlertRenderer()
    self._driver_state_renderer = DriverStateRenderer()
    self._confidence_ball = ConfidenceBall()
    self._mode_transition_banner = ModeTransitionBanner()
    self._min_steer_speed_banner = MinSteerSpeedBanner()
    self._standstill_timer = StandstillTimerOverlay()
    self._offroad_label = UnifiedLabel("start the car to\nuse openpilot", 54, FontWeight.DISPLAY,
                                       text_color=rl.Color(255, 255, 255, int(255 * 0.9)),
                                       alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER,
                                       alignment_vertical=rl.GuiTextAlignmentVertical.TEXT_ALIGN_MIDDLE)

    self._fade_texture = gui_app.texture("icons_mici/onroad/onroad_fade.png")

    # debug
    self._pm = messaging.PubMaster(['uiDebug'])

  @staticmethod
  def _controls_ready() -> bool:
    return ui_state.sm.recv_frame["selfdriveState"] >= ui_state.started_frame

  def _update_reverse_driver_camera_state(self) -> bool:
    should_force_driver = ui_state.started and ui_state.params.get_bool("DriverCamera") and self._is_in_reverse()
    if not should_force_driver:
      self._reverse_driver_camera_frames = 0
      self._reverse_driver_camera_active = False
      return False

    self._reverse_driver_camera_frames = min(self._reverse_driver_camera_frames + 1, REVERSE_DRIVER_CAMERA_DELAY_FRAMES)
    self._reverse_driver_camera_active = self._reverse_driver_camera_frames >= REVERSE_DRIVER_CAMERA_DELAY_FRAMES
    return self._reverse_driver_camera_active

  def is_swiping_left(self) -> bool:
    """Check if currently swiping left (for scroller to disable)."""
    return self._bookmark_icon.is_swiping_left()

  def _update_state(self):
    super()._update_state()

    # update offroad label
    if ui_state.panda_type == log.PandaState.PandaType.unknown:
      self._offroad_label.set_text("system booting")
    elif ui_state.started and not self._controls_ready():
      self._offroad_label.set_text("waiting for\ncontrols to start")
    else:
      self._offroad_label.set_text("start the car to\nuse openpilot")

  def _handle_mouse_release(self, mouse_pos: MousePos):
    # Don't trigger click callback if bookmark was triggered
    if not self._bookmark_icon.interacting():
      super()._handle_mouse_release(mouse_pos)

  def _render(self, _):
    start_draw = time.monotonic()
    self._switch_stream_if_needed(ui_state.sm)

    # Update calibration before rendering
    self._update_calibration()

    # Create inner content area with border padding
    self._content_rect = rl.Rectangle(
      self.rect.x,
      self.rect.y,
      self.rect.width - SIDE_PANEL_WIDTH,
      self.rect.height,
    )

    # Enable scissor mode to clip all rendering within content rectangle boundaries
    # This creates a rendering viewport that prevents graphics from drawing outside the border
    rl.begin_scissor_mode(
      int(self._content_rect.x),
      int(self._content_rect.y),
      int(self._content_rect.width),
      int(self._content_rect.height)
    )

    # Render the base camera view
    super()._render(self._content_rect)

    waiting_for_controls = ui_state.started and not self._controls_ready()
    if waiting_for_controls:
      rl.draw_rectangle(int(self._content_rect.x), int(self._content_rect.y),
                        int(self._content_rect.width), int(self._content_rect.height),
                        rl.Color(0, 0, 0, 145))
      self._offroad_label.render(self._content_rect)
      rl.end_scissor_mode()
      self._draw_border()
      self._bookmark_icon.render(self.rect)

      msg = messaging.new_message('uiDebug')
      msg.uiDebug.drawTimeMillis = (time.monotonic() - start_draw) * 1000
      self._pm.send('uiDebug', msg)
      return

    in_reverse = self._is_in_reverse()
    is_driver_stream = self.stream_type == DRIVER_CAM
    self._hud_renderer.prepare(self._content_rect)

    # Draw all UI overlays
    if not in_reverse and not is_driver_stream:
      self._model_renderer.render(self._content_rect)

    # Fade out bottom of overlays for looks
    rl.draw_texture_ex(self._fade_texture, rl.Vector2(self._content_rect.x, self._content_rect.y), 0.0, 1.0, rl.WHITE)
    if not in_reverse and not is_driver_stream:
      self._hud_renderer.render_background()

    alert_to_render, not_animating_out = self._alert_renderer.will_render()

    should_draw_dmoji = ui_state.is_onroad() and (
      is_driver_stream or ((not in_reverse) and (not self._hud_renderer.drawing_top_icons()))
    )
    self._driver_state_renderer.set_should_draw(should_draw_dmoji)
    self._driver_state_renderer.set_position(self._rect.x + 16, self._rect.y + 10)
    if is_driver_stream or not in_reverse:
      self._driver_state_renderer.render()

    self._hud_renderer.set_can_draw_top_icons((not in_reverse) and (not is_driver_stream) and (alert_to_render is None))
    self._hud_renderer.set_wheel_critical_icon((not in_reverse) and (not is_driver_stream) and alert_to_render is not None and not not_animating_out and
                                               alert_to_render.visual_alert == car.CarControl.HUDControl.VisualAlert.steerRequired)
    self._mode_transition_banner.update()
    # TODO: have alert renderer draw offroad mici label below
    if ui_state.started:
      self._alert_renderer.render(self._content_rect)
    if not in_reverse and not is_driver_stream:
      self._hud_renderer.render_foreground()
    if (not in_reverse) and (not is_driver_stream) and alert_to_render is None:
      self._mode_transition_banner.render(self._content_rect)
    rendered_standstill_timer = False
    if not in_reverse and not is_driver_stream:
      rendered_standstill_timer = self._standstill_timer.render(self._content_rect, in_reverse)
    if not in_reverse and not is_driver_stream and not rendered_standstill_timer:
      self._min_steer_speed_banner.render(self._content_rect)

    # End clipping region
    rl.end_scissor_mode()

    # Custom UI extension point - add custom overlays here
    # Use self._content_rect for positioning within camera bounds
    if not in_reverse and not is_driver_stream:
      self._confidence_ball.render(self.rect)
    if is_driver_stream or not in_reverse:
      self._draw_border()

    self._bookmark_icon.render(self.rect)

    # Draw darkened background and text if not onroad
    if not ui_state.started:
      rl.draw_rectangle(int(self.rect.x), int(self.rect.y), int(self.rect.width), int(self.rect.height), rl.Color(0, 0, 0, 175))
      self._offroad_label.render(self._content_rect)

    # publish uiDebug
    msg = messaging.new_message('uiDebug')
    msg.uiDebug.drawTimeMillis = (time.monotonic() - start_draw) * 1000
    self._pm.send('uiDebug', msg)

  def _draw_border(self):
    border_size = self._get_border_width()
    # Keep full border visible by drawing outside scissor with an inset rect.
    border_rect = rl.Rectangle(
      self._content_rect.x + border_size / 2,
      self._content_rect.y + border_size / 2,
      self._content_rect.width - border_size,
      self._content_rect.height - border_size,
    )
    rl.draw_rectangle_rounded_lines_ex(border_rect, 0.12, 16, border_size, get_border_color(ui_state))

  def _get_border_width(self) -> int:
    return get_border_width(8, ui_state.params)

  @staticmethod
  def _is_in_reverse() -> bool:
    if ui_state.sm.recv_frame["carState"] < ui_state.started_frame:
      return False

    try:
      gear = ui_state.sm["carState"].gearShifter
    except Exception:
      return False

    if gear == GEAR_SHIFTER_REVERSE:
      return True

    reverse_enum = getattr(car.CarState.GearShifter, "reverse", None)
    if reverse_enum is not None and gear == reverse_enum:
      return True

    return str(gear).split(".")[-1].lower() == "reverse"

  def is_in_reverse(self) -> bool:
    return self._is_in_reverse()

  def _switch_stream_if_needed(self, sm):
    if self._update_reverse_driver_camera_state():
      target = DRIVER_CAM
      if self.stream_type != target:
        self.switch_stream(target)
      return

    camera_view = ui_state.params.get_int("CameraView", return_default=True, default=CAMERA_VIEW_WIDE)
    if camera_view not in (CAMERA_VIEW_AUTO, CAMERA_VIEW_DRIVER, CAMERA_VIEW_STANDARD, CAMERA_VIEW_WIDE):
      camera_view = CAMERA_VIEW_WIDE

    if camera_view == CAMERA_VIEW_DRIVER:
      target = DRIVER_CAM
    elif camera_view == CAMERA_VIEW_STANDARD:
      target = ROAD_CAM
    elif camera_view == CAMERA_VIEW_WIDE:
      target = WIDE_CAM if WIDE_CAM in self.available_streams else ROAD_CAM
    elif sm['selfdriveState'].experimentalMode and WIDE_CAM in self.available_streams:
      v_ego = sm['carState'].vEgo
      if v_ego < WIDE_CAM_MAX_SPEED:
        target = WIDE_CAM
      elif v_ego > ROAD_CAM_MIN_SPEED:
        target = ROAD_CAM
      else:
        # Hysteresis zone - keep the current road camera selection.
        target = WIDE_CAM if self.stream_type == WIDE_CAM else ROAD_CAM
    else:
      target = ROAD_CAM

    if self.stream_type != target:
      self.switch_stream(target)

  def _update_calibration(self):
    # Update device camera if not already set
    sm = ui_state.sm
    if not self.device_camera and sm.seen['roadCameraState'] and sm.seen['deviceState']:
      self.device_camera = DEVICE_CAMERAS[(str(sm['deviceState'].deviceType), str(sm['roadCameraState'].sensor))]

    # Check if live calibration data is available and valid
    if not (sm.updated["liveCalibration"] and sm.valid['liveCalibration']):
      return

    calib = sm['liveCalibration']
    if len(calib.rpyCalib) != 3 or calib.calStatus != CALIBRATED:
      return

    # Update view_from_calib matrix
    device_from_calib = rot_from_euler(calib.rpyCalib)
    self.view_from_calib = view_frame_from_device_frame @ device_from_calib

    # Update wide calibration if available
    if hasattr(calib, 'wideFromDeviceEuler') and len(calib.wideFromDeviceEuler) == 3:
      wide_from_device = rot_from_euler(calib.wideFromDeviceEuler)
      self.view_from_wide_calib = view_frame_from_device_frame @ wide_from_device @ device_from_calib

  def _calc_frame_matrix(self, rect: rl.Rectangle) -> np.ndarray:
    if self.stream_type == DRIVER_CAM:
      return CameraView._calc_frame_matrix(self, rect)

    # Get camera configuration
    # TODO: cache with vEgo?
    calib_time = ui_state.sm.recv_frame['liveCalibration']
    current_dims = (self._content_rect.width, self._content_rect.height)
    device_camera = self.device_camera or DEFAULT_DEVICE_CAMERA
    is_wide_camera = self.stream_type == WIDE_CAM
    intrinsic = device_camera.ecam.intrinsics if is_wide_camera else device_camera.fcam.intrinsics
    calibration = self.view_from_wide_calib if is_wide_camera else self.view_from_calib
    if is_wide_camera:
      zoom = 0.7 * 1.5
    else:
      zoom = np.interp(ui_state.sm['carState'].vEgo, [10, 30], [0.8, 1.0])

    # Calculate transforms for vanishing point
    inf_point = np.array([1000.0, 0.0, 0.0])
    calib_transform = intrinsic @ calibration
    kep = calib_transform @ inf_point

    # Calculate center points and dimensions
    x, y = self._content_rect.x, self._content_rect.y
    w, h = self._content_rect.width, self._content_rect.height
    cx, cy = intrinsic[0, 2], intrinsic[1, 2]

    # Ensure zoom views the whole area
    zoom = max(zoom, w / (2 * cx), h / (2 * cy))

    # Calculate max allowed offsets with margins
    margin = 5
    max_x_offset = max(0.0, cx * zoom - w / 2 - margin)
    max_y_offset = max(0.0, cy * zoom - h / 2 - margin)

    # Calculate and clamp offsets to prevent out-of-bounds issues
    try:
      if abs(kep[2]) > 1e-6:
        x_offset = np.clip((kep[0] / kep[2] - cx) * zoom, -max_x_offset, max_x_offset)
        y_offset = np.clip((kep[1] / kep[2] - cy) * zoom + CAM_Y_OFFSET, -max_y_offset, max_y_offset)
      else:
        x_offset, y_offset = 0, 0
    except (ZeroDivisionError, OverflowError):
      x_offset, y_offset = 0, 0

    # Cache the computed transformation matrix to avoid recalculations
    self._last_calib_time = calib_time
    self._last_rect_dims = current_dims
    self._last_stream_type = self.stream_type
    self._cached_matrix = np.array([
      [zoom * 2 * cx / w, 0, -x_offset / w * 2],
      [0, zoom * 2 * cy / h, -y_offset / h * 2],
      [0, 0, 1.0]
    ])

    video_transform = np.array([
      [zoom, 0.0, (w / 2 + x - x_offset) - (cx * zoom)],
      [0.0, zoom, (h / 2 + y - y_offset) - (cy * zoom)],
      [0.0, 0.0, 1.0]
    ])
    self._model_renderer.set_transform(video_transform @ calib_transform)

    return self._cached_matrix


if __name__ == "__main__":
  gui_app.init_window("OnRoad Camera View")
  road_camera_view = AugmentedRoadView(ROAD_CAM)
  print("***press space to switch camera view***")
  try:
    for _ in gui_app.render():
      ui_state.update()
      if rl.is_key_released(rl.KeyboardKey.KEY_SPACE):
        if WIDE_CAM in road_camera_view.available_streams:
          stream = ROAD_CAM if road_camera_view.stream_type == WIDE_CAM else WIDE_CAM
          road_camera_view.switch_stream(stream)
      road_camera_view.render(rl.Rectangle(0, 0, gui_app.width, gui_app.height))
  finally:
    road_camera_view.close()
