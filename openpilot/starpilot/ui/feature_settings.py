"""Large saved-feature editor inside the established Settings right pane."""

import pyray as rl

from openpilot.starpilot.ui import clip
from openpilot.starpilot.ui.feature_settings_state import (
  FeatureRow, FeatureSettingsState, FEATURE_CONFIRM_ACTIONS, is_long_confirm_action,
)
from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile
from openpilot.starpilot.ui.settings_geometry import (
  ACCENT, ACTIVE_ROW_BG, ACTIVE_ROW_BORDER, CONTROL_BG, CONTROL_BORDER, DANGER,
  PANEL_BG, PANEL_BORDER, PANEL_INNER_BORDER, ROW_SEPARATOR, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
  constellation, draw_aether_toggle, draw_constellation_nodes, draw_hud_background, draw_rounded_fill, draw_rounded_stroke,
)


def _confirmation(row: FeatureRow) -> bool:
  return row.key in FEATURE_CONFIRM_ACTIONS or row.key.startswith("pip:format:") or is_long_confirm_action(row.key)


def _boolean_value(row: FeatureRow) -> bool | None:
  if not row.key or row.page or row.repair_value or row.step or _confirmation(row) or row.choices != ("Off", "On"):
    return None
  if row.value in ("Off", "On"):
    return row.value == "On"
  if row.key == "SLCFallback" and row.value == "Off (saved mode 0 or 1)":
    return False
  return None


class FeatureSettingsView:
  def __init__(self, fonts: BitmapFonts):
    if fonts.profile != Profile.LARGE:
      raise ValueError("Large profile only")
    self.fonts = fonts

  def render(self, state: FeatureSettingsState) -> None:
    shell = rl.Rectangle(510, 10, 1640, 1060)
    draw_rounded_fill(shell, PANEL_BG, radius_px=32)
    draw_rounded_stroke(shell, PANEL_BORDER, radius_px=32)
    draw_rounded_stroke(rl.Rectangle(512, 12, 1636, 1056), PANEL_INNER_BORDER, radius_px=29)
    back = rl.Rectangle(545, 24, 205, 72)
    draw_rounded_fill(back, CONTROL_BG)
    draw_rounded_stroke(back, CONTROL_BORDER)
    self.fonts.draw("< Back", FontRole.MEDIUM, 37, 570, 38, TEXT_PRIMARY)
    header = rl.Rectangle(780, 24, 1345, 72)
    draw_hud_background(header, ACCENT, 0.5, radius_px=34)
    clip.begin_scissor_mode(header.x, header.y, header.width, header.height)
    try:
      if self.fonts.measure(state.title, FontRole.SEMI_BOLD, 52).width <= 1144:
        decoration = rl.Rectangle(1968, 32, 144, 56)
        nodes, edges = constellation(state.title, decoration)
        draw_constellation_nodes(nodes, edges, decoration, ACCENT, 0.25, scale=0.45)
      self.fonts.draw(self._elide(state.title, FontRole.SEMI_BOLD, 52, 1305), FontRole.SEMI_BOLD, 52, 800, 31, TEXT_PRIMARY)
    finally:
      clip.end_scissor_mode()
    subtitle = self._elide(state.subtitle, FontRole.NORMAL, 27, 1545)
    if subtitle:
      _, bottom = self.fonts.vertical_ink(subtitle, FontRole.NORMAL, 27)
      self.fonts.draw(subtitle, FontRole.NORMAL, 27, 560, 126 - bottom, TEXT_SECONDARY)
    clip.begin_scissor_mode(545, 130, 1580, 837)
    try:
      for visible, row in enumerate(state.rows[state.scroll:state.scroll + 8]):
        y = 130 + visible * 104
        value = _boolean_value(row)
        heading = (bool(row.label) and not (row.key or row.page or row.value or row.reason or
                                           row.choices or row.step or row.repair_value))
        if value is True and row.available:
          bounds = rl.Rectangle(548, y + 2, 1570, 96)
          draw_rounded_fill(bounds, ACTIVE_ROW_BG, radius_px=12)
          draw_rounded_stroke(bounds, ACTIVE_ROW_BORDER, radius_px=12)
        rl.draw_line(575, y + 98, 2094, y + 98, ROW_SEPARATOR)
        has_control = bool(row.page or _confirmation(row) or row.available or value is not None)
        width = 1149 if has_control else 1519
        self.fonts.draw(self._elide(row.label, FontRole.MEDIUM, 31, width), FontRole.MEDIUM, 31,
                        575, y + 12, TEXT_MUTED if heading else TEXT_PRIMARY)
        if heading:
          continue
        detail = row.value + (" " + row.unit if row.unit and row.value != "Auto" else "")
        if row.reason:
          detail += (" - " if detail else "") + row.reason
        self.fonts.draw(self._elide(detail, FontRole.NORMAL, 27, width), FontRole.NORMAL, 27,
                        575, y + 54, TEXT_SECONDARY)
        if row.page:
          self.fonts.draw("Open >", FontRole.MEDIUM, 32, 1930, y + 29, TEXT_PRIMARY if row.available else TEXT_MUTED)
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
          self.fonts.draw(action, FontRole.MEDIUM, 32, 1880, y + 29,
                          DANGER if row.available else TEXT_MUTED)
        elif value is not None:
          action = rl.Rectangle(1748, y + 10, 370, 80)
          draw_rounded_fill(action, CONTROL_BG)
          draw_rounded_stroke(action, CONTROL_BORDER)
          self.fonts.draw("On" if value else "Off", FontRole.MEDIUM, 32, 1770, y + 25,
                          TEXT_PRIMARY if row.available else TEXT_MUTED)
          draw_aether_toggle(rl.Rectangle(1993, y + 20, 113, 61), value,
                             available=row.available, seed_id=f"{state.page}:{row.key}")
        elif row.available:
          if not row.repair_value:
            button = rl.Rectangle(1760, y + 19, 155, 60)
            draw_rounded_fill(button, CONTROL_BG)
            draw_rounded_stroke(button, CONTROL_BORDER)
          button = rl.Rectangle(1940, y + 19, 155, 60)
          draw_rounded_fill(button, CONTROL_BG)
          draw_rounded_stroke(button, CONTROL_BORDER)
          if not row.repair_value:
            self.fonts.draw("-", FontRole.MEDIUM, 39, 1815, y + 25, TEXT_PRIMARY)
          text = self._elide(f"Set {row.repair_value}", FontRole.MEDIUM, 29, 125) if row.repair_value else "+"
          self.fonts.draw(text, FontRole.MEDIUM, 29 if row.repair_value else 39, 1960, y + 25, TEXT_PRIMARY)
    finally:
      clip.end_scissor_mode()
    self.fonts.draw("Previous", FontRole.MEDIUM, 30, 1000, 993,
                    TEXT_PRIMARY if state.scroll > 0 else TEXT_MUTED)
    self.fonts.draw("Next", FontRole.MEDIUM, 30, 1480, 993,
                    TEXT_PRIMARY if state.scroll + 8 < len(state.rows) else TEXT_MUTED)

  def _elide(self, text: str, role: FontRole, size: float, width: float) -> str:
    if self.fonts.measure(text, role, size).width <= width:
      return text
    suffix = "..."
    low, high = 0, len(text)
    while low < high:
      middle = (low + high + 1) // 2
      if self.fonts.measure(text[:middle] + suffix, role, size).width <= width:
        low = middle
      else:
        high = middle - 1
    return text[:low] + suffix
