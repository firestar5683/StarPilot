from openpilot.selfdrive.ui.layouts.settings.starpilot.vehicle import VehicleSettingsManagerView
from openpilot.selfdrive.ui.lib import starpilot_state as state_module
from openpilot.selfdrive.ui.lib.starpilot_state import StarPilotCarState, starpilot_state


EV9_CONTROL_KEYS = {
  "EV9LongPreinitPanda",
}


class FakeParams:
  def get_bool(self, _key):
    return False


class FakeController:
  def __init__(self):
    self._params = FakeParams()

  def _on_toggle(self, _key):
    pass

  def _on_panda_firmware_toggle(self, _key, _message):
    pass


def test_ev9_capability_requires_exact_fingerprint():
  assert state_module.is_ev9_fingerprint("KIA_EV9")
  assert not state_module.is_ev9_fingerprint("KIA_EV6")
  assert not state_module.is_ev9_fingerprint("KIA_EV9_GT_LINE")
  assert not state_module.is_ev9_fingerprint("")


def test_on_device_ev9_controls_are_scoped_to_ev9():
  view = object.__new__(VehicleSettingsManagerView)
  view._controller = FakeController()
  original_state = starpilot_state.car_state
  try:
    non_ev9 = StarPilotCarState()
    non_ev9.isEV9 = False
    starpilot_state.car_state = non_ev9
    assert EV9_CONTROL_KEYS.isdisjoint({toggle.get("key") for toggle in view._build_driving_toggles()})

    ev9 = StarPilotCarState()
    ev9.isEV9 = True
    ev9.isHKGCanFd = True
    ev9.hasOpenpilotLongitudinal = True
    starpilot_state.car_state = ev9
    assert EV9_CONTROL_KEYS <= {toggle.get("key") for toggle in view._build_driving_toggles()}
  finally:
    starpilot_state.car_state = original_state
