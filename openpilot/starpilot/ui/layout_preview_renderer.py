"""Parked onroad layout preview using the same native view as the driving UI."""

from pathlib import Path
import struct
import time
from openpilot.common.filter_simple import FirstOrderFilter
import zlib

import numpy as np
import pyray as rl

from openpilot.starpilot.ui.developer_preview import OnroadVisualPreview
from openpilot.starpilot.ui.onroad_customization import PROFILES, placement, validate_document
from openpilot.starpilot.ui.onroad_widget_style import draw_widget_frame
from openpilot.starpilot.ui.onroad_state import AlertSize, ObservationKind, OnroadAlert, OnroadState, SpeedLimitObservation
from openpilot.starpilot.ui.appearance_preferences import CameraViewChoice, OnroadAppearance
from openpilot.starpilot.ui.onroad_dm import monitor_visible
from openpilot.starpilot.ui.layout_preview_sidebar import SIDEBAR_WIDTH, render_sidebar
from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile, default_font_directory
from openpilot.starpilot.ui.wheel_feedback import WheelFeedback
from openpilot.starpilot.ui.rainbow_path import RainbowPath
from openpilot.starpilot.ui.road_colors import edge_gradient, lane_color, path_mode, solid_gradient
from openpilot.starpilot.ui.onroad_customization import ROAD_COLORS
from openpilot.system.ui.lib.shader_polygon import Gradient, draw_polygon


CEM_SCENE_REASONS = {"cem_stop_light": "STOP LIGHT", "cem_lead": "LEAD", "cem_curve": "CURVE"}
SCENES = ("engaged", "aol", "long_only", "experimental", "braking", "slc_pending", *CEM_SCENE_REASONS)
IDLE_SECONDS = 30.0
ASSET_DIRECTORY = Path(__file__).parents[2] / "selfdrive/assets"


def render_sample_road(rect: rl.Rectangle, state: OnroadState, profile: Profile) -> None:
  style = state.customization["roadColors"][str(profile)]

  def points(values):
    return np.array([(rect.x + x * rect.width, rect.y + y * rect.height) for x, y in values], dtype=np.float32)

  draw_polygon(rect, points([(0, 1), (.4, .45), (.55, .45), (.83, 1)]), rl.Color(48, 57, 67, 255))
  if profile == Profile.LARGE and "pathEdge" in style:
    for strip in ([(.18, 1), (.44, .45), (.447, .45), (.231, 1)],
                  [(.639, 1), (.503, .45), (.51, .45), (.69, 1)]):
      draw_polygon(rect, points(strip), gradient=edge_gradient(style["pathEdge"]))
    path = [(.231, 1), (.447, .45), (.503, .45), (.639, 1)]
  else:
    path = [(.18, 1), (.44, .45), (.51, .45), (.69, 1)]
  mode = path_mode(style, False)
  gradient = (RainbowPath().gradient() if mode == "rainbow" else
              solid_gradient(style.get("path", ROAD_COLORS["path"])) if mode == "color" else
              Gradient((0, 1), (0, 0), [rl.Color(13, 248, 122, 102), rl.Color(114, 255, 92, 89),
                                       rl.Color(114, 255, 92, 0)], [0, .5, 1]))
  draw_polygon(rect, points(path), gradient=gradient)
  for index, (bottom, top) in enumerate(((.16, .43), (.71, .52), (.02, .38), (.85, .57))):
    adjacent = profile == Profile.COMPACT and index < 2
    default = rl.Color(0, 255, 64, 178) if adjacent else rl.Color(255, 255, 255, 178)
    line = [(bottom - .002, 1), (top - .0005, .45), (top + .0005, .45), (bottom + .002, 1)]
    draw_polygon(rect, points(line), lane_color(style, adjacent, default, .7))


def sample_state(scene: str, document: dict) -> OnroadState:
  if scene not in SCENES:
    raise ValueError("Unknown layout preview scene")
  lateral = scene in ("engaged", "aol", "experimental", "braking", "slc_pending") or scene in CEM_SCENE_REASONS
  longitudinal = scene in ("engaged", "long_only", "experimental", "braking", "slc_pending") or scene in CEM_SCENE_REASONS
  return OnroadState(engaged=lateral or longitudinal, camera_available=False,
                     speed_mps=0.0 if scene == "cem_lead" else 22.0, cruise_kph=88.0,
                     speed_limit=SpeedLimitObservation(kind=ObservationKind.VALID, source="sample", speed_limit_mps=24.6,
                                                       pending_speed_limit_mps=20.0 if scene == "slc_pending" else None,
                                                       session_id="preview" if scene == "slc_pending" else None,
                                                       decision_id=1, presentation_id=1, action_enabled=scene == "slc_pending"),
                     alert=OnroadAlert(), appearance=OnroadAppearance(wheel_pedal_feedback=True,
                                                                      show_speed_limit_sign=True),
                     wheel_feedback=WheelFeedback(brake_pressed=scene == "braking"),
                     metric=False, experimental_available=True,
                     experimental_enabled=scene == "experimental" or scene in CEM_SCENE_REASONS, lateral_active=lateral,
                     longitudinal_active=longitudinal, stock_cruise_active=False,
                     slc_system_long_available=longitudinal, torque_utilization=0.78 if lateral else 0.0,
                     customization=document,
                     visual_preview=OnroadVisualPreview(cem_reason=CEM_SCENE_REASONS[scene]) if scene in CEM_SCENE_REASONS else None)


def _chunk(kind: bytes, data: bytes) -> bytes:
  payload = kind + data
  return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xffffffff)


def _png_rgba(width: int, height: int, pixels: bytes) -> bytes:
  if len(pixels) != width * height * 4:
    raise ValueError("Invalid layout preview pixel buffer")
  stride = width * 4
  rows = b"".join(b"\0" + pixels[y * stride:(y + 1) * stride] for y in range(height))
  return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) +
          _chunk(b"IDAT", zlib.compress(rows, 3)) + _chunk(b"IEND", b""))


class _DriverMonitorArt:
  def __init__(self, profile: Profile):
    from openpilot.selfdrive.ui.mici.onroad.driver_state import DriverStateRenderer

    self.profile = profile
    self.textures: dict[str, rl.Texture] = {}
    self.renderer = DriverStateRenderer.__new__(DriverStateRenderer)
    self.renderer._lines = False
    self.renderer._is_active = True
    self.renderer._force_active = False
    self.renderer._awareness_unfull = False
    self.renderer._fade_filter = FirstOrderFilter(1.0, 0.05, 1 / 60)
    self.renderer._rotation_filter = FirstOrderFilter(90.0, 0.05, 1 / 60)
    self.renderer._color_fade_filter = FirstOrderFilter(1.0, 0.05, 1 / 60)
    directory = ASSET_DIRECTORY / "icons_mici/onroad/driver_monitoring"
    try:
      for name in ("dm_background", "dm_person", "dm_cone"):
        image = rl.load_image(str(directory / f"{name}.png"))
        try:
          size = 128 if profile == Profile.LARGE else 60
          if name != "dm_background":
            size = round(52 / 60 * size)
          rl.image_resize(image, size, size)
          texture = rl.load_texture_from_image(image)
        finally:
          rl.unload_image(image)
        if not texture.id:
          raise RuntimeError(f"Unable to load driver monitoring artwork: {name}")
        self.textures[name] = texture
      self.renderer._dm_background = self.textures["dm_background"]
      self.renderer._dm_person = self.textures["dm_person"]
      self.renderer._dm_cone = self.textures["dm_cone"]
    except Exception:
      self.close()
      raise

  def render(self, _content: rl.Rectangle, state: OnroadState, *, top_icons: bool = False) -> None:
    position = placement(state.customization, self.profile, "driver_monitor")
    if not monitor_visible(self.profile, state, fresh=True, onroad=True, top_icons=top_icons):
      return
    size = 128 if self.profile == Profile.LARGE else 60
    x = position["x"] + (192 - size) / 2 if self.profile == Profile.LARGE else position["x"]
    y = position["y"] + (192 - size) / 2 if self.profile == Profile.LARGE else position["y"]
    self.renderer._rect = rl.Rectangle(x, y, size, size)
    widget = PROFILES[str(self.profile)]["widgets"]["driver_monitor"]
    draw_widget_frame(rl.Rectangle(position["x"], position["y"], widget["width"], widget["height"]),
                      state.customization, self.profile, "driver_monitor")
    self.renderer._render(self.renderer._rect)

  def close(self) -> None:
    if rl.is_window_ready():
      for texture in self.textures.values():
        rl.unload_texture(texture)
    self.textures.clear()


class _Canvas:
  def __init__(self, profile: Profile, viewport=None):
    from openpilot.starpilot.ui.onroad import OnroadView

    self.profile = profile
    self.viewport = viewport
    self.fonts: BitmapFonts | None = None
    self.view: OnroadView | None = None
    self.monitor: _DriverMonitorArt | None = None
    self.target: rl.RenderTexture | None = None
    try:
      self.fonts = BitmapFonts(profile, default_font_directory())
      layers = {'background_layer': lambda rect, state: render_sample_road(rect, state, profile)}
      if viewport is None:
        self.view = OnroadView(self.fonts, ASSET_DIRECTORY, background_layer=layers['background_layer'])
      else:
        from openpilot.starpilot.system.android_auto.projection_onroad import ProjectionOnroad
        self.view = ProjectionOnroad.create_view(OnroadView, self.fonts, viewport=viewport, **layers)
      self.monitor = _DriverMonitorArt(profile)
      self.view.driver_monitor_layer = self._render_driver_monitor
      self.target = rl.load_render_texture(*(viewport or profile.size))
      if not self.target.id:
        raise RuntimeError("Unable to create layout preview target")
    except Exception:
      self.close()
      raise

  def _render_driver_monitor(self, rect: rl.Rectangle, state: OnroadState) -> None:
    top_icons = (self.profile == Profile.COMPACT and state.alert.size == AlertSize.NONE and
                 state.appearance.camera_view != CameraViewChoice.DRIVER and not state.reverse_driver_camera and
                 not state.appearance.hide_max_speed and self.view.compact_hud._set_speed_alpha.x > 0.01 and
                 placement(state.customization, self.profile, "max_speed")["enabled"])
    if self.viewport is None:
      self.monitor.render(rect, state, top_icons=top_icons)
    else:
      rl.rl_push_matrix()
      rl.rl_translatef(0, self.viewport[1] - 1080, 0)
      try:
        self.monitor.render(rect, state, top_icons=top_icons)
      finally:
        rl.rl_pop_matrix()

  def render(self, state: OnroadState, scene: str) -> bytes:
    if self.view is None or self.fonts is None or self.target is None:
      raise RuntimeError("Layout preview resources are closed")
    self._settle(state)
    width, height = self.viewport or self.profile.size
    rl.begin_texture_mode(self.target)
    try:
      rl.clear_background(rl.BLACK)
      self.view.render(state)
      if self.profile == Profile.LARGE and self.viewport is None:
        render_sidebar(self.fonts, rl.Rectangle(width - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, height))
      self._label(scene)
    finally:
      rl.end_texture_mode()
    image = rl.load_image_from_texture(self.target.texture)
    try:
      rl.image_format(image, rl.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8)
      rl.image_flip_vertical(image)
      scale = min(1.0, 2560 / width, 1440 / height)
      if scale < 1.0:
        width, height = round(width * scale), round(height * scale)
        rl.image_resize(image, width, height)
      return _png_rgba(width, height, bytes(rl.ffi.buffer(image.data, width * height * 4)))
    finally:
      rl.unload_image(image)

  def _settle(self, state: OnroadState) -> None:
    if self.view is None:
      return
    if self.profile == Profile.COMPACT:
      hud = self.view.compact_hud
      hud._was_cruise_active = state.cruise_active
      hud._set_speed_alpha.x = 1.0 if state.cruise_active else 0.0
      hud._wheel_alpha.x = 255 * 0.9 if state.lateral_active else 0.0
      hud._wheel_y.x = 0.0 if state.lateral_active else 25.0
    self.view.torque_bar._torque_filter.x = state.torque_utilization if state.lateral_active else 0.0
    self.view.torque_bar._alpha_filter.x = 1.0 if state.lateral_active else 0.0

  def _label(self, scene: str) -> None:
    if self.fonts is None:
      return
    large = self.profile == Profile.LARGE
    names = {"experimental": "MANUAL EXPERIMENTAL", "cem_stop_light": "CEM TRAFFIC LIGHT",
             "cem_lead": "CEM STOPPED LEAD", "cem_curve": "CEM CURVE"}
    label = "SAMPLE: " + names.get(scene, scene.replace("_", " ").upper())
    size = 27 if large else 14
    measured = self.fonts.measure(label, FontRole.SEMI_BOLD, size)
    x = (1860 if large else 476) - measured.width - (38 if large else 8)
    y = 1000 if large else 213
    rl.draw_rectangle_rounded(rl.Rectangle(x - 8, y - 3, measured.width + 16, measured.height + 6),
                              0.2, 4, rl.Color(0, 0, 0, 220))
    self.fonts.draw(label, FontRole.SEMI_BOLD, size, x, y, rl.Color(255, 255, 255, 255))

  def close(self) -> None:
    if self.target is not None and rl.is_window_ready():
      rl.unload_render_texture(self.target)
    self.target = None
    if self.monitor is not None:
      self.monitor.close()
    self.monitor = None
    if self.view is not None:
      self.view.close()
    self.view = None
    if self.fonts is not None:
      self.fonts.close()
    self.fonts = None


class LayoutPreviewRenderer:
  def __init__(self):
    self._canvas: _Canvas | None = None
    self._last_use = 0.0

  @property
  def has_resources(self) -> bool:
    return self._canvas is not None

  def __call__(self, payload: dict) -> bytes:
    if type(payload) is not dict or set(payload) != {"document", "profile", "scene"}:
      raise ValueError("Invalid layout preview request")
    viewport = None
    if payload['profile'] == 'projection':
      from openpilot.starpilot.system.android_auto.projection_layout import projection_customization
      layout = payload['document']['layout']
      viewport = (layout['canvas']['width'], layout['canvas']['height'])
      document = projection_customization(layout, validate_document(payload['document']['base']))
    else:
      document = validate_document(payload['document'])
    if type(payload["profile"]) is not str or payload["profile"] not in ("large", "compact", "projection"):
      raise ValueError("Invalid layout preview profile")
    profile = Profile.LARGE if viewport else Profile(payload["profile"])
    scene = payload["scene"]
    state = sample_state(scene, document)
    if not rl.is_window_ready():
      raise RuntimeError("Layout preview requires the UI graphics context")
    if self._canvas is None or self._canvas.profile != profile or self._canvas.viewport != viewport:
      self.close()
      self._canvas = _Canvas(profile, viewport)
    self._last_use = time.monotonic()
    return self._canvas.render(state, scene)

  def expire(self) -> None:
    if self._canvas is not None and time.monotonic() - self._last_use >= IDLE_SECONDS:
      self.close()

  def close(self) -> None:
    if self._canvas is not None:
      self._canvas.close()
    self._canvas = None
