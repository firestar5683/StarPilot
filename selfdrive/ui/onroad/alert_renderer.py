import time
import pyray as rl
from dataclasses import dataclass
from cereal import messaging, log, custom
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.common.filter_simple import BounceFilter, FirstOrderFilter
from openpilot.system.hardware import TICI
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.label import UnifiedLabel

AlertSize = log.SelfdriveState.AlertSize
AlertStatus = log.SelfdriveState.AlertStatus
StarPilotAlertStatus = custom.StarPilotSelfdriveState.AlertStatus

ALERT_MARGIN = 40
ALERT_PADDING = 60

ALERT_HEIGHTS = {
  AlertSize.small: 271,
  AlertSize.mid: 420,
}

ALERT_SLIDE_DISTANCES = {
  AlertSize.small: 40,
  AlertSize.mid: 70,
  AlertSize.full: 100,
}

SMALL_FONT_SIZE = 60
MID_FONT_SIZE_1 = 88
MID_FONT_SIZE_2 = 56

SELFDRIVE_STATE_TIMEOUT = 5
SELFDRIVE_UNRESPONSIVE_TIMEOUT = 10

ALERT_COLORS = {
  AlertStatus.normal: rl.Color(0, 0, 0, 255),
  AlertStatus.userPrompt: rl.Color(255, 115, 0, 255),
  AlertStatus.critical: rl.Color(255, 0, 21, 255),
  StarPilotAlertStatus.starpilot: rl.Color(23, 134, 68, 255),
}


@dataclass
class Alert:
  text1: str = ""
  text2: str = ""
  size: int = 0
  status: int = 0
  alert_type: str = ""


def _is_reverse_gear_full_alert(alert: Alert) -> bool:
  return alert.size == AlertSize.full and (alert.alert_type or "").split("/", 1)[0] == "reverseGear"


ALERT_STARTUP_PENDING = Alert(
  text1=tr("openpilot Unavailable"),
  text2=tr("Waiting to start"),
  size=AlertSize.mid,
  status=AlertStatus.normal,
)

ALERT_CRITICAL_TIMEOUT = Alert(
  text1=tr("TAKE CONTROL IMMEDIATELY"),
  text2=tr("System Unresponsive"),
  size=AlertSize.full,
  status=AlertStatus.critical,
)

ALERT_CRITICAL_REBOOT = Alert(
  text1=tr("System Unresponsive"),
  text2=tr("Reboot Device"),
  size=AlertSize.mid,
  status=AlertStatus.normal,
)


class AlertRenderer(Widget):
  def __init__(self):
    super().__init__()

    self._alert_text1_label = UnifiedLabel(text="", font_size=48, font_weight=FontWeight.BOLD,
                                           line_height=0.86, letter_spacing=-0.02)
    self._alert_text2_label = UnifiedLabel(text="", font_size=32, font_weight=FontWeight.NORMAL,
                                           line_height=0.86, letter_spacing=0.025)

    self._prev_alert: Alert | None = None
    self._current_alert: Alert | None = None

    self._alert_y_filter = BounceFilter(0, 0.1, 1 / gui_app.target_fps, initialized=False)
    self._alpha_filter = FirstOrderFilter(0, 0.05, 1 / gui_app.target_fps)

  def get_alert(self, sm: messaging.SubMaster) -> Alert | None:
    ss = sm['selfdriveState']

    if not sm.updated['selfdriveState']:
      recv_frame = sm.recv_frame['selfdriveState']
      time_since_onroad = time.monotonic() - ui_state.started_time

      waiting_for_startup = recv_frame < ui_state.started_frame
      if waiting_for_startup and time_since_onroad > 5:
        return ALERT_STARTUP_PENDING

      if TICI and not waiting_for_startup:
        ss_missing = time.monotonic() - sm.recv_time['selfdriveState']
        if ss_missing > SELFDRIVE_STATE_TIMEOUT:
          if ss.enabled and (ss_missing - SELFDRIVE_STATE_TIMEOUT) < SELFDRIVE_UNRESPONSIVE_TIMEOUT:
            return ALERT_CRITICAL_TIMEOUT
          return ALERT_CRITICAL_REBOOT

    if ss.alertSize != AlertSize.none:
      ret = Alert(text1=ss.alertText1, text2=ss.alertText2, size=ss.alertSize.raw, status=ss.alertStatus.raw,
                  alert_type=ss.alertType)
    else:
      starpilot_ss = sm["starpilotSelfdriveState"]
      if starpilot_ss.alertSize == custom.StarPilotSelfdriveState.AlertSize.none:
        return None
      ret = Alert(text1=starpilot_ss.alertText1, text2=starpilot_ss.alertText2,
                  size=starpilot_ss.alertSize.raw, status=starpilot_ss.alertStatus.raw,
                  alert_type=starpilot_ss.alertType)

    if ret.status == AlertStatus.normal and ui_state.starpilot_toggles.get("hide_alerts", False):
      return None

    if sm.recv_frame['selfdriveState'] < ui_state.started_frame:
      return None

    self._prev_alert = ret
    return ret

  def will_render(self) -> tuple[Alert | None, bool]:
    """Return cached alert state without re-polling get_alert(). Safe to call multiple times per frame."""
    alert = self._current_alert
    return alert or self._prev_alert, alert is None

  def _get_alert_rect(self, rect: rl.Rectangle, size: int) -> rl.Rectangle:
    if size == AlertSize.full:
      return rect
    h = ALERT_HEIGHTS.get(size, rect.height)
    return rl.Rectangle(rect.x, rect.y + rect.height - h, rect.width, h)

  def _render(self, rect: rl.Rectangle) -> bool:
    alert = self.get_alert(ui_state.sm)
    self._current_alert = alert

    self._alpha_filter.update(0 if alert is None else 1)

    if alert is not None:
      self._rect = self._get_alert_rect(rect, alert.size)
      self._alert_y_filter.update(self._rect.y)
    elif self._prev_alert is not None:
      self._rect = self._get_alert_rect(rect, self._prev_alert.size)
      slide = ALERT_SLIDE_DISTANCES.get(self._prev_alert.size, 100)
      self._alert_y_filter.update(self._rect.y - slide)
    else:
      return False

    if alert is None:
      if self._alpha_filter.x > 0.01 and self._prev_alert is not None:
        alert = self._prev_alert
      else:
        self._prev_alert = None
        return False

    if not _is_reverse_gear_full_alert(alert):
      self._draw_background(alert)
    self._draw_text(alert)

    return True

  def _draw_background(self, alert: Alert) -> None:
    color = ALERT_COLORS.get(alert.status, ALERT_COLORS[AlertStatus.normal])
    color = rl.Color(color.r, color.g, color.b, int(255 * 0.90 * self._alpha_filter.x))
    translucent_color = rl.Color(color.r, color.g, color.b, int(0 * self._alpha_filter.x))

    if alert.size == AlertSize.full:
      bg_height = int(self._rect.height)
      solid_height = round(bg_height * 0.2)
      rl.draw_rectangle(int(self._rect.x), int(self._rect.y), int(self._rect.width), solid_height, color)
      rl.draw_rectangle_gradient_v(int(self._rect.x), int(self._rect.y + solid_height), int(self._rect.width),
                                   int(bg_height - solid_height), color, translucent_color)
    else:
      bg_height = int(self._rect.height)

      font_size = SMALL_FONT_SIZE if alert.size == AlertSize.small else MID_FONT_SIZE_1
      self._alert_text1_label.set_text(alert.text1)
      self._alert_text1_label.set_font_size(font_size)
      content_h = self._alert_text1_label.get_content_height(int(self._rect.width - ALERT_PADDING * 2))

      # Center the plateau on text1's rendered position with a 2px buffer on each
      # side to guarantee int-truncated draw calls fully cover text1's float render.
      plateau_y = round(self._alert_y_filter.x + (self._rect.height - content_h) / 2) - 2
      plateau_h = round(content_h) + 4
      top_fade_h = plateau_y - int(self._rect.y)
      bottom_fade_h = bg_height - top_fade_h - plateau_h

      rl.draw_rectangle_gradient_v(int(self._rect.x), int(self._rect.y),
                                   int(self._rect.width), top_fade_h,
                                   translucent_color, color)
      rl.draw_rectangle(int(self._rect.x), plateau_y,
                        int(self._rect.width), plateau_h, color)
      rl.draw_rectangle_gradient_v(int(self._rect.x), plateau_y + plateau_h,
                                   int(self._rect.width), bottom_fade_h,
                                   color, translucent_color)

  def _draw_text(self, alert: Alert) -> None:
    text_color = rl.Color(255, 255, 255, int(255 * 0.9 * self._alpha_filter.x))
    text2_color = rl.Color(255, 255, 255, int(255 * 0.65 * self._alpha_filter.x))

    text_rect = rl.Rectangle(
      self._rect.x + ALERT_PADDING,
      self._alert_y_filter.x,
      self._rect.width - ALERT_PADDING * 2,
      self._rect.height,
    )

    if alert.size == AlertSize.small:
      self._alert_text1_label.set_text(alert.text1)
      self._alert_text1_label.set_text_color(text_color)
      self._alert_text1_label.set_font_size(SMALL_FONT_SIZE)
      self._alert_text1_label.set_alignment(rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
      self._alert_text1_label.set_alignment_vertical(rl.GuiTextAlignmentVertical.TEXT_ALIGN_MIDDLE)
      self._alert_text1_label.render(text_rect)

    elif alert.size == AlertSize.mid:
      self._alert_text1_label.set_text(alert.text1)
      self._alert_text1_label.set_text_color(text_color)
      self._alert_text1_label.set_font_size(MID_FONT_SIZE_1)
      self._alert_text1_label.set_alignment(rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
      self._alert_text1_label.set_alignment_vertical(rl.GuiTextAlignmentVertical.TEXT_ALIGN_MIDDLE)
      self._alert_text1_label.render(text_rect)

      if alert.text2:
        content_h = self._alert_text1_label.get_content_height(int(text_rect.width))
        center_y = self._alert_y_filter.x + (self._rect.height - content_h) / 2
        text2_rect = rl.Rectangle(
          text_rect.x,
          center_y + content_h,
          text_rect.width,
          self._rect.height - (center_y + content_h - self._alert_y_filter.x),
        )
        self._alert_text2_label.set_text(alert.text2)
        self._alert_text2_label.set_text_color(text2_color)
        self._alert_text2_label.set_font_size(MID_FONT_SIZE_2)
        self._alert_text2_label.set_alignment(rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
        self._alert_text2_label.set_alignment_vertical(rl.GuiTextAlignmentVertical.TEXT_ALIGN_TOP)
        self._alert_text2_label.render(text2_rect)

    else:
      if len(alert.text1) <= 12:
        font_size = 120
      elif len(alert.text1) <= 16:
        font_size = 110
      else:
        font_size = 100

      self._alert_text1_label.set_text(alert.text1)
      self._alert_text1_label.set_text_color(text_color)
      self._alert_text1_label.set_font_size(font_size)
      self._alert_text1_label.set_alignment(rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
      self._alert_text1_label.set_alignment_vertical(rl.GuiTextAlignmentVertical.TEXT_ALIGN_MIDDLE)
      self._alert_text1_label.render(text_rect)

      if alert.text2:
        if len(alert.text2) > 24:
          t2_size = 48
        elif len(alert.text2) > 18:
          t2_size = 52
        else:
          t2_size = 56
        content_h = self._alert_text1_label.get_content_height(int(text_rect.width))
        center_y = self._alert_y_filter.x + (self._rect.height - content_h) / 2
        text2_rect = rl.Rectangle(
          text_rect.x,
          center_y + content_h,
          text_rect.width,
          self._rect.height - (center_y + content_h - self._alert_y_filter.x),
        )
        self._alert_text2_label.set_text(alert.text2)
        self._alert_text2_label.set_text_color(text2_color)
        self._alert_text2_label.set_font_size(t2_size)
        self._alert_text2_label.set_alignment(rl.GuiTextAlignment.TEXT_ALIGN_CENTER)
        self._alert_text2_label.set_alignment_vertical(rl.GuiTextAlignmentVertical.TEXT_ALIGN_TOP)
        self._alert_text2_label.render(text2_rect)
