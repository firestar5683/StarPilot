"""Offline shell requests and supplied-observation semantics."""

import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch
from pathlib import Path

from openpilot.starpilot.ui.onroad_state import ObservationKind, speed_limit_from_message
from openpilot.starpilot.ui.onroad_state import OnroadState, SpeedLimitObservation
from openpilot.starpilot.ui.device_state import DeviceRequest
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.preview_home import reference_state
from openpilot.starpilot.ui.settings_state import Destination, SettingsState
from openpilot.starpilot.ui.shell import ShellInput, ShellMode, ShellSnapshot, ShellView
from openpilot.starpilot.ui.toggles_state import Personality, ToggleKey, TogglesInput, TogglesState


class ShellActionTests(unittest.TestCase):
  def test_toggle_request_needs_same_displayed_value_on_release(self) -> None:
    requests = []
    touch = TogglesInput(requests.append)
    state = TogglesState()
    touch.press(2000, 120, state)
    touch.release(2000, 120, replace(state, enabled=False))
    self.assertEqual(requests, [])
    touch.press(2000, 120, state)
    touch.release(2000, 120, state)
    self.assertEqual(len(requests), 1)
    self.assertEqual(requests[0].key, ToggleKey.ENABLED)
    self.assertIs(requests[0].value, False)
    self.assertIs(state.enabled, True)

  def test_personality_request_is_inert(self) -> None:
    requests = []
    touch = TogglesInput(requests.append)
    state = TogglesState()
    touch.press(1350, 800, state)
    touch.release(1350, 800, state)
    self.assertEqual(requests[0].personality, Personality.AGGRESSIVE)
    self.assertEqual(state.personality, Personality.STANDARD)

  def test_below_fold_toggle_uses_supplied_scroll_and_value(self) -> None:
    requests = []
    touch = TogglesInput(requests.append)
    state = TogglesState(scroll_y=855)
    touch.press(2000, 240, state)
    touch.release(2000, 240, state)
    self.assertEqual(requests[-1].key, ToggleKey.ALWAYS_ON_DM)
    self.assertIs(requests[-1].value, True)
    self.assertIs(state.always_on_dm, False)

  def test_slc_numeric_defaults_are_not_observations(self) -> None:
    base = {"observationKind": "unknown", "source": "none", "speedLimit": 0.0, "offset": 0.0,
            "pendingSpeedLimit": 0.0, "effectiveCap": 0.0, "acceptedSpeedLimit": 0.0,
            "hasPending": False, "hasCeiling": False, "hasAccepted": False,
            "sessionId": "7", "decisionId": 8, "presentationId": 9, "status": "unavailable"}
    unknown = speed_limit_from_message(SimpleNamespace(**base))
    self.assertEqual(unknown.kind, ObservationKind.UNKNOWN)
    self.assertIsNone(unknown.speed_limit_mps)
    self.assertIsNone(unknown.pending_speed_limit_mps)
    valid = speed_limit_from_message(SimpleNamespace(**(base | {"observationKind": "valid", "source": "map",
                                                         "speedLimit": 13.4, "hasPending": True,
                                                         "pendingSpeedLimit": 14.1})))
    self.assertEqual(valid.speed_limit_mps, 13.4)
    self.assertEqual(valid.pending_speed_limit_mps, 14.1)
    self.assertIsNone(valid.effective_cap_mps)

  def test_malformed_native_slc_values_never_render_as_a_limit(self) -> None:
    base = {"observationKind": "valid", "source": "map", "speedLimit": float("nan"), "offset": 0.0,
            "pendingSpeedLimit": 0.0, "effectiveCap": 0.0, "acceptedSpeedLimit": 0.0,
            "hasPending": False, "hasCeiling": False, "hasAccepted": False,
            "sessionId": "abc123", "decisionId": 8, "presentationId": 9, "status": "live"}
    for speed in (float("nan"), float("inf"), 0.0, -1.0):
      observation = speed_limit_from_message(SimpleNamespace(**(base | {"speedLimit": speed})))
      self.assertEqual(observation.kind, ObservationKind.UNKNOWN)
      self.assertIsNone(observation.speed_limit_mps)
    stale = speed_limit_from_message(SimpleNamespace(**(base | {"observationKind": "stale"})))
    self.assertEqual(stale.kind, ObservationKind.STALE)
    self.assertIsNone(stale.speed_limit_mps)
    valid = speed_limit_from_message(SimpleNamespace(**(base | {"speedLimit": 13.4})))
    self.assertEqual(valid.session_id, "abc123")
    with self.assertRaises(ValueError):
      OnroadState(False, False, float("nan"), None, SpeedLimitObservation())

  def test_shell_navigation_cancels_press_across_panes(self) -> None:
    requests = []
    touch = ShellInput(Profile.LARGE, requests.append)
    snapshot = ShellSnapshot(ShellMode.HOME, reference_state(), SettingsState(),
                             OnroadState(False, False, 0.0, None, SpeedLimitObservation()))
    touch.press(100, 100, 0.0, snapshot)
    touch.release(100, 100, 0.1, snapshot)
    self.assertEqual(requests[-1].source, "home")
    settings = replace(snapshot, mode=ShellMode.SETTINGS)
    touch.press(200, 450, 0.2, settings)
    touch.release(200, 450, 0.3, settings)
    self.assertEqual(requests[-1].source, "settings")
    self.assertEqual(requests[-1].action.destination.destination, Destination.DEVICE)
    device = replace(settings, selected=Destination.DEVICE)
    touch.press(1900, 600, 0.4, device)
    touch.release(1900, 600, 0.5, replace(device, mode=ShellMode.ONROAD))
    self.assertEqual(len([request for request in requests if request.source == "device"]), 0)
    touch.press(1900, 600, 0.6, device)
    touch.release(1900, 600, 0.7, device)
    self.assertEqual(requests[-1].source, "device")
    self.assertEqual(requests[-1].action.request, DeviceRequest.PREVIEW_DRIVER_CAMERA)

  def test_onroad_wheel_request_requires_unchanged_supplied_state(self) -> None:
    requests = []
    touch = ShellInput(Profile.LARGE, requests.append)
    snapshot = ShellSnapshot(ShellMode.ONROAD, reference_state(), SettingsState(),
                             OnroadState(True, False, 0.0, None, SpeedLimitObservation(),
                                         experimental_available=True, experimental_enabled=False))
    touch.press(1670, 170, 0.0, snapshot)
    touch.release(1670, 170, 0.1, replace(snapshot, onroad=replace(snapshot.onroad, experimental_enabled=True)))
    self.assertEqual(requests, [])
    touch.press(1670, 170, 0.2, snapshot)
    touch.release(1670, 170, 0.3, snapshot)
    self.assertEqual(requests[-1].source, "onroad")
    self.assertIs(requests[-1].action.value, True)

  def test_compact_never_dispatches_large_leaf_controls(self) -> None:
    requests = []
    touch = ShellInput(Profile.COMPACT, requests.append)
    snapshot = ShellSnapshot(ShellMode.SETTINGS, reference_state(), SettingsState(),
                             OnroadState(False, False, 0.0, None, SpeedLimitObservation()),
                             selected=Destination.TOGGLES)
    with (patch.object(touch.toggles, 'press') as toggles,
          patch.object(touch.device, 'press') as device,
          patch.object(touch.software, 'press') as software):
      for destination in (Destination.TOGGLES, Destination.DEVICE, Destination.SOFTWARE):
        injected = replace(snapshot, selected=destination)
        touch.press(510, 100, 0.0, injected)
        touch.release(510, 100, 0.1, injected)
      for control in (toggles, device, software):
        control.assert_not_called()
    self.assertFalse(any(request.source in {"toggles", "device", "software"} for request in requests))

  def test_compact_wheel_icon_is_not_a_large_button(self) -> None:
    requests = []
    touch = ShellInput(Profile.COMPACT, requests.append)
    snapshot = ShellSnapshot(ShellMode.ONROAD, reference_state(), SettingsState(),
                             OnroadState(True, False, 0.0, None, SpeedLimitObservation(),
                                         experimental_available=True))
    for x, y in ((46, 200), (1670, 170)):
      touch.press(x, y, 0.0, snapshot)
      touch.release(x, y, 0.1, snapshot)
    self.assertEqual(requests, [])

  def test_failed_shell_construction_closes_acquired_views(self) -> None:
    with (patch("openpilot.starpilot.ui.shell.HomeView") as home,
          patch("openpilot.starpilot.ui.shell.SettingsView") as settings,
          patch("openpilot.starpilot.ui.shell.OnroadView") as onroad,
          patch("openpilot.starpilot.ui.shell.DeviceView"),
          patch("openpilot.starpilot.ui.shell.SoftwareView"),
          patch("openpilot.starpilot.ui.shell.TogglesView") as toggles):
      settings.return_value.prepare.side_effect = RuntimeError("asset validation failed")
      with self.assertRaisesRegex(RuntimeError, "asset validation failed"):
        ShellView(Mock(profile=Profile.LARGE), Path("/unused"))
      home.return_value.close.assert_called_once()
      settings.return_value.close.assert_called_once()
      onroad.return_value.close.assert_called_once()
      toggles.return_value.close.assert_called_once()


if __name__ == "__main__":
  unittest.main()
