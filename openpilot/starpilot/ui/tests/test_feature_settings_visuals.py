"""Presentation edge cases without constructing device services or GPU resources."""

from contextlib import ExitStack
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pyray as rl

from openpilot.starpilot.ui import clip, feature_settings as view, settings_geometry as geometry
from openpilot.starpilot.ui.feature_settings_state import (
  FeatureInput, FeatureRow, FeatureSettingsState, FEATURE_ROW_TOP, FEATURE_ROW_HEIGHT, FEATURE_VISIBLE_ROWS,
  feature_scroll, feature_row_top, sound_buttons, sound_editor_rect, sound_done_rect,
)
from openpilot.starpilot.ui.presentation import FontRole, Profile


def fake_fonts():
  return SimpleNamespace(profile=Profile.LARGE, draw=Mock(),
                         measure=lambda text, _role, size: SimpleNamespace(width=len(text) * size * .5),
                         vertical_ink=lambda *_args: (6, 33))


class FeatureVisualTests(unittest.TestCase):
  def test_sound_overview_shows_values_without_edit_controls(self):
    self.drawing()
    for expanded in (True, False):
      rows = (FeatureRow("EngageVolume", "Engagement Chime", "40", source=b"40", unit="%", step=5,
                         minimum=0, maximum=100, available=True, page="EngageVolume"),
              FeatureRow("SoundPack", "Sound Pack", "StarPilot (Built-in)", available=True, page="SoundPack"))
      state = FeatureSettingsState(page="sounds:overview", rows=rows, sidebar_expanded=expanded)
      fonts = fake_fonts()
      view.FeatureSettingsView(fonts).render(state)
      text = [call.args[0] for call in fonts.draw.call_args_list]
      self.assertIn("40%", text)
      self.assertIn("StarPilot (Built-in)", text)
      self.assertNotIn("Mute", text)
      self.assertNotIn("+", text)
      self.assertNotIn("-", text)
      for i, row in enumerate(rows):
        target = FeatureInput.target(800, feature_row_top(state) + i * FEATURE_ROW_HEIGHT + 77, state)
        self.assertEqual(target.kind, "open")
        self.assertEqual(target.row, row)

  def test_sound_value_and_legal_presets_share_drawn_touch_bounds(self):
    self.drawing()
    for expanded in (True, False):
      for key, minimum in (("WarningSoftVolume", 25), ("EngageVolume", 0)):
        for value in ("40", "50", "Auto", *(() if minimum else ("0",))):
          row = FeatureRow(key, "Alert", value, source=value.encode(), step=5, minimum=minimum, maximum=100,
                           available=True, reason="Existing details")
          state = FeatureSettingsState(page="sounds", rows=(row,), sidebar_expanded=expanded)
          fonts = fake_fonts()
          rl.draw_line_ex.reset_mock()
          rl.draw_rectangle_rounded_lines_ex.reset_mock()
          with patch.object(view, "draw_settings_header"):
            view.FeatureSettingsView(fonts).render(state)
          rl.draw_line_ex.assert_not_called()
          selected = [call for call in rl.draw_rectangle_rounded_lines_ex.call_args_list if call.args[-1] == view.SOUND_SELECTED_BORDER]
          self.assertEqual(len(selected), 1 if value == "40" else 2)
          rl.draw_rectangle_rounded_lines_ex.reset_mock()
          text = [call.args[0] for call in fonts.draw.call_args_list]
          self.assertIn("Muted" if value == "0" else value if value == "Auto" else value + "%", text)
          self.assertNotIn(row.reason, text)
          self.assertEqual("Mute" in text, minimum == 0)
          self.assertEqual("10%" in text, minimum == 0)
          saved = next(call for call in fonts.draw.call_args_list if call.args[1] == FontRole.SEMI_BOLD)
          self.assertEqual(saved.args[2], 140)
          self.assertEqual(saved.args[-1], geometry.ACCENT)
          self.assertIn("Done", text)
          self.assertNotIn("Back", text)
          self.assertNotIn("Next", text)
          buttons = sound_buttons(state, row, feature_row_top(state))
          first, last = buttons[1][1], buttons[-2][1]
          cx, cy, editor_width, editor_height = sound_editor_rect(state)
          self.assertEqual(cx, (520 if expanded else 20) + 55)
          self.assertAlmostEqual(saved.args[3] + fonts.measure(*saved.args[:3]).width / 2, cx + editor_width / 2)
          top, bottom = fonts.vertical_ink(*saved.args[:3])
          self.assertAlmostEqual(saved.args[4] + (top + bottom) / 2, buttons[0][1][1] + buttons[0][1][3] / 2)
          self.assertEqual(first[0], cx)
          self.assertAlmostEqual(last[0] + last[2], 2094)
          self.assertGreater(first[1], buttons[0][1][1] + buttons[0][1][3])
          bx, by, bw, bh = sound_done_rect(state)
          done = next(call for call in fonts.draw.call_args_list if call.args[0] == "Done")
          self.assertAlmostEqual(done.args[3] + fonts.measure(*done.args[:3]).width / 2, bx + bw / 2)
          self.assertLessEqual(by + bh, cy + editor_height)
          self.assertGreater(by, last[1] + last[3])
          self.assertEqual((bx, bw, bh), (cx, editor_width, 140))
          self.assertEqual(bx + bw, cx + editor_width)
          self.assertEqual(FeatureInput.target(bx + bw / 2, by + bh / 2, state).kind, "back")
          self.assertEqual(FeatureInput.target(bx + 20, by + bh - 5, state).kind, "back")
          self.assertEqual(FeatureInput.target(bx + bw - 20, by + bh - 5, state).kind, "back")
          self.assertIsNone(FeatureInput.target(1900, by + bh + 10, state))
          for index, (button, (x, y, width, height), enabled) in enumerate(sound_buttons(state, row, feature_row_top(state))):
            label = "Mute" if button == "0" else button if button in ("-", "+", "Auto") else button + "%"
            drawn = next(call for call in fonts.draw.call_args_list if call.args[0] == label and call.args[1] == FontRole.MEDIUM)
            self.assertEqual(height, 200)
            self.assertEqual(drawn.args[2], 64 if button in ("-", "+") else 44)
            self.assertAlmostEqual(drawn.args[3] + fonts.measure(*drawn.args[:3]).width / 2, x + width / 2, delta=.01)
            target = FeatureInput.target(x + width / 2, y + height / 2, state)
            if enabled:
              self.assertEqual(target.kind, "change" if button in ("-", "+") else "action")
              self.assertEqual(target.direction, (-1 if button == "-" else 1) if button in ("-", "+") else index)
            else:
              self.assertIsNone(target)
          self.assertEqual(sound_buttons(replace(state, page="display"), row), ())
          self.assertEqual(FeatureInput.target(1300, feature_row_top(state) + 157, state).kind, "details")
          self.assertIsNone(FeatureInput.target(1300, feature_row_top(state) + 330, state))
          disabled = replace(state, rows=(replace(row, available=False),))
          fonts.draw.reset_mock()
          with patch.object(view, "draw_settings_header"):
            view.FeatureSettingsView(fonts).render(disabled)
          self.assertIn("Editing unavailable", [call.args[0] for call in fonts.draw.call_args_list])
          saved = next(call for call in fonts.draw.call_args_list if call.args[1] == FontRole.SEMI_BOLD)
          self.assertEqual(saved.args[-1], geometry.TEXT_MUTED)
          for _, (x, y, width, height), enabled in sound_buttons(disabled, disabled.rows[0], feature_row_top(disabled)):
            self.assertFalse(enabled)
            self.assertIsNone(FeatureInput.target(x + width / 2, y + height / 2, disabled))

  def test_page_counter_counts_partial_pages_and_aligns_with_footer_in_both_layouts(self):
    self.drawing()
    for expanded in (True, False):
      for count, scroll, expected in ((0, 0, "1/1"), (1, 0, "1/1"), (5, 0, "1/1"), (6, 0, "1/2"),
                                       (6, 5, "2/2"), (20, 0, "1/4"), (20, 15, "4/4"), (13, 10, "3/3")):
        with self.subTest(expanded=expanded, count=count, scroll=scroll):
          fonts = fake_fonts()
          state = FeatureSettingsState(rows=(FeatureRow("", "Heading", ""),) * count, scroll=scroll, sidebar_expanded=expanded)
          view.FeatureSettingsView(fonts).render(state, -80)
          counter, = [call for call in fonts.draw.call_args_list if call.args[0] == expected]
          self.assertEqual(counter.args[1:3], (FontRole.MEDIUM, view.DETAIL_SIZE))
          self.assertIs(counter.args[-1], geometry.TEXT_SECONDARY)
          left = 520 if expanded else 20
          self.assertEqual(counter.args[3] + fonts.measure(*counter.args[:3]).width / 2, (left + 25 + 2120) / 2)
          for label in ("Previous", "Next"):
            button = next(call for call in fonts.draw.call_args_list if call.args[0] == label)
            self.assertEqual(counter.args[4], button.args[4])

  def test_page_change_fades_through_one_row_pass_and_preserves_direction(self):
    self.drawing()
    rows = tuple(FeatureRow("", str(index), "") for index in range(10))
    half = view.PAGE_TRANSITION_TIME / 2
    with patch.object(view, "draw_settings_header"), patch.object(view.time, "monotonic") as clock:
      for direction in (1, -1):
        start = FeatureSettingsState(rows=rows, scroll=0 if direction == 1 else 5)
        end = replace(start, scroll=5 if direction == 1 else 0)
        fonts = fake_fonts()
        renderer = view.FeatureSettingsView(fonts)
        clock.return_value = 0.0
        renderer.render(start, -direction * 80)
        for elapsed, shown, offset, alpha in ((0, start, -direction * 44, 0),
                                             (half / 2, start, -direction * 52, 128),
                                             (half, end, direction * 60, 255),
                                             (half * 1.5, end, direction * 30, 128),
                                             (view.PAGE_TRANSITION_TIME, end, 0, 0)):
          with self.subTest(direction=direction, elapsed=elapsed):
            clock.return_value = elapsed
            fonts.draw.reset_mock()
            rl.draw_rectangle_rec.reset_mock()
            for transform in (rl.rl_push_matrix, rl.rl_translatef, rl.rl_pop_matrix):
              transform.reset_mock()
            renderer.render(end)
            counter, = [call for call in fonts.draw.call_args_list if call.args[0] == f"{end.scroll // FEATURE_VISIBLE_ROWS + 1}/2"]
            self.assertEqual(counter.args[4], 980 + 35 - (6 + 33) / 2)
            labels = [call.args[0] for call in fonts.draw.call_args_list if call.args[0].isdigit()]
            self.assertEqual(labels, [row.label for row in shown.rows[shown.scroll:shown.scroll + 5]])
            self.assertEqual(rl.rl_push_matrix.call_count, int(bool(offset)))
            self.assertEqual(rl.rl_pop_matrix.call_count, int(bool(offset)))
            if offset:
              self.assertAlmostEqual(rl.rl_translatef.call_args.args[0], offset)
            else:
              rl.rl_translatef.assert_not_called()
            fills = rl.draw_rectangle_rec.call_args_list
            self.assertEqual(len(fills), int(bool(offset)) + int(alpha != 0))
            if alpha:
              self.assertAlmostEqual(fills[-1].args[1].a, alpha, delta=1)
        self.assertFalse(renderer.reset(end))

  def test_transition_interruptions_show_current_rows_at_rest(self):
    rows = tuple(FeatureRow("", str(index), "") for index in range(10))
    start = FeatureSettingsState(rows=rows)
    end = replace(start, scroll=5)
    with patch.object(view.time, "monotonic", return_value=0):
      changes = (replace(end, page="other"), replace(end, title="Other"), replace(end, subtitle="Description"),
                 replace(end, sidebar_expanded=False), replace(end, rows=rows[:-1]))
      for changed in changes:
        renderer = view.FeatureSettingsView(fake_fonts())
        renderer._page_frame(start, 0, False)
        renderer._page_frame(end, 0, False)
        self.assertEqual(renderer._page_frame(changed, 0, False), (changed, 0, 0))
        self.assertIsNone(renderer._transition)
      renderer = view.FeatureSettingsView(fake_fonts())
      renderer._page_frame(start, 0, False)
      renderer._page_frame(end, 0, False)
      self.assertTrue(renderer.reset(end))
      self.assertEqual(renderer._page_frame(end, 0, False), (end, 0, 0))
      # Rejected/boundary gestures never change scroll and cannot start a transition.
      renderer._page_frame(end, -18, True)
      self.assertEqual(renderer._page_frame(end, 0, False), (end, 0, 0))
      # A second drag takes over immediately.
      renderer._page_frame(start, 0, False)
      self.assertEqual(renderer._page_frame(start, 24, True), (start, 24, 0))

  def test_pending_swap_and_fast_press_release_are_handled_without_an_intermediate_frame(self):
    rows = tuple(FeatureRow("", str(index), "") for index in range(10))
    start = FeatureSettingsState(rows=rows)
    end = replace(start, scroll=5)
    renderer = view.FeatureSettingsView(fake_fonts())
    with patch.object(view.time, "monotonic", return_value=0):
      renderer._page_frame(start, 0, False)
      self.assertTrue(renderer.reset(end))
      self.assertEqual(renderer._page_frame(end, 0, False), (end, 0, 0))
      renderer.reset(start)
      self.assertEqual(renderer._page_frame(end, 0, False), (start, 0, 0))
      renderer.reset()
      self.assertEqual(renderer._page_frame(end, 0, False), (end, 0, 0))

  def test_pull_policy_reuses_gesture_thresholds_for_both_signs(self):
    for sign in (-1, 1):
      for raw, expected in ((20, 0), (36, 0), (60, 24), (80, 44), (96, 60), (120, 60), (300, 60)):
        self.assertEqual(view.feature_pull(sign * raw, True), sign * expected)
        self.assertEqual(view.feature_pull(sign * raw, False), sign * min(expected, 18))

  def test_edge_reveal_uses_scroll_authority_and_fixed_clip(self):
    self.drawing()
    rows = (FeatureRow("", "Heading", ""),) * 7
    for expanded in (True, False):
      left = 520 if expanded else 20
      for scroll, drag, can_page in ((0, -37.5, True), (5, 37.5, True), (0, -80, True), (5, 80, True),
                                     (0, -300, True), (5, 300, True), (0, 80, False), (5, -80, False), (0, 20, True), (0, 0, False)):
        with self.subTest(expanded=expanded, scroll=scroll, drag=drag):
          rl.draw_rectangle_rec.reset_mock()
          rl.draw_rectangle_gradient_ex.reset_mock()
          rl.draw_line_ex.reset_mock()
          for transform in (rl.rl_push_matrix, rl.rl_translatef, rl.rl_pop_matrix):
            transform.reset_mock()
          fonts = fake_fonts()
          with patch.object(view, "feature_scroll", wraps=feature_scroll) as paging, patch.object(view, "draw_settings_header"):
            view.FeatureSettingsView(fonts).render(FeatureSettingsState(rows=rows, scroll=scroll, sidebar_expanded=expanded), drag)
          if drag:
            paging.assert_called_once_with(scroll, 1 if drag < 0 else -1, len(rows))
          else:
            paging.assert_not_called()
          self.assertEqual(rl.begin_scissor_mode.call_args.args, (left + 25, FEATURE_ROW_TOP, 2100 - left, 5 * FEATURE_ROW_HEIGHT))
          pull = view.feature_pull(drag, can_page)
          self.assertEqual(rl.rl_push_matrix.call_count, int(bool(pull)))
          self.assertEqual(rl.rl_pop_matrix.call_count, int(bool(pull)))
          if pull:
            rl.rl_translatef.assert_called_once_with(pull, 0, 0)
          else:
            rl.rl_translatef.assert_not_called()
          fills = rl.draw_rectangle_rec.call_args_list
          cue = can_page and abs(drag) > 36
          self.assertEqual(len(fills), int(bool(pull)))
          self.assertEqual(rl.draw_rectangle_gradient_ex.call_count, int(cue))
          self.assertEqual(rl.draw_line_ex.call_count, 2 * int(cue))
          if pull:
            self.assertIs(fills[-1].args[1], geometry.PANEL_BG)
            rect = fills[-1].args[0]
            self.assertEqual((rect.x, rect.y, rect.width, rect.height), (left + 25, FEATURE_ROW_TOP, 2100 - left, 5 * FEATURE_ROW_HEIGHT))
          if cue:
            gradient = rl.draw_rectangle_gradient_ex.call_args
            gap = abs(view.feature_pull(drag, can_page))
            bounds = gradient.args[0]
            self.assertEqual((bounds.x, bounds.y, bounds.width, bounds.height),
                             (2125 - gap if drag < 0 else left + 25, FEATURE_ROW_TOP, gap, 5 * FEATURE_ROW_HEIGHT))
            color_left, color_right = (geometry.PANEL_BG, view.EDGE_ACCENT) if drag < 0 else (view.EDGE_ACCENT, geometry.PANEL_BG)
            self.assertEqual(gradient.args[1:], (color_left, color_left, color_right, color_right))
            self.assertEqual(rl.draw_line_ex.call_args.args[0].x, (2095 if drag < 0 else left + 55) + (8 if drag < 0 else -8))
          footer = [call for call in fonts.draw.call_args_list if call.args[0] in ("Previous", "Next")]
          self.assertEqual(len(footer), 2)

  def test_row_failure_restores_matrix_and_scissor(self):
    self.drawing()
    with patch.object(rl, "draw_line", side_effect=RuntimeError("row failed")), patch.object(view, "draw_settings_header"):
      with self.assertRaisesRegex(RuntimeError, "row failed"):
        view.FeatureSettingsView(fake_fonts()).render(FeatureSettingsState(rows=(FeatureRow("", "Heading", ""),)), -80)
    rl.rl_pop_matrix.assert_called_once()
    rl.end_scissor_mode.assert_called()

  def test_description_space_and_row_hit_targets_share_the_rendered_layout(self):
    self.drawing()
    rows = tuple(FeatureRow(str(index), "Setting", "", available=True, actions=(("OPEN", True),)) for index in range(5))
    for expanded in (True, False):
      for subtitle, expected_top in (("", 112), ("Panel description", 164)):
        with self.subTest(expanded=expanded, subtitle=subtitle):
          state = FeatureSettingsState(subtitle=subtitle, rows=rows, sidebar_expanded=expanded)
          fonts = fake_fonts()
          rl.begin_scissor_mode.reset_mock()
          rl.draw_line.reset_mock()
          view.FeatureSettingsView(fonts).render(state)
          self.assertEqual(feature_row_top(state), expected_top)
          self.assertEqual(rl.begin_scissor_mode.call_args.args[1], expected_top)
          separators = [call for call in rl.draw_line.call_args_list if call.args[-1] == geometry.ROW_SEPARATOR]
          for index, row in enumerate(rows):
            y = expected_top + (index + .5) * FEATURE_ROW_HEIGHT
            action = FeatureInput.target(1930, y, state)
            self.assertEqual((action.kind, action.row), ("action", row))
            self.assertEqual(separators[index].args[1], expected_top + (index + 1) * FEATURE_ROW_HEIGHT - 3)
          self.assertIsNone(FeatureInput.target(1930, expected_top + 5 * FEATURE_ROW_HEIGHT, state))
          gap = FeatureInput.target(1930, 108, state)
          self.assertEqual(gap.kind if gap else None, "details" if subtitle else None)
          self.assertEqual(FeatureInput.target(1930, 1015, state).kind, "scroll")
          descriptions = [call for call in fonts.draw.call_args_list if call.args[0] == subtitle]
          self.assertEqual(len(descriptions), int(bool(subtitle)))
          if descriptions:
            self.assertLess(descriptions[0].args[4] + 33, expected_top)

  def drawing(self):
    stack = ExitStack()
    self.addCleanup(stack.close)
    for name in ("draw_rectangle_rec", "draw_rectangle_gradient_ex", "draw_rectangle_rounded", "draw_rectangle_rounded_lines_ex", "draw_line", "draw_line_ex",
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
    self.assertLessEqual(title.args[3] + fonts.measure(*title.args[:3]).width, 2110)
    label = next(call for call in fonts.draw.call_args_list if call.args[0].startswith("Long label"))
    self.assertLessEqual(fonts.measure(*label.args[:3]).width, 1149)
    subtitle = next(call for call in fonts.draw.call_args_list if call.args[0] == state.subtitle)
    self.assertLess(subtitle.args[4] + 33, feature_row_top(state))
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

  def test_header_uses_tile_border_and_stars_inside_clip_before_text(self):
    self.drawing()
    for expanded in (True, False):
      fonts = fake_fonts()

      def background(rect, accent):
        self.assertIs(accent, geometry.ACCENT)
        x, y, width, height = rl.begin_scissor_mode.call_args.args
        self.assertLessEqual(x, rect.x - 10)
        self.assertLessEqual(y, rect.y - 10)
        self.assertGreaterEqual(x + width, rect.x + rect.width + 10)
        self.assertGreaterEqual(y + height, rect.y + rect.height + 10)

      def constellation(nodes, edges, rect, accent, glow, fonts=fonts):
        self.assertEqual((nodes, edges), geometry.constellation("settings-header", rect))
        self.assertIs(rect, header.call_args.args[0])
        self.assertIs(accent, geometry.ACCENT)
        self.assertEqual(glow, 1.0)
        fonts.draw.assert_not_called()

      with patch.object(geometry, "draw_hud_background", side_effect=background) as header, \
           patch.object(geometry, "draw_constellation_nodes", side_effect=constellation) as stars:
        view.FeatureSettingsView(fonts).render(FeatureSettingsState(sidebar_expanded=expanded))
      header.assert_called_once()
      stars.assert_called_once()

  def test_header_omits_generic_roots_and_retains_nested_parents(self):
    self.drawing()
    for expanded in (True, False):
      for title, parent, back, expected in (
        ("Driving Model", "StarPilot", True, ["< Back", "Driving Model"]),
        ("Device", "Settings", True, ["< Back", "Device"]),
        ("Lane Centering", "Driving Controls", True, ["< Back", "Driving Controls > ", "Lane Centering"]),
        ("Aggressive", "Long Planner", True, ["< Back", "Long Planner > ", "Aggressive"]),
        ("StarPilot", "", False, ["StarPilot"]),
      ):
        with self.subTest(expanded=expanded, title=title):
          fonts = fake_fonts()
          rl.draw_line.reset_mock()
          geometry.draw_settings_header(fonts, expanded, title, parent, back=back)
          self.assertEqual([call.args[0] for call in fonts.draw.call_args_list], expected[1:] if expanded and back else expected)
          self.assertEqual(rl.draw_line.call_count, int(back and not expanded))

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
      self.assertTrue(all(call.args[2] in (35, 44, 50) for call in fonts.draw.call_args_list))
      header = [call for call in fonts.draw.call_args_list
                if call.args[0] == "< Back" or call.args[0].startswith("Driving Controls") or call.args[0] == "Lane Centering"]
      self.assertEqual(len(header), 2 if expanded else 3)
      self.assertEqual(header[0].args[3], left + 34 if expanded else left + 28)
      self.assertTrue(all(call.args[1:3] == (FontRole.MEDIUM, 44) for call in header))
      self.assertEqual(len({call.args[4] for call in header}), 1)
      self.assertNotEqual(FeatureInput.target(left + 60, 120, state).kind, "back")
      self.assertEqual(FeatureInput.target(left + 60, 76, state).kind, "details" if expanded else "back")
      self.assertEqual(FeatureInput.target(left + 207, 76, state).kind, "details" if expanded else "back")
      self.assertEqual(FeatureInput.target(left + 208, 76, state).kind, "details")
      actions = []
      owner = FeatureInput(actions.append)
      owner.press(left + 60, 76, state)
      owner.release(left + 60, 76, replace(state, sidebar_expanded=not expanded))
      self.assertFalse(actions)


if __name__ == "__main__":
  unittest.main()
