import pyray as rl
from openpilot.cereal import log
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import Widget

HIGHLIGHT_TIME = 2.5  # seconds


class LongIndicator(Widget):
  def __init__(self):
    super().__init__()
    self._txt_lead_car = (self._texture('car', 35, 27), self._texture('car_green', 50, 42))
    self._txt_distance = [(self._texture('distance_1', 32, 7), self._texture('distance_1_green', 60, 35)),
                          (self._texture('distance_2', 40, 9), self._texture('distance_2_green', 68, 37)),
                          (self._texture('distance_3', 48, 11), self._texture('distance_3_green', 76, 39))]
    self._alpha_filter = FirstOrderFilter(0.0, 0.05, 1 / gui_app.target_fps)
    # crossfade between states, a white and a green filter per icon
    self._lead_car_filters = (FirstOrderFilter(0.0, 0.1, 1 / gui_app.target_fps), FirstOrderFilter(0.0, 0.1, 1 / gui_app.target_fps))
    self._distance_filters = [(FirstOrderFilter(0.0, 0.1, 1 / gui_app.target_fps), FirstOrderFilter(0.0, 0.1, 1 / gui_app.target_fps))
                              for _ in range(3)]
    self._personality: int | None = None
    self._personality_changed_time = -HIGHLIGHT_TIME
    self._should_draw = False
    self._sidebar = False
    self._traffic_mode = False
    self._sidebar_personality: int | None = None
    self._sidebar_long_active: bool | None = None

  @staticmethod
  def _texture(name: str, width: int, height: int) -> rl.Texture:
    return gui_app.texture(f'icons_mici/longitudinal/{name}.png', width, height, keep_aspect_ratio=False)

  def set_should_draw(self, should_draw: bool):
    self._should_draw = should_draw

  def render_sidebar(self, rect: rl.Rectangle, *, personality: int | None = None,
                     longitudinal_active: bool = False, traffic_mode: bool = False) -> None:
    self._sidebar, self._traffic_mode = True, traffic_mode
    self._sidebar_personality = personality
    self._sidebar_long_active = longitudinal_active if personality is not None else None
    try:
      self.render(rect)
    finally:
      self._sidebar, self._traffic_mode = False, False
      self._sidebar_personality = self._sidebar_long_active = None

  def _render(self, rect: rl.Rectangle) -> None:
    sm = ui_state.sm
    if self._sidebar_personality is None and (sm.recv_frame['selfdriveState'] < ui_state.started_frame or
                                             not sm['selfdriveState'].enabled or not ui_state.has_longitudinal_control):
      self._personality = None
      self._personality_changed_time = -HIGHLIGHT_TIME
      self._alpha_filter.x = 0.0
      return

    # hidden under alerts and set speed
    visible = self._should_draw and (self._sidebar_personality is not None or
                                    sm['selfdriveState'].alertSize == log.SelfdriveState.AlertSize.none)
    alpha = self._alpha_filter.update(visible)
    self._draw_lead_car(rect, alpha)
    self._draw_distance_bars(rect, alpha, visible)

  def _draw_lead_car(self, rect: rl.Rectangle, alpha: float) -> None:
    sm = ui_state.sm
    plan = sm['longitudinalPlan']
    has_lead = self._sidebar_long_active is not False and sm.alive['longitudinalPlan'] and plan.hasLead

    e2e = has_lead and plan.longitudinalPlanSource == log.LongitudinalPlan.LongitudinalPlanSource.e2e
    white_f, green_f = self._lead_car_filters
    if self._sidebar_long_active is False:
      white_f.x, green_f.x = 0.35, 0.0
    white_alpha = white_f.update(0.0 if e2e else 0.9 if has_lead else 0.35)
    green_alpha = green_f.update(float(e2e))

    white, green = self._txt_lead_car
    self._draw_centered(white, rect, 100, white_alpha * alpha)
    self._draw_centered(green, rect, 100, green_alpha * alpha)

  def _draw_distance_bars(self, rect: rl.Rectangle, alpha: float, visible: bool) -> None:
    sm = ui_state.sm
    now = rl.get_time()
    personality = self._sidebar_personality if self._sidebar_personality is not None else sm['selfdriveState'].personality.raw
    if self._personality is not None and personality != self._personality:
      self._personality_changed_time = now
    self._personality = personality
    # the personality alert covers the bars, hold the highlight until they show
    if not visible and now - self._personality_changed_time < HIGHLIGHT_TIME:
      self._personality_changed_time = now
    highlight = now - self._personality_changed_time < HIGHLIGHT_TIME

    # blink at double the turn signal rate (2.67 Hz) while overriding the gas
    overriding = self._sidebar_long_active is not False and any(
      e.name == log.OnroadEvent.EventName.gasPressedOverride for e in sm['onroadEvents'])
    blink = 0.35 / 0.9 if overriding and now % 0.375 > 0.1875 else 1.0

    count = 1 if self._traffic_mode else personality + 1
    for i, ((white, green), y, (active_f, green_f)) in enumerate(zip(self._txt_distance, (122, 136, 152), self._distance_filters, strict=True)):
      active = active_f.update(float(i < count))
      green_alpha = green_f.update(float(highlight and i == count - 1 and not self._traffic_mode))
      # only lit bars blink on override
      color = (200, 32, 48) if self._traffic_mode and i < count else (255, 255, 255)
      self._draw_centered(white, rect, y, (0.35 * (1 - active) + 0.9 * (active - green_alpha) * blink) * alpha, color)
      self._draw_centered(green, rect, y, green_alpha * blink * alpha)

  def _draw_centered(self, texture: rl.Texture, rect: rl.Rectangle, y: float, alpha: float,
                     color: tuple[int, int, int] = (255, 255, 255)) -> None:
    scale = min((rect.width - 4) / 76, (rect.height - 4) / 94) if self._sidebar else 1.0
    center_x = rect.x + rect.width / 2 if self._sidebar else rect.x + 46
    center_y = rect.y + rect.height / 2 + (y - 126) * scale if self._sidebar else rect.y + y
    pos = rl.Vector2(center_x - texture.width * scale / 2, center_y - texture.height * scale / 2)
    rl.draw_texture_ex(texture, pos, 0.0, scale, rl.Color(*color, round(255 * alpha)))
