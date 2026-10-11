"""Pressed feedback uses the same guarded targets as settings actions."""

from dataclasses import replace
import unittest

from openpilot.starpilot.ui.feature_settings_state import FeatureInput, FeatureRow, FeatureSettingsState, FeatureUiAction


class FeaturePressedTests(unittest.TestCase):
  def setUp(self):
    self.row = FeatureRow("wifi:test", "Network", "Available", available=True, actions=(("CONNECT", True), ("Forget", True)))
    self.state = FeatureSettingsState(page="Network", rows=(self.row,))
    self.actions = []
    self.input = FeatureInput(self.actions.append)

  def test_feedback_identifies_only_the_held_button_and_activates_on_release(self):
    for index, x in enumerate((1500, 1930)):
      with self.subTest(index=index):
        expected = FeatureUiAction("action", self.row, index)
        self.input.press(x, 189, self.state)
        self.assertEqual(self.input.pressed_action(self.state), expected)
        self.assertEqual(self.input.pressed_action(self.state), expected)
        self.assertFalse(self.actions)
        self.input.release(x, 189, self.state)
        self.assertEqual(self.actions.pop(), expected)
        self.assertIsNone(self.input.held)
        self.assertEqual(self.input.pressed_action(self.state), expected)
        self.assertIsNone(self.input.pressed_action(self.state))

  def test_feedback_revalidates_current_state_and_canceled_taps_stay_canceled(self):
    for changed in (replace(self.state, page="Other"), replace(self.state, scroll=5), replace(self.state, sidebar_expanded=False),
                    replace(self.state, rows=()), replace(self.state, rows=(replace(self.row, value="Connected"),)),
                    replace(self.state, rows=(replace(self.row, available=False),)),
                    replace(self.state, rows=(replace(self.row, actions=(("CONNECT", False), ("Forget", True))),))):
      with self.subTest(changed=changed):
        self.input.press(1500, 189, self.state)
        self.assertIsNone(self.input.pressed_action(changed))
        self.input.move(1500, 189, changed)
        self.assertIsNone(self.input.pressed_action(self.state))
        self.input.release(1500, 189, changed)
        self.assertIsNone(self.input.pressed_action(changed))
        self.assertFalse(self.actions)
    for cancel in (lambda: self.input.move(1550, 189, self.state), lambda: self.input.move(1500, 100, self.state),
                   self.input.cancel_tap, self.input.cancel):
      self.input.press(1500, 189, self.state)
      cancel()
      self.assertIsNone(self.input.pressed_action(self.state))
      self.input.release(1500, 189, self.state)
      self.assertFalse(self.actions)

  def test_batched_tap_has_one_feedback_frame_and_lifecycle_cancellation_clears_it(self):
    self.input.press(1500, 189, self.state)
    self.input.release(1500, 189, self.state)
    self.assertEqual(self.input.pressed_action(self.state), FeatureUiAction("action", self.row, 0))
    self.assertIsNone(self.input.pressed_action(self.state))
    self.input.press(1500, 189, self.state)
    self.input.release(1500, 189, self.state)
    self.input.cancel()
    self.assertIsNone(self.input.pressed_action(self.state))
    self.input.emit = lambda _action: self.input.cancel()
    self.input.press(1500, 189, self.state)
    self.input.release(1500, 189, self.state)
    self.assertIsNone(self.input.pressed_action(self.state))
