import pyray as rl
from dataclasses import dataclass
from openpilot.common.constants import CV
from openpilot.selfdrive.ui.mici.onroad.torque_bar import TorqueBar
from openpilot.selfdrive.ui.mici.onroad.speed_limit_utils import resolve_display_speed_limit_ms
from openpilot.selfdrive.ui.ui_state import ui_state, UIStatus
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget
from openpilot.common.filter_simple import FirstOrderFilter
from cereal import log

EventName = log.OnroadEvent.EventName

# Constants
SET_SPEED_NA = 255
KM_TO_MILE = 0.621371
CRUISE_DISABLED_CHAR = '–'

SET_SPEED_PERSISTENCE = 2.5  # seconds

SPEED_LIMIT_PROMPT_CARD_WIDTH = 500
SPEED_LIMIT_PROMPT_CARD_HEIGHT = 208
SPEED_LIMIT_PROMPT_BUTTON_SIZE = 112
SPEED_LIMIT_PROMPT_BUTTON_GAP = 28
SPEED_LIMIT_PROMPT_CARD_PADDING = 34
SPEED_LIMIT_PROMPT_US_SIGN_WIDTH = 132
SPEED_LIMIT_PROMPT_US_SIGN_HEIGHT = 150
SPEED_LIMIT_PROMPT_EU_SIGN_SIZE = 148


@dataclass(frozen=True)
class FontSizes:
  current_speed: int = 176
  speed_unit: int = 66
  max_speed: int = 36
  set_speed: int = 112


@dataclass(frozen=True)
class Colors:
  WHITE = rl.WHITE
  WHITE_TRANSLUCENT = rl.Color(255, 255, 255, 200)


FONT_SIZES = FontSizes()
COLORS = Colors()


class TurnIntent(Widget):
  FADE_IN_ANGLE = 30  # degrees

  def __init__(self):
    super().__init__()
    self._pre = False
    self._turn_intent_direction: int = 0

    self._turn_intent_alpha_filter = FirstOrderFilter(0, 0.05, 1 / gui_app.target_fps)
    self._turn_intent_rotation_filter = FirstOrderFilter(0, 0.1, 1 / gui_app.target_fps)

    self._txt_turn_intent_left: rl.Texture = gui_app.texture('icons_mici/turn_intent_left.png', 50, 19)
    self._txt_turn_intent_right: rl.Texture = gui_app.texture('icons_mici/turn_intent_right.png', 50, 19)

  def _render(self, _):
    if self._turn_intent_alpha_filter.x > 1e-2:
      turn_intent_texture = self._txt_turn_intent_right if self._turn_intent_direction == 1 else self._txt_turn_intent_left
      src_rect = rl.Rectangle(0, 0, turn_intent_texture.width, turn_intent_texture.height)
      dest_rect = rl.Rectangle(self._rect.x + self._rect.width / 2, self._rect.y + self._rect.height / 2,
                               turn_intent_texture.width, turn_intent_texture.height)

      origin = (turn_intent_texture.width / 2, self._rect.height / 2)
      color = rl.Color(255, 255, 255, int(255 * self._turn_intent_alpha_filter.x))
      rl.draw_texture_pro(turn_intent_texture, src_rect, dest_rect, origin, self._turn_intent_rotation_filter.x, color)

  def _update_state(self) -> None:
    sm = ui_state.sm

    left = any(e.name == EventName.preLaneChangeLeft for e in sm['onroadEvents'])
    right = any(e.name == EventName.preLaneChangeRight for e in sm['onroadEvents'])
    if left or right:
      # pre lane change
      if not self._pre:
        self._turn_intent_rotation_filter.x = self.FADE_IN_ANGLE if left else -self.FADE_IN_ANGLE

      self._pre = True
      self._turn_intent_direction = -1 if left else 1
      self._turn_intent_alpha_filter.update(1)
      self._turn_intent_rotation_filter.update(0)
    elif any(e.name == EventName.laneChange for e in sm['onroadEvents']):
      # fade out and rotate away
      self._pre = False
      self._turn_intent_alpha_filter.update(0)

      if self._turn_intent_direction == 0:
        # unknown. missed pre frame?
        self._turn_intent_rotation_filter.update(0)
      else:
        self._turn_intent_rotation_filter.update(self._turn_intent_direction * self.FADE_IN_ANGLE)
    else:
      # didn't complete lane change, just hide
      self._pre = False
      self._turn_intent_direction = 0
      self._turn_intent_alpha_filter.update(0)
      self._turn_intent_rotation_filter.update(0)


class HudRenderer(Widget):
  def __init__(self):
    super().__init__()
    """Initialize the HUD renderer."""
    self.is_cruise_set: bool = False
    self.is_cruise_available: bool = True
    self.set_speed: float = SET_SPEED_NA
    self._set_speed_changed_time: float = 0
    self.speed: float = 0.0
    self.v_ego_cluster_seen: bool = False
    self._engaged: bool = False
    self._show_speed_limit: bool = False
    self._speed_limit: float = 0.0
    self._speed_limit_offset: float = 0.0
    self._show_speed_limit_offset: bool = False
    self._speed_limit_overridden: bool = False
    self._pending_speed_limit: float = 0.0
    self._prompt_visible: bool = False
    self._prompt_card_rect: rl.Rectangle = rl.Rectangle(0, 0, 0, 0)
    self._prompt_sign_rect: rl.Rectangle = rl.Rectangle(0, 0, 0, 0)
    self._prompt_deny_rect: rl.Rectangle = rl.Rectangle(0, 0, 0, 0)
    self._prompt_accept_rect: rl.Rectangle = rl.Rectangle(0, 0, 0, 0)

    self._can_draw_top_icons = True
    self._show_wheel_critical = False

    self._font_bold: rl.Font = gui_app.font(FontWeight.BOLD)
    self._font_medium: rl.Font = gui_app.font(FontWeight.MEDIUM)
    self._font_semi_bold: rl.Font = gui_app.font(FontWeight.SEMI_BOLD)
    self._font_display: rl.Font = gui_app.font(FontWeight.DISPLAY)

    self._turn_intent = TurnIntent()
    self._torque_bar = TorqueBar()

    self._txt_wheel: rl.Texture = gui_app.texture('icons_mici/wheel.png', 50, 50)
    self._txt_wheel_critical: rl.Texture = gui_app.texture('icons_mici/wheel_critical.png', 50, 50)
    self._txt_exclamation_point: rl.Texture = gui_app.texture('icons_mici/exclamation_point.png', 44, 44)

    self._wheel_alpha_filter = FirstOrderFilter(0, 0.05, 1 / gui_app.target_fps)
    self._wheel_y_filter = FirstOrderFilter(0, 0.1, 1 / gui_app.target_fps)

    self._set_speed_alpha_filter = FirstOrderFilter(0.0, 0.1, 1 / gui_app.target_fps)

  def set_wheel_critical_icon(self, critical: bool):
    """Set the wheel icon to critical or normal state."""
    self._show_wheel_critical = critical

  def set_can_draw_top_icons(self, can_draw_top_icons: bool):
    """Set whether to draw the top part of the HUD."""
    self._can_draw_top_icons = can_draw_top_icons

  def drawing_top_icons(self) -> bool:
    # whether we're drawing any top icons currently
    return bool(self._set_speed_alpha_filter.x > 1e-2)

  def _update_state(self) -> None:
    """Update HUD state based on car state and controls state."""
    sm = ui_state.sm
    if sm.recv_frame["carState"] < ui_state.started_frame:
      self.is_cruise_set = False
      self.set_speed = SET_SPEED_NA
      self.speed = 0.0
      return

    controls_state = sm['controlsState']
    car_state = sm['carState']

    v_cruise_cluster = car_state.vCruiseCluster
    set_speed = (
      controls_state.vCruiseDEPRECATED if v_cruise_cluster == 0.0 else v_cruise_cluster
    )
    engaged = sm['selfdriveState'].enabled
    if (set_speed != self.set_speed and engaged) or (engaged and not self._engaged):
      self._set_speed_changed_time = rl.get_time()
    self._engaged = engaged
    self.set_speed = set_speed
    self.is_cruise_set = 0 < self.set_speed < SET_SPEED_NA
    self.is_cruise_available = self.set_speed != -1

    v_ego_cluster = car_state.vEgoCluster
    self.v_ego_cluster_seen = self.v_ego_cluster_seen or v_ego_cluster != 0.0
    v_ego = v_ego_cluster if self.v_ego_cluster_seen else car_state.vEgo
    speed_conversion = CV.MS_TO_KPH if ui_state.is_metric else CV.MS_TO_MPH
    self.speed = max(0.0, v_ego * speed_conversion)

    if sm.recv_frame["starpilotPlan"] >= ui_state.started_frame:
      starpilot_plan = sm["starpilotPlan"]
      self._show_speed_limit = ui_state.params.get_bool("ShowSpeedLimits") or ui_state.params.get_bool("SpeedLimitController")
      if self._show_speed_limit:
        dashboard_speed_limit = sm["starpilotCarState"].dashboardSpeedLimit if sm.valid.get("starpilotCarState", False) else 0.0
        vision_speed_limit = ui_state.params_memory.get_float("VisionSpeedLimit") if ui_state.params.get_bool("VisionSpeedLimitDetection") else 0.0
        self._show_speed_limit_offset = ui_state.params.get_bool("ShowSLCOffset")
        primary_priority = ui_state.params.get("SLCPriority1", encoding='utf-8') or "Map Data"
        secondary_priority = ui_state.params.get("SLCPriority2", encoding='utf-8') or "None"
        source_limits = {
          "Dashboard": dashboard_speed_limit,
          "Map Data": starpilot_plan.slcMapSpeedLimit,
          "Vision": vision_speed_limit,
          "Mapbox": starpilot_plan.slcMapboxSpeedLimit if ui_state.params.get_bool("SLCMapboxFiller") else 0.0,
        }
        resolved_speed_limit = resolve_display_speed_limit_ms(
          slc_speed_limit=starpilot_plan.slcSpeedLimit,
          speed_limit_source=starpilot_plan.slcSpeedLimitSource,
          source_limits=source_limits,
          primary_priority=primary_priority,
          secondary_priority=secondary_priority,
        )
        self._speed_limit = max(0.0, resolved_speed_limit * speed_conversion)
        self._speed_limit_offset = starpilot_plan.slcSpeedLimitOffset * speed_conversion
        self._speed_limit_overridden = bool(starpilot_plan.slcOverriddenSpeed > 0 and starpilot_plan.slcSpeedLimit > 0)
        if self._speed_limit > 0 and not self._speed_limit_overridden and not self._show_speed_limit_offset:
          self._speed_limit += self._speed_limit_offset
        self._pending_speed_limit = max(0.0, starpilot_plan.unconfirmedSlcSpeedLimit * speed_conversion)
      else:
        self._speed_limit = 0.0
        self._speed_limit_offset = 0.0
        self._show_speed_limit_offset = False
        self._speed_limit_overridden = False
        self._pending_speed_limit = 0.0
      self._prompt_visible = self._pending_speed_limit > 0
    else:
      self._show_speed_limit = False
      self._speed_limit = 0.0
      self._speed_limit_offset = 0.0
      self._show_speed_limit_offset = False
      self._speed_limit_overridden = False
      self._pending_speed_limit = 0.0
      self._prompt_visible = False

  def prepare(self, rect: rl.Rectangle) -> None:
    """Update HUD state once before drawing background/foreground passes."""
    self.set_rect(rect)
    self._update_state()
    self._update_prompt_layout(rect)

  def render_background(self) -> None:
    """Draw HUD elements that should sit behind alerts."""
    self._draw_speed_limit(self._rect)
    self._draw_speed_limit_prompt(self._rect)

  def render_foreground(self) -> None:
    """Draw HUD elements that should sit above alerts."""
    if ui_state.sm['controlsState'].lateralControlState.which() != 'angleState':
      self._torque_bar.render(self._rect)

    if self.is_cruise_set:
      self._draw_set_speed(self._rect)

    self._draw_steering_wheel(self._rect)

  def _render(self, rect: rl.Rectangle) -> None:
    """Render HUD elements to the screen."""
    self.prepare(rect)
    self.render_background()
    self.render_foreground()

  def _draw_steering_wheel(self, rect: rl.Rectangle) -> None:
    wheel_txt = self._txt_wheel_critical if self._show_wheel_critical else self._txt_wheel

    if self._show_wheel_critical:
      self._wheel_alpha_filter.update(255)
      self._wheel_y_filter.update(0)
    else:
      if ui_state.status == UIStatus.DISENGAGED:
        self._wheel_alpha_filter.update(0)
        self._wheel_y_filter.update(wheel_txt.height / 2)
      else:
        self._wheel_alpha_filter.update(255 * 0.9)
        self._wheel_y_filter.update(0)

    # pos
    pos_x = int(rect.x + 21 + wheel_txt.width / 2)
    pos_y = int(rect.y + rect.height - 14 - wheel_txt.height / 2 + self._wheel_y_filter.x)
    rotation = -ui_state.sm['carState'].steeringAngleDeg

    turn_intent_margin = 25
    self._turn_intent.render(rl.Rectangle(
      pos_x - wheel_txt.width / 2 - turn_intent_margin,
      pos_y - wheel_txt.height / 2 - turn_intent_margin,
      wheel_txt.width + turn_intent_margin * 2,
      wheel_txt.height + turn_intent_margin * 2,
    ))

    src_rect = rl.Rectangle(0, 0, wheel_txt.width, wheel_txt.height)
    dest_rect = rl.Rectangle(pos_x, pos_y, wheel_txt.width, wheel_txt.height)
    origin = (wheel_txt.width / 2, wheel_txt.height / 2)

    # color and draw
    color = rl.Color(255, 255, 255, int(self._wheel_alpha_filter.x))
    rl.draw_texture_pro(wheel_txt, src_rect, dest_rect, origin, rotation, color)

    if self._show_wheel_critical:
      # Draw exclamation point icon
      EXCLAMATION_POINT_SPACING = 10
      exclamation_pos_x = pos_x - self._txt_exclamation_point.width / 2 + wheel_txt.width / 2 + EXCLAMATION_POINT_SPACING
      exclamation_pos_y = pos_y - self._txt_exclamation_point.height / 2
      rl.draw_texture(self._txt_exclamation_point, int(exclamation_pos_x), int(exclamation_pos_y), rl.WHITE)

  def _draw_set_speed(self, rect: rl.Rectangle) -> None:
    """Draw the MAX speed indicator box."""
    alpha = self._set_speed_alpha_filter.update(0 < rl.get_time() - self._set_speed_changed_time < SET_SPEED_PERSISTENCE and
                                                self._can_draw_top_icons and self._engaged)
    if alpha < 1e-2:
      return

    x = rect.x
    y = rect.y

    # draw drop shadow
    circle_radius = 162 // 2
    rl.draw_circle_gradient(int(x + circle_radius), int(y + circle_radius), circle_radius,
                            rl.Color(0, 0, 0, int(255 / 2 * alpha)), rl.BLANK)

    set_speed_color = rl.Color(255, 255, 255, int(255 * 0.9 * alpha))
    max_color = rl.Color(255, 255, 255, int(255 * 0.9 * alpha))

    set_speed = self.set_speed
    if self.is_cruise_set and not ui_state.is_metric:
      set_speed *= KM_TO_MILE

    set_speed_text = CRUISE_DISABLED_CHAR if not self.is_cruise_set else str(round(set_speed))
    rl.draw_text_ex(
      self._font_display,
      set_speed_text,
      rl.Vector2(x + 13 + 4, y + 3 - 8 - 3 + 4),
      FONT_SIZES.set_speed,
      0,
      set_speed_color,
    )

    max_text = tr("MAX")
    rl.draw_text_ex(
      self._font_semi_bold,
      max_text,
      rl.Vector2(x + 25, y + FONT_SIZES.set_speed - 7 + 4),
      FONT_SIZES.max_speed,
      0,
      max_color,
    )

  def _draw_us_speed_limit_sign(
    self,
    sign_rect: rl.Rectangle,
    speed_text: str,
    sign_alpha: int,
    *,
    border_thickness: float,
    header_font_size: int,
    header_gap: int,
    speed_font_size: int,
    header_top: float,
    speed_top: float,
    footer_text: str = "",
    footer_font_size: int = 0,
    footer_top: float = 0.0,
  ) -> None:
    border_color = rl.Color(255, 255, 255, sign_alpha)
    text_color = rl.Color(255, 255, 255, sign_alpha)

    inner_border_rect = rl.Rectangle(
      sign_rect.x + 8,
      sign_rect.y + 8,
      sign_rect.width - 16,
      sign_rect.height - 16,
    )
    rl.draw_rectangle_rounded_lines_ex(inner_border_rect, 0.14, 16, max(border_thickness - 2, 1), border_color)

    speed_label = tr("SPEED")
    limit_label = tr("LIMIT")
    speed_label_size = measure_text_cached(self._font_semi_bold, speed_label, header_font_size)
    limit_label_size = measure_text_cached(self._font_semi_bold, limit_label, header_font_size)

    rl.draw_text_ex(
      self._font_semi_bold,
      speed_label,
      rl.Vector2(sign_rect.x + sign_rect.width / 2 - speed_label_size.x / 2, sign_rect.y + header_top),
      header_font_size,
      0,
      text_color,
    )
    rl.draw_text_ex(
      self._font_semi_bold,
      limit_label,
      rl.Vector2(sign_rect.x + sign_rect.width / 2 - limit_label_size.x / 2, sign_rect.y + header_top + header_gap),
      header_font_size,
      0,
      text_color,
    )

    speed_text_size = measure_text_cached(self._font_bold, speed_text, speed_font_size)
    speed_text_pos = rl.Vector2(sign_rect.x + sign_rect.width / 2 - speed_text_size.x / 2, sign_rect.y + speed_top)
    rl.draw_text_ex(self._font_bold, speed_text, speed_text_pos, speed_font_size, 0, text_color)

    if footer_text and footer_font_size > 0:
      footer_size = measure_text_cached(self._font_semi_bold, footer_text, footer_font_size)
      footer_pos = rl.Vector2(sign_rect.x + sign_rect.width / 2 - footer_size.x / 2, sign_rect.y + footer_top)
      rl.draw_text_ex(self._font_semi_bold, footer_text, footer_pos, footer_font_size, 0, text_color)

  def _draw_speed_limit(self, rect: rl.Rectangle) -> None:
    if not self._show_speed_limit:
      return

    display_speed = self._speed_limit if self._speed_limit > 0 else self._pending_speed_limit
    if display_speed <= 0:
      return

    sign_alpha = 72 if self._speed_limit_overridden and self._pending_speed_limit <= 0 else 255
    use_vienna_speed_limit = ui_state.params.get_bool("UseVienna")
    sign_width = 118 if use_vienna_speed_limit else 116
    sign_height = 118 if use_vienna_speed_limit else 132
    base_x = rect.x + rect.width - sign_width - 28
    sign_x = base_x
    sign_y = rect.y + (28 if use_vienna_speed_limit else 20)

    speed_text = str(round(display_speed))
    offset_text = ""
    if self._show_speed_limit_offset and not self._speed_limit_overridden:
      rounded_offset = round(self._speed_limit_offset)
      offset_text = "–" if rounded_offset == 0 else f"{rounded_offset:+d}"
    if use_vienna_speed_limit:
      center_x = sign_x + sign_width / 2
      center_y = sign_y + sign_height / 2
      radius = sign_width / 2

      rl.draw_circle(int(center_x), int(center_y), radius, rl.Color(255, 255, 255, sign_alpha))
      rl.draw_ring(
        rl.Vector2(center_x, center_y),
        radius - 12,
        radius,
        0,
        360,
        64,
        rl.Color(201, 34, 49, sign_alpha),
      )

      font_size = 58 if len(speed_text) <= 2 else 48
      text_size = measure_text_cached(self._font_bold, speed_text, font_size)
      text_pos = rl.Vector2(center_x - text_size.x / 2, center_y - text_size.y / 2 + (-14 if offset_text else 4))
      rl.draw_text_ex(self._font_bold, speed_text, text_pos, font_size, 0, rl.Color(0, 0, 0, sign_alpha))
      if offset_text:
        offset_font_size = 34
        offset_size = measure_text_cached(self._font_semi_bold, offset_text, offset_font_size)
        offset_pos = rl.Vector2(center_x - offset_size.x / 2, sign_y + sign_height - 42)
        rl.draw_text_ex(self._font_semi_bold, offset_text, offset_pos, offset_font_size, 0, rl.Color(0, 0, 0, sign_alpha))
    else:
      sign_rect = rl.Rectangle(sign_x, sign_y, sign_width, sign_height)
      self._draw_us_speed_limit_sign(
        sign_rect,
        speed_text,
        sign_alpha,
        border_thickness=4,
        header_font_size=20,
        header_gap=18,
        speed_font_size=44 if offset_text else (50 if len(speed_text) <= 2 else 42),
        header_top=18,
        speed_top=58 if offset_text else 66,
        footer_text=offset_text,
        footer_font_size=28 if offset_text else 0,
        footer_top=100,
      )

  def _update_prompt_layout(self, rect: rl.Rectangle) -> None:
    if not self._prompt_visible:
      self._prompt_card_rect = rl.Rectangle(0, 0, 0, 0)
      self._prompt_sign_rect = rl.Rectangle(0, 0, 0, 0)
      self._prompt_deny_rect = rl.Rectangle(0, 0, 0, 0)
      self._prompt_accept_rect = rl.Rectangle(0, 0, 0, 0)
      return

    use_vienna_speed_limit = ui_state.params.get_bool("UseVienna")
    sign_width = SPEED_LIMIT_PROMPT_EU_SIGN_SIZE if use_vienna_speed_limit else SPEED_LIMIT_PROMPT_US_SIGN_WIDTH
    sign_height = SPEED_LIMIT_PROMPT_EU_SIGN_SIZE if use_vienna_speed_limit else SPEED_LIMIT_PROMPT_US_SIGN_HEIGHT
    button_size = SPEED_LIMIT_PROMPT_BUTTON_SIZE
    card_width = max(
      SPEED_LIMIT_PROMPT_CARD_WIDTH,
      SPEED_LIMIT_PROMPT_CARD_PADDING * 2 + sign_width + button_size * 2 + SPEED_LIMIT_PROMPT_BUTTON_GAP * 2,
    )
    card_x = rect.x + (rect.width - card_width) / 2
    card_y = rect.y + rect.height * 0.34
    card_rect = rl.Rectangle(card_x, card_y, card_width, SPEED_LIMIT_PROMPT_CARD_HEIGHT)

    controls_y = card_y + 68
    deny_x = card_x + SPEED_LIMIT_PROMPT_CARD_PADDING
    sign_x = card_x + (card_width - sign_width) / 2
    accept_x = card_x + card_width - SPEED_LIMIT_PROMPT_CARD_PADDING - button_size

    self._prompt_card_rect = card_rect
    self._prompt_sign_rect = rl.Rectangle(sign_x, controls_y - (sign_height - button_size) / 2, sign_width, sign_height)
    self._prompt_deny_rect = rl.Rectangle(deny_x, controls_y, button_size, button_size)
    self._prompt_accept_rect = rl.Rectangle(accept_x, controls_y, button_size, button_size)

  def _draw_prompt_button(self, rect: rl.Rectangle, symbol: str, fill: rl.Color, outline: rl.Color, pressed: bool) -> None:
    scale = 0.95 if pressed else 1.0
    width = rect.width * scale
    height = rect.height * scale
    x = rect.x + (rect.width - width) / 2
    y = rect.y + (rect.height - height) / 2
    button_rect = rl.Rectangle(x, y, width, height)
    center = rl.Vector2(button_rect.x + button_rect.width / 2, button_rect.y + button_rect.height / 2)
    radius = min(button_rect.width, button_rect.height) / 2

    rl.draw_circle_gradient(int(center.x), int(center.y), radius, rl.Color(0, 0, 0, 90), rl.BLANK)
    rl.draw_circle(int(center.x), int(center.y), radius, fill)
    rl.draw_ring(center, radius - 6, radius, 0, 360, 48, outline)

    symbol_size = 88 if symbol == "+" else 98
    symbol_text = tr(symbol)
    symbol_measure = measure_text_cached(self._font_display, symbol_text, symbol_size)
    symbol_pos = rl.Vector2(center.x - symbol_measure.x / 2, center.y - symbol_measure.y / 2 - (6 if symbol == "-" else 0))
    rl.draw_text_ex(self._font_display, symbol_text, symbol_pos, symbol_size, 0, rl.WHITE)

  def _draw_speed_limit_prompt(self, rect: rl.Rectangle) -> None:
    if not self._prompt_visible:
      return

    accent_color = rl.Color(255, 115, 0, 255)
    card_rect = self._prompt_card_rect
    rl.draw_rectangle_rounded(card_rect, 0.14, 18, rl.Color(10, 10, 10, 210))
    rl.draw_rectangle_rounded_lines_ex(card_rect, 0.14, 18, 4, accent_color)

    title_text = tr("NEW SPEED LIMIT")
    title_size = measure_text_cached(self._font_semi_bold, title_text, 28)
    title_pos = rl.Vector2(card_rect.x + card_rect.width / 2 - title_size.x / 2, card_rect.y + 18)
    rl.draw_text_ex(self._font_semi_bold, title_text, title_pos, 28, 0, rl.Color(255, 255, 255, 235))

    use_vienna_speed_limit = ui_state.params.get_bool("UseVienna")
    speed_text = str(round(self._pending_speed_limit))
    sign_rect = self._prompt_sign_rect

    if use_vienna_speed_limit:
      center_x = sign_rect.x + sign_rect.width / 2
      center_y = sign_rect.y + sign_rect.height / 2
      radius = sign_rect.width / 2

      rl.draw_circle(int(center_x), int(center_y), radius, rl.WHITE)
      rl.draw_ring(
        rl.Vector2(center_x, center_y),
        radius - 14,
        radius,
        0,
        360,
        64,
        rl.Color(201, 34, 49, 255),
      )

      font_size = 78 if len(speed_text) <= 2 else 66
      text_size = measure_text_cached(self._font_bold, speed_text, font_size)
      text_pos = rl.Vector2(center_x - text_size.x / 2, center_y - text_size.y / 2 + 4)
      rl.draw_text_ex(self._font_bold, speed_text, text_pos, font_size, 0, rl.BLACK)
    else:
      self._draw_us_speed_limit_sign(
        sign_rect,
        speed_text,
        255,
        border_thickness=5,
        header_font_size=24,
        header_gap=20,
        speed_font_size=72 if len(speed_text) <= 2 else 60,
        header_top=20,
        speed_top=80,
      )

    self._draw_prompt_button(
      self._prompt_deny_rect,
      "-",
      rl.Color(104, 20, 20, 235),
      rl.Color(255, 78, 78, 255),
      False,
    )
    self._draw_prompt_button(
      self._prompt_accept_rect,
      "+",
      rl.Color(12, 110, 66, 235),
      rl.Color(78, 255, 173, 255),
      False,
    )

    hint_text = tr("SET/+ TO CONFIRM  RES/- TO DENY")
    hint_size = measure_text_cached(self._font_medium, hint_text, 24)
    hint_pos = rl.Vector2(card_rect.x + card_rect.width / 2 - hint_size.x / 2, card_rect.y + card_rect.height - 34)
    rl.draw_text_ex(self._font_medium, hint_text, hint_pos, 24, 0, rl.Color(255, 255, 255, 180))

  def _draw_current_speed(self, rect: rl.Rectangle) -> None:
    """Draw the current vehicle speed and unit."""
    speed_text = str(round(self.speed))
    speed_text_size = measure_text_cached(self._font_bold, speed_text, FONT_SIZES.current_speed)
    speed_pos = rl.Vector2(rect.x + rect.width / 2 - speed_text_size.x / 2, 180 - speed_text_size.y / 2)
    rl.draw_text_ex(self._font_bold, speed_text, speed_pos, FONT_SIZES.current_speed, 0, COLORS.WHITE)

    unit_text = tr("km/h") if ui_state.is_metric else tr("mph")
    unit_text_size = measure_text_cached(self._font_medium, unit_text, FONT_SIZES.speed_unit)
    unit_pos = rl.Vector2(rect.x + rect.width / 2 - unit_text_size.x / 2, 290 - unit_text_size.y / 2)
    rl.draw_text_ex(self._font_medium, unit_text, unit_pos, FONT_SIZES.speed_unit, 0, COLORS.WHITE_TRANSLUCENT)
