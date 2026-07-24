from openpilot.starpilot.common.experimental_state import (
  LONGITUDINAL_PREFERENCE_OVERRIDE_PARAM,
  requested_experimental_mode,
  toggle_longitudinal_model_preference,
)


class FakeParams:
  def __init__(self, bools=None, ints=None):
    self.bools = dict(bools or {})
    self.ints = dict(ints or {})

  def get_bool(self, key):
    return bool(self.bools.get(key, False))

  def get_int(self, key, default=0):
    return int(self.ints.get(key, default))

  def put_int(self, key, value):
    self.ints[key] = int(value)


def test_set_speed_first_is_default():
  assert not requested_experimental_mode(FakeParams(), FakeParams())


def test_persistent_model_first_preference_is_respected():
  params = FakeParams(ints={"LongitudinalModelPreference": 1})
  assert requested_experimental_mode(params, FakeParams())


def test_drive_override_takes_priority_without_changing_persistent_default():
  params = FakeParams(ints={"LongitudinalModelPreference": 0})
  params_memory = FakeParams(ints={LONGITUDINAL_PREFERENCE_OVERRIDE_PARAM: 1})

  assert requested_experimental_mode(params, params_memory)
  assert params.get_int("LongitudinalModelPreference") == 0


def test_exp_button_flips_preference_for_current_drive():
  params = FakeParams(ints={"LongitudinalModelPreference": 0})
  params_memory = FakeParams()

  assert toggle_longitudinal_model_preference(params, params_memory)
  assert params_memory.get_int(LONGITUDINAL_PREFERENCE_OVERRIDE_PARAM) == 1
  assert not toggle_longitudinal_model_preference(params, params_memory)
  assert params_memory.get_int(LONGITUDINAL_PREFERENCE_OVERRIDE_PARAM) == 0


def test_safe_mode_forces_set_speed_first():
  params = FakeParams(bools={"SafeMode": True}, ints={"LongitudinalModelPreference": 1})
  params_memory = FakeParams(ints={LONGITUDINAL_PREFERENCE_OVERRIDE_PARAM: 1})
  assert not requested_experimental_mode(params, params_memory)
