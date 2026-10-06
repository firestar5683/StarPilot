"""Read-only large onroad composition for a separate projection frame."""

from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import time

from openpilot.starpilot.system.android_auto.projection_geometry import FALLBACK_VIEWPORT


def native_dependencies():
  import pyray as rl
  from openpilot.cereal.visionipc import VisionStreamType
  from openpilot.common.transformations.camera import view_frame_from_device_frame
  from openpilot.selfdrive.ui.onroad.augmented_road_view import AugmentedRoadView, BORDER_COLORS
  from openpilot.selfdrive.ui.onroad.cameraview import CameraView
  from openpilot.selfdrive.ui.onroad.model_renderer import ModelRenderer
  from openpilot.selfdrive.ui.ui_state import ui_state, UIStatus
  from openpilot.starpilot.ui.onroad import OnroadView
  from openpilot.starpilot.ui.onroad_customization import CAMERA_WIDGETS, placement, widget_size
  from openpilot.starpilot.ui.onroad_dm import DriverMonitorLayer
  from openpilot.starpilot.ui.pip_preferences import read_pip
  from openpilot.starpilot.ui.pip_render import PiPRenderer
  from openpilot.starpilot.ui.pip_sidecam import Rect, Signals
  from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile, default_font_directory
  from openpilot.starpilot.ui.runtime_snapshot import RuntimeSnapshotAdapter, current_message
  from openpilot.starpilot.ui.shell import ShellMode

  class ProjectionRoadCamera(AugmentedRoadView):
    """Current native calibrated camera/model without stock action widgets."""

    def __init__(self):
      stream = VisionStreamType.VISION_STREAM_NARROW_ROAD
      try:
        CameraView.__init__(self, 'camerad', stream)
        self._set_placeholder_color(BORDER_COLORS[UIStatus.DISENGAGED])
        self.device_camera = None
        self.view_from_calib = view_frame_from_device_frame.copy()
        self.view_from_wide_calib = view_frame_from_device_frame.copy()
        self._matrix_cache_key = (0, 0.0, 0.0, stream)
        self._cached_matrix = None
        self._content_rect = rl.Rectangle()
        self.model_renderer = ModelRenderer()
      except BaseException:
        callbacks = ui_state._offroad_transition_callbacks
        if self._offroad_transition in callbacks:
          callbacks.remove(self._offroad_transition)
        try:
          CameraView.close(self)
        except (AttributeError, RuntimeError):
          pass
        raise

  return SimpleNamespace(rl=rl, ui_state=ui_state, camera=ProjectionRoadCamera,
                         onroad=OnroadView, monitor=DriverMonitorLayer, fonts=BitmapFonts,
                         font_role=FontRole, profile=Profile, font_directory=default_font_directory,
                         adapter=RuntimeSnapshotAdapter, current_message=current_message,
                         shell_mode=ShellMode, pip_renderer=PiPRenderer, read_pip=read_pip, pip_signals=Signals,
                         pip_rect=Rect, pip_widgets=CAMERA_WIDGETS, placement=placement, widget_size=widget_size)


class ProjectionOnroad:
  """Display-only renderer: no shell, settings, network, pairing, or action owner."""

  def __init__(self, *, dependencies=None, viewport=None, customization=None):
    viewport = FALLBACK_VIEWPORT if viewport is None else viewport
    self.width, self.height = viewport
    self.customization = customization
    self._base_customization = None
    self._projection_customization = None
    self.camera_stream = None  # the camera stream the last frame drew, or None
    self.native = dependencies or native_dependencies()
    native = self.native
    if native.ui_state.projection_read_only is not True:
      raise RuntimeError('Projection UIState must be read-only')
    self._resources = ExitStack()
    try:
      self.fonts = native.fonts(native.profile.LARGE, native.font_directory(), headless_context=True)
      self._resources.callback(self.fonts.close)
      self.camera = native.camera()
      self._resources.callback(self._close_camera)
      self.onroad = self.create_view(native.onroad, self.fonts, camera_layer=self._camera_layer, viewport=viewport)
      self._resources.callback(self._close_onroad)
      self.monitor = native.monitor(native.profile.LARGE)
      self.onroad.driver_monitor_layer = self._driver_monitor_layer
      self.pip = None
      self._pip_saved = None
      self._pip_read_ns = None
      if getattr(native, 'pip_renderer', None) is not None:
        self.pip = native.pip_renderer("bubble")
        self._resources.callback(self.pip.close)
        self.onroad.pip_layer = self._pip_layer
      self.adapter = native.adapter(native.ui_state)
    except BaseException:
      self._resources.close()
      raise

  @staticmethod
  def create_view(view_factory, fonts, *, viewport, **layers):
    """Production AA composition, shared with the parked theme preview."""
    return view_factory(fonts, Path(__file__).parents[3] / 'selfdrive/assets',
                        projection_viewport=viewport, **layers)

  def _close_camera(self):
    callbacks = self.native.ui_state._offroad_transition_callbacks
    callback = self.camera._offroad_transition
    try:
      callbacks.remove(callback)
    except ValueError:
      pass
    self.camera.close()

  def _close_onroad(self):
    # Raylib's window-ready flag stays false for a valid headless EGL context.
    # The large steering wheel texture is owned by this view and must be freed.
    wheel = self.onroad.steering_wheel
    texture = getattr(wheel, '_texture', None)
    if texture is not None:
      self.native.rl.unload_texture(texture)
      wheel._texture = None
    self.onroad.close()

  def _camera_layer(self, rect, state):
    self.camera_stream = self.camera.stream_type
    self.camera.render_camera_model_layer(rect, road_style=state.customization['roadColors']['large'])

  def _driver_monitor_layer(self, rect, state):
    ui = self.native.ui_state
    now_ns = time.monotonic_ns()
    monitor = self.native.current_message(ui.sm, 'driverMonitoringState', now_ns, after_frame=ui.started_frame)
    driver = self.native.current_message(ui.sm, 'driverStateV2', now_ns, after_frame=ui.started_frame)
    self.native.rl.rl_push_matrix()
    self.native.rl.rl_translatef(0, self.height - 1080, 0)
    try:
      self.monitor.render(state, monitor=monitor, driver=driver,
                          fresh=monitor is not None and driver is not None,
                          onroad=ui.is_onroad())
    finally:
      self.native.rl.rl_pop_matrix()

  def _pip_layer(self, rect, state):
    """The comma's blinker/blind-spot side-camera bubbles, at the AA layout's placements."""
    native = self.native
    now_ns = time.monotonic_ns()
    if self._pip_read_ns is None or not 0 <= now_ns - self._pip_read_ns < 1_000_000_000:
      self._pip_saved = native.read_pip(native.ui_state.params)
      self._pip_read_ns = now_ns
    saved = self._pip_saved
    if (saved is None or saved.enabled is not True or saved.mask is None or
        saved.invert is None or saved.on_blinker is None or saved.on_bsm is None):
      self.pip.deactivate()
      return
    ui = native.ui_state
    car = native.current_message(ui.sm, 'carState', now_ns, after_frame=ui.started_frame)
    signals = native.pip_signals(car is not None,
                                 bool(car.leftBlinker) if car is not None else False,
                                 bool(car.rightBlinker) if car is not None else False,
                                 bool(car.leftBlindspot) if car is not None else False,
                                 bool(car.rightBlindspot) if car is not None else False)
    placements = {}
    for side, key in zip(('left', 'right'), native.pip_widgets, strict=True):
      position = native.placement(state.customization, 'large', key)
      if position['enabled']:
        width, height = native.widget_size(state.customization, 'large', key)
        placements[side] = native.pip_rect(position['x'], position['y'], width, height)
    self.pip.render(rect, saved.mask, signals, enabled=True, on_blinker=saved.on_blinker,
                    on_bsm=saved.on_bsm, invert=saved.invert, placements=placements)

  def _standby(self):
    rl = self.native.rl
    rl.draw_rectangle(0, 0, int(self.width), int(self.height), rl.Color(12, 26, 34, 255))
    rl.draw_rectangle_rounded(rl.Rectangle(120, 140, self.width - 240, self.height - 280), 0.06, 16, rl.Color(18, 40, 57, 255))
    rl.draw_rectangle_rounded_lines_ex(rl.Rectangle(120, 140, self.width - 240, self.height - 280), 0.06, 16, 4, rl.Color(50, 126, 144, 255))
    self.fonts.draw('StarPilot', self.native.font_role.BRAND, 112, 220, 325)
    self.fonts.draw('Ready when driving', self.native.font_role.MEDIUM, 55, 225, 475)

  def render(self):
    ui = self.native.ui_state
    self.camera_stream = None
    if ui.started:
      state = self.adapter.build(self.native.shell_mode.ONROAD, now_ns=time.monotonic_ns()).onroad
      if self.customization is not None:
        from openpilot.starpilot.system.android_auto.projection_layout import projection_customization
        if state.customization is not self._base_customization:
          self._projection_customization = projection_customization(self.customization, state.customization)
          self._base_customization = state.customization
        state = replace(state, customization=self._projection_customization)
      self.onroad.render(state)
      self.fonts.draw('StarPilot', self.native.font_role.BRAND, 30, self.width - 210, self.height - 90)
    else:
      if self.pip is not None:
        self.pip.deactivate()
      self._standby()

  def close(self):
    self._resources.close()
