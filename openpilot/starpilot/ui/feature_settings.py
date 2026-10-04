"""Large saved-feature editor inside the established Settings right pane."""

import pyray as rl

from openpilot.starpilot.ui import clip
from openpilot.starpilot.ui.feature_settings_state import (
  FeatureRow, FeatureSettingsState, FEATURE_CONFIRM_ACTIONS, is_long_confirm_action, boolean_value as _boolean_value,
  FEATURE_ROW_TOP, FEATURE_ROW_HEIGHT, FEATURE_VISIBLE_ROWS, FEATURE_CONTROL_LEFT, FEATURE_CONTROL_RIGHT,
  FEATURE_BUTTON_TOP, FEATURE_BUTTON_HEIGHT, FEATURE_ACTION_MARGIN, FEATURE_HEADER_HEIGHT,
)
from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile
from openpilot.starpilot.ui.settings_geometry import (
  ACTIVE_ROW_BG, ACTIVE_ROW_BORDER, CONTROL_BG, CONTROL_BORDER, DANGER,
  PANEL_BG, PANEL_BORDER, PANEL_INNER_BORDER, ROW_SEPARATOR, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
  draw_aether_toggle, draw_rounded_fill, draw_rounded_stroke, draw_settings_header, elide_text,
)

LABEL_SIZE = 50
DETAIL_SIZE = 35


def _confirmation(row: FeatureRow) -> bool:
  return row.key in FEATURE_CONFIRM_ACTIONS or row.key.startswith("pip:format:") or is_long_confirm_action(row.key)


class FeatureSettingsView:
  def __init__(self, fonts: BitmapFonts):
    if fonts.profile != Profile.LARGE:
      raise ValueError("Large profile only")
    self.fonts = fonts

  def render(self, state: FeatureSettingsState) -> None:
    left = 520 if state.sidebar_expanded else 20
    shell = rl.Rectangle(left - 10, 10, 2160 - left, 1060)
    draw_rounded_fill(shell, PANEL_BG, radius_px=32)
    draw_rounded_stroke(shell, PANEL_BORDER, radius_px=32)
    draw_rounded_stroke(rl.Rectangle(shell.x + 2, 12, shell.width - 4, 1056), PANEL_INNER_BORDER, radius_px=29)
    clip.begin_scissor_mode(left, 12, 2140 - left, FEATURE_HEADER_HEIGHT)
    try:
      draw_settings_header(self.fonts, state.sidebar_expanded, state.title, state.parent_title, back=True)
    finally:
      clip.end_scissor_mode()
    subtitle = self._elide(state.subtitle, FontRole.NORMAL, DETAIL_SIZE, 2094 - left - 55)
    if subtitle:
      top, _ = self.fonts.vertical_ink(subtitle, FontRole.NORMAL, DETAIL_SIZE)
      self.fonts.draw(subtitle, FontRole.NORMAL, DETAIL_SIZE, left + 55, 116 - top, TEXT_SECONDARY)
    clip.begin_scissor_mode(left + 25, FEATURE_ROW_TOP, 2100 - left, FEATURE_VISIBLE_ROWS * FEATURE_ROW_HEIGHT)
    try:
      for visible, row in enumerate(state.rows[state.scroll:state.scroll + FEATURE_VISIBLE_ROWS]):
        y = FEATURE_ROW_TOP + visible * FEATURE_ROW_HEIGHT
        value = _boolean_value(row)
        heading = (bool(row.label) and not (row.key or row.page or row.value or row.reason or
                                           row.choices or row.step or row.repair_value))
        if value is True and row.available:
          bounds = rl.Rectangle(left + 28, y + 2, 2098 - left, FEATURE_ROW_HEIGHT - 8)
          draw_rounded_fill(bounds, ACTIVE_ROW_BG, radius_px=12)
          draw_rounded_stroke(bounds, ACTIVE_ROW_BORDER, radius_px=12)
        rl.draw_line(left + 55, y + FEATURE_ROW_HEIGHT - 3, 2094, y + FEATURE_ROW_HEIGHT - 3, ROW_SEPARATOR)
        has_control = bool(row.page or _confirmation(row) or row.available or value is not None)
        width = (FEATURE_CONTROL_LEFT - 24 if has_control else 2094) - (left + 55)
        detail = row.value + (" " + row.unit if row.unit and row.value != "Auto" else "")
        if value is not None or (row.available and not row.page and not _confirmation(row) and not row.repair_value):
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
        if row.page:
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
      clip.end_scissor_mode()
    self._center("Previous", DETAIL_SIZE, rl.Rectangle(left + 25, 980, 1320 - left - 25, 70),
                 TEXT_PRIMARY if state.scroll > 0 else TEXT_MUTED)
    self._center("Next", DETAIL_SIZE, rl.Rectangle(1320, 980, 800, 70),
                 TEXT_PRIMARY if state.scroll + FEATURE_VISIBLE_ROWS < len(state.rows) else TEXT_MUTED)

  def _center(self, text: str, size: float, rect: rl.Rectangle, color: rl.Color = TEXT_PRIMARY, *, role: FontRole = FontRole.MEDIUM) -> None:
    top, bottom = self.fonts.vertical_ink(text, role, size)
    self.fonts.draw(text, role, size, rect.x + (rect.width - self.fonts.measure(text, role, size).width) / 2,
                    rect.y + rect.height / 2 - (top + bottom) / 2, color)

  def _elide(self, text: str, role: FontRole, size: float, width: float) -> str:
    return elide_text(self.fonts, text, role, size, width)
