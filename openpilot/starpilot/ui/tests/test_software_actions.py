"""Software panel emits requests and waits for caller-supplied state."""

from dataclasses import FrozenInstanceError, replace
import unittest

from openpilot.starpilot.ui.software_state import (
  BUTTON_ROWS, TOGGLE_RECT, DownloadLabel, SoftwareInput, SoftwareRequest, SoftwareState, button_rect,
)


class TestSoftwareActions(unittest.TestCase):
  def test_captured_controls_emit_one_request_each(self):
    actions = []
    handler = SoftwareInput(actions.append)
    state = SoftwareState()
    tx, ty, tw, th = TOGGLE_RECT
    handler.press(tx + tw / 2, ty + th / 2, state)
    handler.release(tx + tw / 2, ty + th / 2, state)
    self.assertEqual(actions[-1].request, SoftwareRequest.SET_AUTOMATIC_UPDATES)
    self.assertFalse(actions[-1].desired_enabled)
    for request, row in BUTTON_ROWS:
      x, y, width, height = button_rect(row)
      point = x + width / 2, y + min(height / 2, 1030 - y - 1)
      handler.press(*point, state)
      handler.release(*point, state)
      handler.release(*point, state)
      self.assertEqual(actions[-1].request, request)
    self.assertEqual(len(actions), 5)
    self.assertTrue(state.automatic_updates)

  def test_check_and_download_are_distinct_displayed_intents(self):
    actions = []
    handler = SoftwareInput(actions.append)
    point = 1980, 475
    check = SoftwareState()
    download = replace(check, download_label=DownloadLabel.DOWNLOAD)
    handler.press(*point, check)
    handler.release(*point, check)
    handler.press(*point, download)
    handler.release(*point, download)
    self.assertEqual([action.request for action in actions],
                     [SoftwareRequest.CHECK_FOR_UPDATES, SoftwareRequest.DOWNLOAD_UPDATE])

  def test_drag_state_change_and_viewport_clip_cancel(self):
    actions = []
    handler = SoftwareInput(actions.append)
    state = SoftwareState()
    handler.press(1980, 475, state)
    handler.move(1990, 475, state)
    handler.release(1980, 475, state)
    handler.press(1980, 475, state)
    handler.release(1980, 475, replace(state, download_label=DownloadLabel.DOWNLOAD))
    handler.press(1980, 991, state)
    handler.release(1980, 1031, state)
    self.assertEqual(actions, [])

  def test_supplied_state_is_immutable_and_acknowledged_externally(self):
    state = SoftwareState()
    with self.assertRaises(FrozenInstanceError):
      state.target_branch = "changed"  # ty: ignore[invalid-assignment]
    actions = []
    handler = SoftwareInput(actions.append)
    handler.press(2030, 306, state)
    handler.release(2030, 306, state)
    self.assertTrue(state.automatic_updates)
    self.assertFalse(actions[0].desired_enabled)
    acknowledged = replace(state, automatic_updates=actions[0].desired_enabled)
    self.assertFalse(acknowledged.automatic_updates)

  def test_external_toggle_change_during_press_cancels_stale_intent(self):
    actions = []
    handler = SoftwareInput(actions.append)
    point = 2030, 306
    shown = SoftwareState(automatic_updates=True)
    changed = replace(shown, automatic_updates=False)
    handler.press(*point, shown)
    handler.release(*point, changed)
    self.assertEqual(actions, [])
    handler.press(*point, changed)
    handler.release(*point, changed)
    self.assertEqual(len(actions), 1)
    self.assertTrue(actions[0].desired_enabled)


if __name__ == "__main__":
  unittest.main()
