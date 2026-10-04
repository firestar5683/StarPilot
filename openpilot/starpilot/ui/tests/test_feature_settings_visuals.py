"""Presentation edge cases without constructing device services or GPU resources."""

from contextlib import ExitStack
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pyray as rl

from openpilot.starpilot.ui import clip, feature_settings as view, settings_geometry as geometry
from openpilot.starpilot.ui.feature_settings_state import (
  FeatureInput, FeatureRow, FeatureSettingsState, FEATURE_ROW_TOP, FEATURE_ROW_HEIGHT, FEATURE_VISIBLE_ROWS, feature_scroll,
)
from openpilot.starpilot.ui.presentation import FontRole, Profile


def fake_fonts():
  return SimpleNamespace(profile=Profile.LARGE, draw=Mock(),
                         measure=lambda text, _role, size: SimpleNamespace(width=len(text) * size * .5),
                         vertical_ink=lambda *_args: (6, 33))


class FeatureVisualTests(unittest.TestCase):
  def drawing(self):
    stack = ExitStack()
    self.addCleanup(stack.close)
    for name in ("draw_rectangle_rounded", "draw_rectangle_rounded_lines_ex", "draw_line", "draw_line_ex",
                 "draw_circle", "begin_scissor_mode", "end_scissor_mode", "rl_push_matrix", "rl_pop_matrix", "rl_translatef"):
      stack.enter_context(patch.object(rl, name))
    return stack

  def test_boolean_uses_display_value_and_excludes_other_controls(self):
    row = FeatureRow("switch", "Switch", "Off", b"1", ("Off", "On"), available=True)
    self.assertIs(view._boolean_value(row), False)
    self.assertIs(view._boolean_value(replace(row, value="On", available=False)), True)
    for changes in ({"key": ""}, {"page": "child"}, {"repair_value": "Off"}, {"step": 1},
                    {"key": "pip:reset"}, {"key": "pip:format:test"}, {"key": "long_repair:test"},
                    {"choices": ("Stock", "On")}, {"choices": ("Off", "Auto", "On")},
                    {"value": "Invalid saved choice"}, {"choices": ()}):
      with self.subTest(changes=changes):
        self.assertIsNone(view._boolean_value(replace(row, **changes)))
    special = replace(row, key="SLCFallback", value="Off (saved mode 0 or 1)")
    self.assertIs(view._boolean_value(special), False)
    self.assertIsNone(view._boolean_value(replace(special, key="other")))

  def test_toggle_stars_only_for_editable_on_and_thumb_keeps_saved_position(self):
    self.drawing()
    rect = rl.Rectangle(1993, 150, 113, 61)
    with patch.object(geometry, "draw_constellation_nodes") as stars:
      centers = {}
      for available in (True, False):
        for value in (False, True):
          rl.draw_rectangle_rounded.reset_mock()
          stars.reset_mock()
          geometry.draw_aether_toggle(rect, value, available=available, seed_id="lane:switch")
          self.assertEqual(stars.call_count, int(available and value))
          self.assertTrue(all(call.args[-1].a > 0 for call in rl.draw_rectangle_rounded.call_args_list))
          knob = next(call.args[0] for call in rl.draw_rectangle_rounded.call_args_list
                      if call.args[0].width == 44)
          centers[available, value] = knob.x + knob.width / 2
      self.assertEqual(centers[True, False], centers[False, False])
      self.assertEqual(centers[True, True], centers[False, True])
      self.assertLess(centers[True, False], centers[True, True])

  def test_constellations_are_stable_bounded_and_visible_before_thumb(self):
    geometry._toggle_constellation.cache_clear()
    self.addCleanup(geometry._toggle_constellation.cache_clear)
    original = geometry._toggle_constellation("lane:first")
    for index in range(160):
      nodes, edges = geometry._toggle_constellation(f"lane:{index}")
      self.assertTrue(2 <= len(nodes) <= 4)
      self.assertTrue(all(node['x'] * 113 + 3 * 0.45 < 62 for node in nodes))
      self.assertTrue(all(0 <= first < len(nodes) and 0 <= second < len(nodes) for first, second in edges))
    self.assertLessEqual(geometry._toggle_constellation.cache_info().currsize, 128)
    self.assertEqual(original, geometry._toggle_constellation("lane:first"))

  def test_mixed_rows_do_not_replace_repairs_actions_or_selectors(self):
    self.drawing()
    fonts = fake_fonts()
    row = FeatureRow("switch", "Switch", "On", choices=("Off", "On"), available=True)
    rows = (row, replace(row, available=False), replace(row, key="repair", repair_value="Off"),
            replace(row, key="power", choices=("Stock", "On")), replace(row, key="pip:reset"),
            FeatureRow("", "Runtime", "Healthy"), FeatureRow("", "Following", ""))
    with patch.object(view, "draw_aether_toggle") as toggles:
      for scroll in range(0, len(rows), FEATURE_VISIBLE_ROWS):
        view.FeatureSettingsView(fonts).render(FeatureSettingsState(rows=rows, scroll=scroll))
    self.assertEqual(toggles.call_count, 2)
    texts = [call.args[0] for call in fonts.draw.call_args_list]
    for text in ("Set Off", "+", "Reset…", "Healthy", "Following"):
      self.assertIn(text, texts)
    healthy = next(call for call in fonts.draw.call_args_list if call.args[0] == "Healthy")
    self.assertEqual(healthy.args[-1], geometry.TEXT_SECONDARY)
    plus = next(call for call in fonts.draw.call_args_list if call.args[0] == "+")
    self.assertEqual(plus.args[2], view.DETAIL_SIZE)

  def test_repair_targets_stay_complete_and_fit_the_button(self):
    self.drawing()
    fonts = fake_fonts()
    renderer = view.FeatureSettingsView(fonts)
    for target in ("0", "Off", "On", "Stock", "Reset", "Auto", "30 s", "10 s", "4.0", "starpilot"):
      with self.subTest(target=target):
        fonts.draw.reset_mock()
        row = FeatureRow("repair", "Repair", "Invalid", available=True, repair_value=target)
        renderer.render(FeatureSettingsState(rows=(row,)))
        labels = [call for call in fonts.draw.call_args_list if call.args[0] in (f"Set {target}", "Set", target)]
        self.assertEqual(" ".join(call.args[0] for call in labels), f"Set {target}")
        for label in labels:
          self.assertLessEqual(fonts.measure(*label.args[:3]).width, 346)
          self.assertEqual(label.args[2], view.DETAIL_SIZE)

  def test_long_text_fits_and_subtitle_ink_clears_rows(self):
    self.drawing()
    fonts = fake_fonts()
    renderer = view.FeatureSettingsView(fonts)
    state = FeatureSettingsState(title="Long title " * 30, subtitle="Subtitle with descenders",
                                 rows=(FeatureRow("switch", "Long label " * 30, "On", choices=("Off", "On"), available=True),))
    renderer.render(state)
    title = next(call for call in fonts.draw.call_args_list if call.args[0].startswith("Long title"))
    self.assertLessEqual(fonts.measure(*title.args[:3]).width, 1372)
    label = next(call for call in fonts.draw.call_args_list if call.args[0].startswith("Long label"))
    self.assertLessEqual(fonts.measure(*label.args[:3]).width, 1149)
    subtitle = next(call for call in fonts.draw.call_args_list if call.args[0] == state.subtitle)
    self.assertLess(subtitle.args[4] + 33, FEATURE_ROW_TOP)
    self.assertEqual(renderer._elide("Fits", FontRole.NORMAL, 27, 100), "Fits")
    renderer.render(FeatureSettingsState(rows=(FeatureRow("choice", "Choice", "Long value", available=True),)))
    selector = next(call for call in fonts.draw.call_args_list if call.args[0] == "Long value")
    self.assertEqual(selector.args[2], view.LABEL_SIZE)

  def test_clip_restored_on_failure_at_translated_widget_position(self):
    self.drawing()
    fonts = fake_fonts()
    viewport = rl.Rectangle(20, 30, 2160, 1080)
    with clip.placed_at(viewport):
      with patch.object(view, "draw_settings_header", side_effect=RuntimeError("drawing failed")):
        with self.assertRaisesRegex(RuntimeError, "drawing failed"):
          view.FeatureSettingsView(fonts).render(FeatureSettingsState())
      self.assertEqual(rl.begin_scissor_mode.call_args.args, (20, 30, 2160, 1080))
    rl.end_scissor_mode.assert_called()

  def test_all_rows_reachable_without_skipping_or_repeating_on_last_page(self):
    for count in (0, 1, 4, 5, 8, 9, 13):
      with self.subTest(count=count):
        rows = tuple(FeatureRow("", str(index), "", page=str(index), available=True) for index in range(count))
        scroll, reached = 0, []
        while True:
          state = FeatureSettingsState(rows=rows, scroll=scroll)
          for index in range(min(FEATURE_VISIBLE_ROWS, count - scroll)):
            action = FeatureInput.target(600, FEATURE_ROW_TOP + (index + .5) * FEATURE_ROW_HEIGHT, state)
            self.assertEqual(action.kind, "open")
            reached.append(action.row)
          next_scroll = feature_scroll(scroll, 1, count)
          if next_scroll == scroll:
            break
          scroll = next_scroll
        self.assertEqual(reached, list(rows))
        self.assertIsNone(FeatureInput.target(600, FEATURE_ROW_TOP + FEATURE_VISIBLE_ROWS * FEATURE_ROW_HEIGHT, state))
        while scroll:
          scroll = feature_scroll(scroll, -1, count)
        self.assertEqual(scroll, 0)

  def test_numeric_value_is_read_only_and_buttons_keep_source_binding(self):
    row = FeatureRow("number", "Number", "75", b"75", step=5, available=True)
    state = FeatureSettingsState(rows=(row,))
    self.assertEqual(FeatureInput.target(1930, FEATURE_ROW_TOP + 50, state).kind, "details")
    self.assertEqual(FeatureInput.target(1820, FEATURE_ROW_TOP + 140, state).direction, -1)
    self.assertEqual(FeatureInput.target(2000, FEATURE_ROW_TOP + 140, state).direction, 1)
    self.assertEqual(FeatureInput.target(1925, FEATURE_ROW_TOP + 140, state).kind, "details")
    self.assertIsNone(FeatureInput.target(2000, FEATURE_ROW_TOP + 140, replace(state, rows=(replace(row, available=False),))))
    actions = []
    owner = FeatureInput(actions.append)
    owner.press(2000, FEATURE_ROW_TOP + 140, state)
    owner.release(2000, FEATURE_ROW_TOP + 140, replace(state, sidebar_expanded=False))
    self.assertFalse(actions)

  def test_collapsed_header_and_content_share_the_expanded_keyline(self):
    self.drawing()
    fonts = fake_fonts()
    for expanded, left in ((True, 520), (False, 20)):
      fonts.draw.reset_mock()
      state = FeatureSettingsState(title="Lane Centering", parent_title="Driving Controls", sidebar_expanded=expanded,
                                   subtitle="Help", rows=(FeatureRow("key", "Setting", "On", choices=("Off", "On"), available=True),))
      view.FeatureSettingsView(fonts).render(state)
      label = next(call for call in fonts.draw.call_args_list if call.args[0] == "Setting")
      self.assertEqual(label.args[3], left + 55)
      self.assertEqual(label.args[2], 50)
      self.assertEqual(label.args[1], FontRole.NORMAL)
      self.assertTrue(all(call.args[2] in (35, 50) for call in fonts.draw.call_args_list))
      header = [call for call in fonts.draw.call_args_list
                if call.args[0] == "< Back" or call.args[0].startswith("Driving Controls") or call.args[0] == "Lane Centering"]
      self.assertEqual(len(header), 3)
      self.assertTrue(all(call.args[1:3] == (FontRole.MEDIUM, 35) for call in header))
      self.assertEqual(len({call.args[4] for call in header}), 1)
      self.assertNotEqual(FeatureInput.target(left + 60, 120, state).kind, "back")
      self.assertEqual(FeatureInput.target(left + 60, 76, state).kind, "back")
      self.assertEqual(FeatureInput.target(left + 300, 76, state).kind, "details")


if __name__ == "__main__":
  unittest.main()
