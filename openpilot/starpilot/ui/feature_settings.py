"""Large saved-feature editor inside the established Settings right pane."""

import pyray as rl

from openpilot.starpilot.ui import clip
from openpilot.starpilot.ui.feature_settings_state import (
  FeatureSettingsState, FEATURE_CONFIRM_ACTIONS, is_long_confirm_action,
)
from openpilot.starpilot.ui.presentation import BitmapFonts, FontRole, Profile


class FeatureSettingsView:
  def __init__(self, fonts: BitmapFonts):
    if fonts.profile != Profile.LARGE:
      raise ValueError("Large profile only")
    self.fonts = fonts

  def render(self, state: FeatureSettingsState) -> None:
    rl.draw_rectangle_rounded(rl.Rectangle(510, 10, 1640, 1060), 0.04, 30, rl.BLACK)
    rl.draw_rectangle_rounded(rl.Rectangle(545, 24, 205, 72), 0.25, 12, rl.Color(44, 39, 62, 255))
    self.fonts.draw("< Back", FontRole.MEDIUM, 37, 570, 38)
    self.fonts.draw(state.title, FontRole.SEMI_BOLD, 52, 800, 31)
    self.fonts.draw(state.subtitle, FontRole.NORMAL, 27, 560, 103, rl.Color(162, 162, 162, 255))
    clip.begin_scissor_mode(545, 130, 1580, 837)
    try:
      for visible, row in enumerate(state.rows[state.scroll:state.scroll + 8]):
        y = 130 + visible * 104
        rl.draw_rectangle_rounded(rl.Rectangle(548, y + 2, 1570, 96), 0.12, 12,
                                  rl.Color(29, 26, 37, 255))
        self.fonts.draw(row.label, FontRole.MEDIUM, 31, 575, y + 12)
        detail = row.value + (" " + row.unit if row.unit and row.value != "Auto" else "")
        if row.reason:
          detail += " - " + row.reason
        self.fonts.draw(detail[:56], FontRole.NORMAL, 27,
                        575, y + 54, rl.Color(190, 185, 205, 255))
        if row.page:
          self.fonts.draw("Open >", FontRole.MEDIUM, 32, 1930, y + 29)
        elif (row.key in FEATURE_CONFIRM_ACTIONS or row.key.startswith("pip:format:") or
              is_long_confirm_action(row.key)):
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
                          rl.Color(245, 130, 130, 255) if row.available else rl.GRAY)
        elif row.available:
          if not row.repair_value:
            rl.draw_rectangle_rounded(rl.Rectangle(1760, y + 19, 155, 60), 0.2, 8, rl.Color(53, 45, 74, 255))
          rl.draw_rectangle_rounded(rl.Rectangle(1940, y + 19, 155, 60), 0.2, 8, rl.Color(53, 45, 74, 255))
          if not row.repair_value:
            self.fonts.draw("-", FontRole.MEDIUM, 39, 1815, y + 25)
          self.fonts.draw(f"Set {row.repair_value}" if row.repair_value else "+", FontRole.MEDIUM,
                          29 if row.repair_value else 39, 1960, y + 25)
        elif row.reason:
          self.fonts.draw(row.reason[:45], FontRole.NORMAL, 22, 1370, y + 64, rl.GRAY)
    finally:
      clip.end_scissor_mode()
    self.fonts.draw("Previous", FontRole.MEDIUM, 30, 1000, 993,
                    rl.WHITE if state.scroll > 0 else rl.GRAY)
    self.fonts.draw("Next", FontRole.MEDIUM, 30, 1480, 993,
                    rl.WHITE if state.scroll + 8 < len(state.rows) else rl.GRAY)
