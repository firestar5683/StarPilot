"""Request boundaries for the captured large Device viewport."""

from dataclasses import FrozenInstanceError, replace
import unittest

from openpilot.starpilot.ui.device_state import DeviceInput, DeviceRequest, DeviceState, button_rect
from openpilot.starpilot.galaxy.access import AccessStatus


class TestDeviceActions(unittest.TestCase):
  def test_galaxy_press_cancels_when_local_state_changes(self):
    actions = []
    handler = DeviceInput(actions.append)
    x, y, width, height = button_rect(DeviceRequest.OPEN_GALAXY)
    point = (x + width / 2, y + height / 2)
    before = DeviceState(galaxy_status=AccessStatus.UNCONFIGURED)
    handler.press(*point, before)
    handler.release(*point, replace(before, galaxy_status=AccessStatus.CONFIGURED_LOCAL))
    self.assertEqual(actions, [])

  def test_each_visible_button_emits_one_typed_request(self):
    actions = []
    handler = DeviceInput(actions.append)
    state = DeviceState()
    for request in DeviceRequest:
      x, y, width, height = button_rect(request)
      point = x + width / 2, y + min(height / 2, 1030 - y - 1)
      handler.press(*point, state)
      handler.release(*point, state)
      handler.release(*point, state)
      self.assertEqual(actions[-1].request, request)
    self.assertEqual(len(actions), len(DeviceRequest))

  def test_disabled_and_cancelled_controls_do_not_emit(self):
    actions = []
    handler = DeviceInput(actions.append)
    camera = (1980, 650)
    handler.press(*camera, replace(DeviceState(), offroad=False))
    handler.release(*camera, replace(DeviceState(), offroad=False))
    handler.press(*camera, DeviceState())
    handler.move(1800, 650, DeviceState())
    handler.release(*camera, DeviceState())
    handler.press(*camera, DeviceState())
    handler.release(*camera, replace(DeviceState(), offroad=False))
    self.assertEqual(actions, [])

  def test_values_are_supplied_and_state_is_immutable(self):
    state = replace(DeviceState(), dongle_id="fixture", serial="fixture")
    self.assertEqual((state.dongle_id, state.serial), ("fixture", "fixture"))
    with self.assertRaises(FrozenInstanceError):
      state.serial = "changed"  # ty: ignore[invalid-assignment]

  def test_pair_and_manage_both_request_the_galaxy_entry(self):
    actions = []
    handler = DeviceInput(actions.append)
    for paired in (False, True):
      state = replace(DeviceState(), galaxy_paired=paired)
      handler.press(1980, 475, state)
      handler.release(1980, 475, state)
    self.assertEqual([action.request for action in actions], [DeviceRequest.OPEN_GALAXY] * 2)


if __name__ == "__main__":
  unittest.main()
