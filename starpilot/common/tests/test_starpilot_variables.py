from types import SimpleNamespace

from openpilot.starpilot.common import starpilot_variables as spv


def test_legacy_volt_stock_acc_models_share_sng_and_auto_hold_scope():
  assert spv.LEGACY_VOLT_STOCK_ACC_CARS == {
    "CHEVROLET_VOLT",
    "CHEVROLET_VOLT_2019",
    "CHEVROLET_VOLT_ASCM",
    "CHEVROLET_VOLT_CAMERA",
  }


def test_get_starpilot_toggles_uses_last_non_empty_broadcast(monkeypatch):
  params = SimpleNamespace(get_bool=lambda _key: False)
  monkeypatch.setattr(spv.get_starpilot_toggles, "_params", params, raising=False)
  monkeypatch.delattr(spv.get_starpilot_toggles, "_last_toggles_text", raising=False)

  payload = '{"always_on_lateral": true, "vision_speed_limit_detection": true}'
  sm_with_toggles = {"starpilotPlan": SimpleNamespace(starpilotToggles=payload)}
  sm_without_toggles = {"starpilotPlan": SimpleNamespace(starpilotToggles="")}

  first = spv.get_starpilot_toggles(sm_with_toggles)
  second = spv.get_starpilot_toggles(sm_without_toggles)

  assert first.always_on_lateral is True
  assert second.always_on_lateral is True
  assert second.vision_speed_limit_detection is True


class _FakeParams:
  def __init__(self, floats=None, ints=None, bools=None):
    self.floats = dict(floats or {})
    self.ints = dict(ints or {})
    self.bools = dict(bools or {})

  def get_float(self, key):
    return float(self.floats.get(key, 0.0))

  def get_int(self, key):
    return int(self.ints.get(key, 0))

  def get_bool(self, key):
    return bool(self.bools.get(key, False))

  def put_float(self, key, value):
    self.floats[key] = float(value)

  def put_int(self, key, value):
    self.ints[key] = int(value)

  def put_bool(self, key, value):
    self.bools[key] = bool(value)

  def remove(self, key):
    self.floats.pop(key, None)
    self.ints.pop(key, None)
    self.bools.pop(key, None)


def test_sync_stock_param_does_not_stomp_existing_custom_value_when_stock_missing():
  params = _FakeParams({"SteerDelay": 0.35, "SteerDelayStock": 0.0})
  variables = object.__new__(spv.StarPilotVariables)
  variables.params = params

  variables._sync_stock_param("SteerDelay", "SteerDelayStock", 0.10)

  assert params.get_float("SteerDelay") == 0.35
  assert params.get_float("SteerDelayStock") == 0.10


def test_cancel_button_migration_copies_distance_actions_once():
  params = _FakeParams(
    ints={
      "DistanceButtonControl": 8,
      "LongDistanceButtonControl": 4,
      "VeryLongDistanceButtonControl": 7,
    },
    bools={"RemapCancelToDistance": True},
  )

  assert spv.migrate_cancel_button_controls(params) is True
  assert params.get_int("CancelButtonControl") == 8
  assert params.get_int("LongCancelButtonControl") == 4
  assert params.get_int("VeryLongCancelButtonControl") == 7
  assert params.get_bool(spv.CANCEL_BUTTON_MIGRATION_KEY) is True

  params.put_int("DistanceButtonControl", 1)
  params.put_int("CancelButtonControl", 3)

  assert spv.migrate_cancel_button_controls(params) is False
  assert params.get_int("CancelButtonControl") == 3


def test_button_function_ignores_tuning_level_gate():
  params = _FakeParams(ints={"LKASButtonControl": spv.BUTTON_FUNCTIONS["AOL_TOGGLE"]})
  variables = object.__new__(spv.StarPilotVariables)
  variables.params = params
  variables.starpilot_toggles = SimpleNamespace(tuning_level=spv.TUNING_LEVELS["STANDARD"])
  variables.tuning_levels = {"LKASButtonControl": spv.TUNING_LEVELS["ADVANCED"]}
  variables.default_values = {"LKASButtonControl": str(spv.BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"])}

  assert variables.get_value("LKASButtonControl", cast=int) == spv.BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"]
  assert variables.get_button_function("LKASButtonControl") == spv.BUTTON_FUNCTIONS["AOL_TOGGLE"]


def test_favorite_button_flags_map_to_three_slots():
  toggle = SimpleNamespace()

  spv.StarPilotVariables.set_favorite_button_flags(toggle, "lkas", spv.BUTTON_FUNCTIONS["FAVORITE_2"])

  assert toggle.favorite_1_via_lkas is False
  assert toggle.favorite_2_via_lkas is True
  assert toggle.favorite_3_via_lkas is False


def test_set_speed_limit_available_on_openpilot_longitudinal():
  assert spv.set_speed_limit_available(openpilot_longitudinal=True, has_cc_long=False, pcm_cruise_speed=True) is True


def test_set_speed_limit_available_on_gm_helper_path():
  assert spv.set_speed_limit_available(openpilot_longitudinal=False, has_cc_long=True, pcm_cruise_speed=True) is True


def test_set_speed_limit_available_on_redneck_helper_path():
  assert spv.set_speed_limit_available(openpilot_longitudinal=False, has_cc_long=False, pcm_cruise_speed=False) is True


def test_set_speed_limit_unavailable_on_stock_pcm_without_helper():
  assert spv.set_speed_limit_available(openpilot_longitudinal=False, has_cc_long=False, pcm_cruise_speed=True) is False
