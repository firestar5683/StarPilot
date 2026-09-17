import math
from enum import Enum

import pyray as rl

from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.selfdrive.ui.onroad.starpilot.widgets.base import LayoutWidget
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app


class ModelSourceStatus(Enum):
  LOADING = "loading"
  ACTIVE = "active"
  FAILED = "failed"
  FALLBACK_ENGAGED = "fallback_engaged"


class ModelSourceWidget(LayoutWidget):
  """Show the external-GPU model state with the same status semantics as Mici."""

  PERSISTENCE_SECONDS = 2.5
  # Mici uses a quarter-scale logical surface; preserve its physical icon size on Big UI.
  SCALE = 4
  ICON_SIZES = {
    ModelSourceStatus.LOADING: (60 * SCALE, 44 * SCALE),
    ModelSourceStatus.ACTIVE: (60 * SCALE, 44 * SCALE),
    ModelSourceStatus.FAILED: (75 * SCALE, 44 * SCALE),
    ModelSourceStatus.FALLBACK_ENGAGED: (60 * SCALE, 52 * SCALE),
  }
  ASSET_PATHS = {
    ModelSourceStatus.LOADING: "icons_mici/egpu_loading.png",
    ModelSourceStatus.ACTIVE: "icons_mici/egpu_green.png",
    ModelSourceStatus.FAILED: "icons_mici/egpu_orange.png",
    ModelSourceStatus.FALLBACK_ENGAGED: "icons_mici/egpu_crossed.png",
  }
  SIZE = (300.0, 208.0)

  def __init__(self):
    super().__init__("model_source", priority=1)
    self.set_enabled(False)
    self._small_model_engaged = False
    self._engaged = False
    self._fade_time = 0.0
    self._status: ModelSourceStatus | None = None
    self._shown_status: ModelSourceStatus | None = None
    self._alpha_filter = FirstOrderFilter(0.0, 0.1, 1 / gui_app.target_fps)
    self._textures = {
      status: gui_app.texture(path, *self.ICON_SIZES[status])
      for status, path in self.ASSET_PATHS.items()
    }

  @property
  def is_visible(self) -> bool:
    return ui_state.usbgpu and ui_state.usbgpu_compiled

  @property
  def blocks_pointer(self) -> bool:
    return False

  def get_size(self) -> tuple[float, float]:
    return self.SIZE

  @staticmethod
  def _big_model_failed(active: bool | None, usbgpu: bool, model_seen: bool, model_alive: bool,
                        pending: bool = False) -> bool:
    # A model that finished loading but is waiting for the driver to disengage is not a failure.
    if pending and usbgpu:
      return False
    return active is False or not usbgpu or (active is True and model_seen and not model_alive)

  @staticmethod
  def _status_for(loading: bool, small_model_engaged: bool, big_failed: bool,
                  pending: bool = False) -> ModelSourceStatus:
    # Pending means the big model finished loading and is waiting for the next disengage,
    # so the blinking loading icon stops: its absence is what tells the driver it is ready.
    if loading and not pending:
      return ModelSourceStatus.LOADING
    if small_model_engaged:
      return ModelSourceStatus.FALLBACK_ENGAGED
    if big_failed:
      return ModelSourceStatus.FAILED
    return ModelSourceStatus.ACTIVE

  def _update_state(self) -> None:
    sm = ui_state.sm
    if sm.recv_frame["selfdriveState"] < ui_state.started_frame:
      self._status = None
      return

    model_seen = sm.recv_frame["modelV2"] > ui_state.started_frame
    model_alive = sm.alive["modelV2"] if model_seen else True
    loading = ui_state.usbgpu_loading
    pending = ui_state.usbgpu_pending
    big_failed = self._big_model_failed(ui_state.usbgpu_active, ui_state.usbgpu, model_seen, model_alive, pending)
    engaged = sm["selfdriveState"].enabled

    if engaged and not self._engaged and not loading and not pending \
       and ui_state.usbgpu_active is not True and model_seen:
      self._small_model_engaged = True
    if engaged != self._engaged:
      self._fade_time = rl.get_time() if engaged else 0.0
    self._engaged = engaged
    self._small_model_engaged &= big_failed
    self._status = self._status_for(loading, self._small_model_engaged, big_failed, pending)

  def _render(self, rect: rl.Rectangle) -> None:
    if self._status is None:
      return

    status = self._status
    if status is ModelSourceStatus.LOADING:
      pulse = 0.5 - 0.5 * math.cos(rl.get_time() * 6.0)
      opacity = 0.35 + 0.65 * pulse
    elif status is ModelSourceStatus.FALLBACK_ENGAGED:
      opacity = 0.65
    else:
      opacity = 1.0

    if status is not self._shown_status:
      self._fade_time = rl.get_time()
      self._shown_status = status
    alpha = self._alpha_filter.update(
      status is ModelSourceStatus.LOADING or 0 < rl.get_time() - self._fade_time < self.PERSISTENCE_SECONDS
    )
    if alpha < 1e-2:
      return

    icon = self._textures[status]
    pos = rl.Vector2(
      rect.x + (rect.width - icon.width) / 2,
      rect.y + (rect.height - icon.height) / 2,
    )
    rl.draw_texture_ex(icon, pos, 0.0, 1.0, rl.Color(255, 255, 255, int(255 * opacity * alpha)))
