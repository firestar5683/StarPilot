"""Static entry interactions; no claim of full scroller or device event parity."""

from dataclasses import FrozenInstanceError, replace
import unittest

from openpilot.starpilot.ui.device_state import DeviceInput, DeviceRequest, button_rect
from openpilot.starpilot.ui.home_state import HomeAction, HomeActionKind, HomeInput
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.preview_home import reference_state
from openpilot.starpilot.ui.preview_settings import SettingsPreviewInput
from openpilot.starpilot.ui.settings_state import (
  Destination, PreviewRouter, SettingsAction, SettingsActionKind, SettingsInput, SettingsState, TILES, tile_rects,
)
from openpilot.starpilot.ui.software_state import SoftwareRequest


class TestSettingsActions(unittest.TestCase):
  def test_large_device_navigation_and_inert_requests(self):
    router = PreviewRouter(Profile.LARGE)
    router.home_action(HomeAction(HomeActionKind.OPEN_SETTINGS))
    settings_input = SettingsInput(Profile.LARGE, router.settings_action, lambda: router.selected)
    device_input = DeviceInput(router.device_action)
    self.assertTrue(router.settings.destination(Destination.DEVICE).available)
    self.assertFalse(router.settings.destination(Destination.NETWORK).available)
    settings_input.press(200, 465, router.settings)
    settings_input.release(200, 465, router.settings)
    self.assertEqual(router.selected, Destination.DEVICE)
    self.assertEqual(router.requests, [])
    # Root tiles overlap the Device pane; they must not dispatch from Device.
    settings_input.press(800, 300, router.settings)
    settings_input.release(800, 300, router.settings)
    self.assertEqual(router.requests, [])
    x, y, width, height = button_rect(DeviceRequest.PREVIEW_DRIVER_CAMERA)
    point = (x + width / 2, y + height / 2)
    device_input.press(*point, router.device)
    device_input.release(*point, router.device)
    self.assertEqual([action.request for action in router.device_requests], [DeviceRequest.PREVIEW_DRIVER_CAMERA])
    self.assertIn("No device operation", router.notice)
    settings_input.press(200, 355, router.settings)
    settings_input.release(200, 355, router.settings)
    self.assertEqual(router.selected, Destination.STAR)
    settings_input.press(250, 160, router.settings)
    settings_input.release(250, 160, router.settings)
    self.assertFalse(router.in_settings)

  def test_back_from_device_and_cancelled_press_across_panel_change(self):
    router = PreviewRouter(Profile.LARGE)
    router.home_action(HomeAction(HomeActionKind.OPEN_SETTINGS))
    settings_input = SettingsInput(Profile.LARGE, router.settings_action, lambda: router.selected)
    device_input = DeviceInput(router.device_action)

    def route(action):
      settings_input.cancel()
      device_input.cancel()
      router.settings_action(action)

    route(SettingsAction(SettingsActionKind.REQUEST_DESTINATION, router.settings.destination(Destination.DEVICE)))
    self.assertEqual(router.selected, Destination.DEVICE)
    x, y, width, height = button_rect(DeviceRequest.RESET_CALIBRATION)
    point = (x + width / 2, y + min(height / 2, 1030 - y - 1))
    device_input.press(*point, router.device)
    route(SettingsAction(SettingsActionKind.CLOSE))
    device_input.release(*point, router.device)
    self.assertEqual(router.selected, Destination.STAR)
    self.assertEqual(router.device_requests, [])
    settings_input.press(750, 300, router.settings)
    route(SettingsAction(SettingsActionKind.CLOSE))
    settings_input.release(750, 300, router.settings)
    self.assertFalse(router.in_settings)
    self.assertEqual(router.requests, [])

  def test_compact_device_remains_unavailable(self):
    router = PreviewRouter(Profile.COMPACT)
    router.home_action(HomeAction(HomeActionKind.OPEN_SETTINGS))
    router.settings_action(SettingsAction(SettingsActionKind.REQUEST_DESTINATION, router.settings.destination(Destination.DEVICE)))
    self.assertEqual(router.selected, Destination.STAR)
    self.assertFalse(router.settings.destination(Destination.DEVICE).available)
    self.assertEqual(len(router.requests), 1)

  def test_large_software_actual_preview_dispatch_and_single_back(self):
    router = PreviewRouter(Profile.LARGE)
    inputs = SettingsPreviewInput(Profile.LARGE, router)
    self.assertTrue(router.settings.destination(Destination.SOFTWARE).available)
    inputs.step(100, 100, 1.0, pressed=True)
    inputs.step(100, 100, 1.1, released=True)
    self.assertTrue(router.in_settings)
    inputs.step(200, 905, 1.2, pressed=True)
    inputs.step(200, 905, 1.3, released=True)
    self.assertEqual(router.selected, Destination.SOFTWARE)
    initial = router.software
    for point, expected in (((1980, 475), SoftwareRequest.CHECK_FOR_UPDATES),
                            ((2030, 306), SoftwareRequest.SET_AUTOMATIC_UPDATES),
                            ((1980, 819), SoftwareRequest.OPEN_UNINSTALL_CONFIRMATION)):
      inputs.step(*point, 1.4, pressed=True)
      inputs.step(*point, 1.5, released=True)
      self.assertEqual(router.software_requests[-1].request, expected)
      self.assertEqual(router.software, initial)
    self.assertEqual(router.software_requests[1].desired_enabled, False)
    self.assertIn("No update", router.notice)
    inputs.step(0, 0, 1.6, back_pressed=True, footer_pressed=True)
    self.assertEqual(router.selected, Destination.STAR)
    self.assertTrue(router.in_settings)
    inputs.step(0, 0, 1.7, back_pressed=True)
    self.assertFalse(router.in_settings)
    self.assertEqual(len(router.software_requests), 3)

  def test_leaf_change_cancels_pending_press_and_release_stays_with_origin(self):
    router = PreviewRouter(Profile.LARGE)
    inputs = SettingsPreviewInput(Profile.LARGE, router)
    router.home_action(HomeAction(HomeActionKind.OPEN_SETTINGS))
    inputs.step(200, 905, 1.0, pressed=True)
    inputs.step(200, 905, 1.1, released=True)
    self.assertEqual(router.selected, Destination.SOFTWARE)
    inputs.step(1980, 475, 1.2, pressed=True)
    inputs.step(200, 465, 1.3, pressed=True, released=True)
    self.assertEqual(router.selected, Destination.DEVICE)
    self.assertEqual(router.software_requests, [])
    self.assertEqual(router.device_requests, [])
    inputs.step(1980, 650, 1.4, pressed=True)
    inputs.step(200, 905, 1.5, pressed=True, released=True)
    self.assertEqual(router.selected, Destination.SOFTWARE)
    self.assertEqual(router.device_requests, [])
    inputs.step(1980, 475, 1.6, pressed=True)
    inputs.step(0, 0, 1.7, back_pressed=True)
    inputs.step(1980, 475, 1.8, released=True)
    self.assertEqual(router.selected, Destination.STAR)
    self.assertEqual(router.software_requests, [])

  def test_compact_software_remains_unavailable(self):
    router = PreviewRouter(Profile.COMPACT)
    router.home_action(HomeAction(HomeActionKind.OPEN_SETTINGS))
    router.settings_action(SettingsAction(SettingsActionKind.REQUEST_DESTINATION, router.settings.destination(Destination.SOFTWARE)))
    self.assertEqual(router.selected, Destination.STAR)
    self.assertFalse(router.settings.destination(Destination.SOFTWARE).available)
    self.assertEqual(len(router.requests), 1)

  def test_actual_home_input_routes_to_settings_and_back_for_both_profiles(self):
    for profile, point in ((Profile.LARGE, (100, 100)), (Profile.COMPACT, (20, 210))):
      with self.subTest(profile=profile):
        router = PreviewRouter()
        handler = HomeInput(profile, router.home_action)
        handler.press(*point, 1)
        handler.release(*point, 1.1, reference_state())
        self.assertTrue(router.in_settings)
        router.settings_action(SettingsAction(SettingsActionKind.CLOSE))
        self.assertFalse(router.in_settings)
        self.assertEqual(router.requests, [])

  def test_each_root_tile_emits_its_explicit_unavailable_destination_once(self):
    for (destination, _, _), (x, y, width, height) in zip(TILES, tile_rects(SettingsState()), strict=True):
      with self.subTest(destination=destination):
        router = PreviewRouter()
        router.home_action(HomeAction(HomeActionKind.OPEN_SETTINGS))
        handler = SettingsInput(Profile.LARGE, router.settings_action)
        handler.press(x + width / 2, y + height / 2, router.settings)
        handler.release(x + width / 2, y + height / 2, router.settings)
        handler.release(x + width / 2, y + height / 2, router.settings)
        self.assertEqual(len(router.requests), 1)
        self.assertEqual(router.requests[0].destination, router.settings.destination(destination))
        self.assertFalse(router.requests[0].destination.available)
        self.assertIn("not implemented", router.notice)
        self.assertTrue(router.in_settings)

  def test_sidebar_collapse_reflow_restore_and_close(self):
    router = PreviewRouter()
    router.in_settings = True
    handler = SettingsInput(Profile.LARGE, router.settings_action)
    for expanded in (False, True):
      handler.press(20, 581, router.settings)
      handler.release(20, 581, router.settings)
      self.assertEqual(router.settings.sidebar_expanded, expanded)
      self.assertEqual(tile_rects(router.settings)[0][0], 520 if expanded else 20)
    handler.press(570, 50, router.settings)
    handler.release(570, 50, router.settings)
    self.assertTrue(router.in_settings)
    handler.press(250, 160, router.settings)
    handler.release(250, 160, router.settings)
    self.assertFalse(router.in_settings)
    router.in_settings = True
    router.settings = replace(router.settings, sidebar_expanded=False)
    handler.press(70, 50, router.settings)
    handler.release(70, 50, replace(router.settings, sidebar_expanded=True))
    self.assertTrue(router.in_settings)
    handler.press(70, 50, router.settings)
    handler.release(70, 50, router.settings)
    self.assertFalse(router.in_settings)

  def test_compact_only_visible_static_cards_are_targets(self):
    requests = []
    state = SettingsState()
    handler = SettingsInput(Profile.COMPACT, requests.append)
    for point, destination in (((200, 100), Destination.TOGGLES), ((500, 100), Destination.NETWORK)):
      handler.press(*point, state)
      handler.release(*point, state)
      self.assertEqual(requests[-1].destination, state.destination(destination))
    handler.press(200, 225, state)
    handler.release(200, 225, state)
    self.assertEqual(len(requests), 2)

  def test_drag_outside_and_cancel_do_not_dispatch_or_fake_scrolling(self):
    for profile, point in ((Profile.LARGE, (750, 300)), (Profile.COMPACT, (200, 100))):
      with self.subTest(profile=profile):
        requests = []
        state = SettingsState()
        handler = SettingsInput(profile, requests.append)
        handler.press(*point, state)
        handler.move(-1 if profile == Profile.LARGE else point[0] + 50, point[1], state)
        handler.release(*point, state)
        handler.press(*point, state)
        handler.release(-1, -1, state)
        handler.press(*point, state)
        handler.cancel()
        handler.release(*point, state)
        self.assertEqual(requests, [])
        self.assertEqual(state, SettingsState())

  def test_current_availability_is_returned_at_release(self):
    actions = []
    state = SettingsState()
    handler = SettingsInput(Profile.COMPACT, actions.append)
    handler.press(200, 100, state)
    changed = replace(state, availability=tuple(replace(item, reason="Host adapter not connected") for item in state.availability))
    handler.release(200, 100, changed)
    self.assertEqual(actions[0].destination.reason, "Host adapter not connected")
    self.assertFalse(actions[0].destination.available)

  def test_state_and_availability_are_immutable(self):
    state = SettingsState()
    for target, attribute, value in ((state, "sidebar_expanded", False), (state.availability[0], "available", True)):
      with self.assertRaises(FrozenInstanceError):
        setattr(target, attribute, value)


if __name__ == "__main__":
  unittest.main()
