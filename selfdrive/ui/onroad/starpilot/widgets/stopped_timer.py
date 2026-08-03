import time
from collections.abc import Callable

import pyray as rl

from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.lib.starpilot_status import (
  ENGAGED_COLOR, EXPERIMENTAL_COLOR, TRAFFIC_COLOR,
)
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget


class StoppedTimerWidget(Widget):
  SHOW_AFTER_SECONDS = 60

  def __init__(self, in_reverse: Callable[[], bool] | None = None):
    super().__init__()
    self.set_enabled(False)
    self._in_reverse = in_reverse or (lambda: False)
    self._font_bold = gui_app.font(FontWeight.BOLD)
    self._font_normal = gui_app.font(FontWeight.NORMAL)
    self._standstill_started_at: float | None = None
    self._started_frame = -1
    self._duration = 0

  @property
  def is_visible(self) -> bool:
    return self._update_timer() > 0

  @property
  def replaces_current_speed(self) -> bool:
    return self.is_visible

  def _update_timer(self) -> int:
    started_frame = getattr(ui_state, "started_frame", 0)
    if started_frame != self._started_frame:
      self._started_frame = started_frame
      self._reset_timer()

    params = ui_state.ui_params
    if (not ui_state.started or
        not params.get_bool("QOLVisuals") or
        not params.get_bool("StoppedTimer") or
        not ui_state.sm.valid.get("carState", False)):
      self._reset_timer()
      return 0

    if self._in_reverse():
      self._reset_timer()
      return 0

    try:
      if ui_state.sm.recv_frame["carState"] < started_frame:
        self._reset_timer()
        return 0
    except (AttributeError, KeyError, TypeError):
      pass

    if not getattr(ui_state.sm["carState"], "standstill", False):
      self._reset_timer()
      return 0

    now = time.monotonic()
    if self._standstill_started_at is None:
      self._standstill_started_at = now

    if now - getattr(ui_state, "started_time", 0.0) < self.SHOW_AFTER_SECONDS:
      self._duration = 0
      return 0

    self._duration = max(0, int(now - self._standstill_started_at))
    return self._duration

  def _reset_timer(self) -> None:
    self._standstill_started_at = None
    self._duration = 0

  @staticmethod
  def _format_duration_text(duration: int) -> tuple[str, str]:
    minutes = duration // 60
    seconds = duration % 60
    return (
      f"{minutes} minute{'s' if minutes != 1 else ''}",
      f"{seconds} second{'s' if seconds != 1 else ''}",
    )

  def _render(self, rect: rl.Rectangle) -> None:
    duration = self._duration
    minute_text, second_text = self._format_duration_text(duration)

    minute_size = measure_text_cached(self._font_bold, minute_text, 176)
    second_size = measure_text_cached(self._font_normal, second_text, 66)

    if duration < 150:
      transition = (duration - 60) / 90.0
      duration_color = self._blend_colors(ENGAGED_COLOR, EXPERIMENTAL_COLOR, transition)
    elif duration < 300:
      transition = (duration - 150) / 150.0
      duration_color = self._blend_colors(EXPERIMENTAL_COLOR, TRAFFIC_COLOR, transition)
    else:
      duration_color = TRAFFIC_COLOR

    center_x = rect.x + rect.width / 2
    rl.draw_text_ex(
      self._font_bold,
      minute_text,
      rl.Vector2(center_x - minute_size.x / 2, rect.y + 210 - minute_size.y),
      176,
      0,
      duration_color,
    )
    rl.draw_text_ex(
      self._font_normal,
      second_text,
      rl.Vector2(center_x - second_size.x / 2, rect.y + 290 - second_size.y),
      66,
      0,
      rl.Color(255, 255, 255, 255),
    )

  @staticmethod
  def _blend_colors(start: rl.Color, end: rl.Color, transition: float) -> rl.Color:
    transition = min(max(transition, 0.0), 1.0)
    return rl.Color(
      int(start.r + transition * (end.r - start.r)),
      int(start.g + transition * (end.g - start.g)),
      int(start.b + transition * (end.b - start.b)),
      255,
    )
