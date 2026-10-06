"""Large saved-feature editor inside the established Settings right pane."""

from math import copysign
import time

import pyray as rl

from openpilot.starpilot.ui import clip
from openpilot.starpilot.ui.feature_settings_state import (
  FeatureRow, FeatureSettingsState, FEATURE_CONFIRM_ACTIONS, is_long_confirm_action, boolean_value as _boolean_value,
  FEATURE_ROW_HEIGHT, FEATURE_VISIBLE_ROWS, FEATURE_CONTROL_LEFT, FEATURE_CONTROL_RIGHT,
  FEATURE_BUTTON_TOP, FEATURE_BUTTON_HEIGHT, FEATURE_ACTION_MARGIN, FEATURE_HEADER_HEIGHT,
  FEATURE_TAP_SLOP, FEATURE_FLICK_DISTANCE, FEATURE_PAGE_COUNTER_WIDTH,
  feature_scroll, feature_action_left, feature_row_top, feature_page_counter_left,
)
from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile
from openpilot.starpilot.ui.settings_geometry import (
  ACCENT, ACTIVE_ROW_BG, ACTIVE_ROW_BORDER, CONTROL_BG, CONTROL_BORDER, DANGER,
  PANEL_BG, PANEL_BORDER, PANEL_INNER_BORDER, ROW_SEPARATOR, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
  draw_aether_toggle, draw_rounded_fill, draw_rounded_stroke, draw_settings_header, elide_text,
)

LABEL_SIZE = 50
DETAIL_SIZE = 35
PAGE_TRANSITION_TIME = 0.18
EDGE_ACCENT = rl.color_lerp(PANEL_BG, ACCENT, 0.5)


def _confirmation(row: FeatureRow) -> bool:
  return row.key in FEATURE_CONFIRM_ACTIONS or row.key.startswith("pip:format:") or is_long_confirm_action(row.key)


def feature_pull(drag_x: float, can_page: bool) -> float:
  excess = max(0, abs(drag_x) - FEATURE_TAP_SLOP)
  limit = FEATURE_FLICK_DISTANCE if can_page else FEATURE_TAP_SLOP / 2
  return copysign(min(excess, limit), drag_x) if excess else 0.0


class FeatureSettingsView:
  def __init__(self, fonts: BitmapFonts):
    if fonts.profile != Profile.LARGE:
      raise ValueError("Large profile only")
    self.fonts = fonts
    self._last_state: FeatureSettingsState | None = None
    self._last_pull = 0.0
    self._awaiting_render = False
    self._transition: tuple[FeatureSettingsState, float, float] | None = None

  def reset(self, state: FeatureSettingsState | None = None) -> bool:
    """Finish presentation; taps on moving or replaced rows must be suppressed."""
    moving = self._transition is not None
    pending = state is not None and self._last_state is not None and state.scroll != self._last_state.scroll
    blocked = self._awaiting_render or moving or pending
    # Keep interrupted row taps blocked until the settled page is drawn.
    self._awaiting_render = blocked if state is not None else False
    self._last_state = state if self._last_state is not None else None
    self._last_pull = 0.0
    self._transition = None
    return blocked

  def _page_frame(self, state: FeatureSettingsState, pull_x: float, dragging: bool) -> tuple[FeatureSettingsState, float, int]:
    previous = self._last_state
    same_context = previous is not None and (previous.page, previous.title, previous.subtitle, previous.sidebar_expanded) == (
      state.page, state.title, state.subtitle, state.sidebar_expanded)
    if not same_context or dragging:
      self._transition = None
    elif previous.scroll != state.scroll:
      direction = 1 if state.scroll > previous.scroll else -1
      self._transition = ((previous, time.monotonic(), self._last_pull)
                          if previous.rows == state.rows and feature_scroll(previous.scroll, direction, len(state.rows)) == state.scroll else None)
    self._last_state = state
    rows, cover = state, 0
    if self._transition is not None:
      outgoing, started, start_pull = self._transition
      phase = (time.monotonic() - started) / (PAGE_TRANSITION_TIME / 2)
      if phase >= 2 or outgoing.rows != state.rows:
        self._transition = None
      else:
        direction = 1 if state.scroll > outgoing.scroll else -1
        t = max(0.0, phase if phase < 1 else phase - 1)
        t = t * t * (3 - 2 * t)
        if phase < 1:
          rows = outgoing
          pull_x = start_pull * (1 - t) - direction * FEATURE_FLICK_DISTANCE * t
          cover = round(255 * t)
        else:
          pull_x = direction * FEATURE_FLICK_DISTANCE * (1 - t)
          cover = round(255 * (1 - t))
    self._last_pull = pull_x
    self._awaiting_render = False
    return rows, pull_x, cover

  def render(self, state: FeatureSettingsState, drag_x: float = 0.0) -> None:
    left = 520 if state.sidebar_expanded else 20
    row_top = feature_row_top(state)
    shell = rl.Rectangle(left - 10, 10, 2160 - left, 1060)
    draw_rounded_fill(shell, PANEL_BG, radius_px=32)
    draw_rounded_stroke(shell, PANEL_BORDER, radius_px=32)
    draw_rounded_stroke(rl.Rectangle(shell.x + 2, 12, shell.width - 4, 1056), PANEL_INNER_BORDER, radius_px=29)
    clip.begin_scissor_mode(left - 10, 2, 2160 - left, FEATURE_HEADER_HEIGHT + 20)
    try:
      draw_settings_header(self.fonts, state.sidebar_expanded, state.title, state.parent_title, back=True)
    finally:
      clip.end_scissor_mode()
    subtitle = self._elide(state.subtitle, FontRole.NORMAL, DETAIL_SIZE, 2094 - left - 55)
    if subtitle:
      top, _ = self.fonts.vertical_ink(subtitle, FontRole.NORMAL, DETAIL_SIZE)
      self.fonts.draw(subtitle, FontRole.NORMAL, DETAIL_SIZE, left + 55, 116 - top, TEXT_SECONDARY)
    clip.begin_scissor_mode(left + 25, row_top, 2100 - left, FEATURE_VISIBLE_ROWS * FEATURE_ROW_HEIGHT)
    try:
      can_page = drag_x != 0 and feature_scroll(state.scroll, 1 if drag_x < 0 else -1, len(state.rows)) != state.scroll
      rows_state, pull_x, cover = self._page_frame(state, feature_pull(drag_x, can_page), drag_x != 0)
      if pull_x and can_page:
        edge_x = 2125 - FEATURE_FLICK_DISTANCE if pull_x < 0 else left + 25
        gap_x = 2125 + pull_x if pull_x < 0 else left + 25
        color_left, color_right = (PANEL_BG, EDGE_ACCENT) if pull_x < 0 else (EDGE_ACCENT, PANEL_BG)
        rl.draw_rectangle_gradient_ex(rl.Rectangle(gap_x, row_top, abs(pull_x), FEATURE_VISIBLE_ROWS * FEATURE_ROW_HEIGHT),
                                      color_left, color_left, color_right, color_right)
        cx, cy = edge_x + FEATURE_FLICK_DISTANCE / 2, row_top + FEATURE_VISIBLE_ROWS * FEATURE_ROW_HEIGHT / 2
        direction = 1 if pull_x < 0 else -1
        tip = rl.Vector2(cx + direction * 8, cy)
        rl.draw_line_ex(rl.Vector2(cx - direction * 8, cy - 16), tip, 4, TEXT_PRIMARY)
        rl.draw_line_ex(tip, rl.Vector2(cx - direction * 8, cy + 16), 4, TEXT_PRIMARY)
      if pull_x:
        rl.rl_push_matrix()
      try:
        if pull_x:
          rl.rl_translatef(pull_x, 0, 0)
          rl.draw_rectangle_rec(rl.Rectangle(left + 25, row_top, 2100 - left, FEATURE_VISIBLE_ROWS * FEATURE_ROW_HEIGHT), PANEL_BG)
        for visible, row in enumerate(rows_state.rows[rows_state.scroll:rows_state.scroll + FEATURE_VISIBLE_ROWS]):
          y = row_top + visible * FEATURE_ROW_HEIGHT
          value = _boolean_value(row)
          heading = (bool(row.label) and not (row.key or row.page or row.value or row.reason or
                                             row.choices or row.step or row.repair_value or row.actions))
          if value is True and row.available:
            bounds = rl.Rectangle(left + 28, y + 2, 2098 - left, FEATURE_ROW_HEIGHT - 8)
            draw_rounded_fill(bounds, ACTIVE_ROW_BG, radius_px=12)
            draw_rounded_stroke(bounds, ACTIVE_ROW_BORDER, radius_px=12)
          rl.draw_line(left + 55, y + FEATURE_ROW_HEIGHT - 3, 2094, y + FEATURE_ROW_HEIGHT - 3, ROW_SEPARATOR)
          has_control = bool(row.actions or row.page or _confirmation(row) or row.available or value is not None)
          width = (feature_action_left(row) - 24 if has_control else 2094) - (left + 55)
          detail = row.value + (" " + row.unit if row.unit and row.value != "Auto" else "")
          if value is not None or (row.available and not row.actions and not row.page and not _confirmation(row) and not row.repair_value):
            detail = ""
          if row.page and detail in ("Saved settings", "Saved preferences", "Saved profiles"):
            detail = ""
          detail += (" - " if detail and row.reason else "") + row.reason
          label = self._elide(row.label, FontRole.NORMAL, LABEL_SIZE, width)
          detail = self._elide(detail, FontRole.NORMAL, DETAIL_SIZE, width)
          label_top, label_bottom = self.fonts.vertical_ink(label, FontRole.NORMAL, LABEL_SIZE)
          detail_top, detail_bottom = self.fonts.vertical_ink(detail, FontRole.NORMAL, DETAIL_SIZE) if detail else (0, 0)
          height = label_bottom - label_top + (12 + detail_bottom - detail_top if detail else 0)
          top = y + (FEATURE_ROW_HEIGHT - height) / 2
          self.fonts.draw(label, FontRole.NORMAL, LABEL_SIZE, left + 55, top - label_top, TEXT_MUTED if heading else TEXT_PRIMARY)
          if detail:
            self.fonts.draw(detail, FontRole.NORMAL, DETAIL_SIZE, left + 55,
                            top + label_bottom - label_top + 12 - detail_top, TEXT_SECONDARY)
          if heading:
            continue
          action = rl.Rectangle(FEATURE_CONTROL_LEFT, y + FEATURE_ACTION_MARGIN, FEATURE_CONTROL_RIGHT - FEATURE_CONTROL_LEFT,
                                FEATURE_ROW_HEIGHT - 2 * FEATURE_ACTION_MARGIN)
          if row.actions:
            for index, (text, enabled) in enumerate(row.actions):
              button = rl.Rectangle(feature_action_left(row) + index * (action.width + 16), action.y, action.width, action.height)
              draw_rounded_fill(button, CONTROL_BG)
              draw_rounded_stroke(button, CONTROL_BORDER)
              self._center(self._elide(text, FontRole.MEDIUM, DETAIL_SIZE, button.width - 24), DETAIL_SIZE, button,
                           TEXT_PRIMARY if row.available and enabled else TEXT_MUTED)
          elif row.page:
            self._center("Open >", DETAIL_SIZE, action, TEXT_PRIMARY if row.available else TEXT_MUTED)
          elif _confirmation(row):
            if row.key in ("torque_adopt", "slc_adopt"):
              action = "Adopt…"
            elif row.key in ("torque_rebase", "torque_gain_rebase"):
              action = "Review…"
            elif row.key == "torque_prepare_firestar":
              action = "Prepare…"
            elif row.key.startswith("pip:format:"):
              action = "Use…"
            else:
              action = "Restore…" if row.key.startswith("long_repair:") else "Reset…"
            button = rl.Rectangle(FEATURE_CONTROL_LEFT, y + FEATURE_ACTION_MARGIN, FEATURE_CONTROL_RIGHT - FEATURE_CONTROL_LEFT,
                                FEATURE_ROW_HEIGHT - 2 * FEATURE_ACTION_MARGIN)
            draw_rounded_fill(button, CONTROL_BG)
            draw_rounded_stroke(button, CONTROL_BORDER)
            self._center(action, DETAIL_SIZE, button, DANGER if row.available else TEXT_MUTED)
          elif value is not None:
            action = rl.Rectangle(FEATURE_CONTROL_LEFT, y + 18, FEATURE_CONTROL_RIGHT - FEATURE_CONTROL_LEFT, FEATURE_ROW_HEIGHT - 36)
            self._center("On" if value else "Off", LABEL_SIZE, rl.Rectangle(1760, action.y, 220, action.height),
                         TEXT_PRIMARY if row.available else TEXT_MUTED, role=FontRole.NORMAL)
            draw_aether_toggle(rl.Rectangle(1993, y + FEATURE_ROW_HEIGHT / 2 - 30.5, 113, 61), value,
                               available=row.available, seed_id=f"{state.page}:{row.key}")
          elif row.available:
            if row.repair_value:
              draw_rounded_fill(action, CONTROL_BG)
              draw_rounded_stroke(action, CONTROL_BORDER)
              text = f"Set {row.repair_value}"
              if self.fonts.measure(text, FontRole.MEDIUM, DETAIL_SIZE).width <= action.width - 24:
                self._center(text, DETAIL_SIZE, action)
              else:
                self._center("Set", DETAIL_SIZE, rl.Rectangle(action.x, action.y, action.width, action.height / 2))
                self._center(self._elide(row.repair_value, FontRole.MEDIUM, DETAIL_SIZE, action.width - 24), DETAIL_SIZE,
                             rl.Rectangle(action.x, action.y + action.height / 2, action.width, action.height / 2))
            else:
              value_text = row.value + (" " + row.unit if row.unit and row.value != "Auto" else "")
              self._center(self._elide(value_text, FontRole.NORMAL, LABEL_SIZE, action.width - 24), LABEL_SIZE,
                           rl.Rectangle(action.x, y + 12, action.width, FEATURE_BUTTON_TOP - 24), role=FontRole.NORMAL)
              for x, text in ((1760, "-"), (1940, "+")):
                button = rl.Rectangle(x, y + FEATURE_BUTTON_TOP, 155, FEATURE_BUTTON_HEIGHT)
                draw_rounded_fill(button, CONTROL_BG)
                draw_rounded_stroke(button, CONTROL_BORDER)
                self._center(text, DETAIL_SIZE, button)
      finally:
        if pull_x:
          rl.rl_pop_matrix()
      if cover:
        rl.draw_rectangle_rec(rl.Rectangle(left + 25, row_top, 2100 - left, FEATURE_VISIBLE_ROWS * FEATURE_ROW_HEIGHT),
                              rl.Color(PANEL_BG.r, PANEL_BG.g, PANEL_BG.b, cover))
    finally:
      clip.end_scissor_mode()
    self._center("Previous", DETAIL_SIZE, rl.Rectangle(left + 25, 980, 1320 - left - 25, 70),
                 TEXT_PRIMARY if state.scroll > 0 else TEXT_MUTED)
    self._center("Next", DETAIL_SIZE, rl.Rectangle(1320, 980, 800, 70),
                 TEXT_PRIMARY if state.scroll + FEATURE_VISIBLE_ROWS < len(state.rows) else TEXT_MUTED)
    current_page = state.scroll // FEATURE_VISIBLE_ROWS + 1
    total_pages = max(1, (len(state.rows) + FEATURE_VISIBLE_ROWS - 1) // FEATURE_VISIBLE_ROWS)
    self._center(f"{current_page}/{total_pages}", DETAIL_SIZE,
                 rl.Rectangle(feature_page_counter_left(state), 980, FEATURE_PAGE_COUNTER_WIDTH, 70), TEXT_SECONDARY)

  def _center(self, text: str, size: float, rect: rl.Rectangle, color: rl.Color = TEXT_PRIMARY, *, role: FontRole = FontRole.MEDIUM) -> None:
    top, bottom = self.fonts.vertical_ink(text, role, size)
    self.fonts.draw(text, role, size, rect.x + (rect.width - self.fonts.measure(text, role, size).width) / 2,
                    rect.y + rect.height / 2 - (top + bottom) / 2, color)

  def _elide(self, text: str, role: FontRole, size: float, width: float) -> str:
    return elide_text(self.fonts, text, role, size, width)
