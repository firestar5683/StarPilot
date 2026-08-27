from types import SimpleNamespace

from openpilot.starpilot.common import starpilot_variables as spv


def test_legacy_volt_stock_acc_models_share_sng_and_auto_hold_scope():
  assert spv.LEGACY_VOLT_STOCK_ACC_CARS == {
    "CHEVROLET_VOLT",
    "CHEVROLET_VOLT_2019",
    "CHEVROLET_VOLT_ASCM",
    "CHEVROLET_VOLT_CAMERA",
  }


def test_tss2_toyota_keeps_main_aol_button_path():
  assert spv._lkas_allowed_for_aol("toyota", 0, []) is False


def test_hyundai_and_honda_keep_lkas_aol_button_path():
  assert spv._lkas_allowed_for_aol("honda", 0, []) is True
  assert spv._lkas_allowed_for_aol("hyundai", spv.HyundaiFlags.CANFD, []) is True


def test_ford_can_map_lkas_button_to_aol():
  assert spv._lkas_allowed_for_aol("ford", 0, []) is True


def test_explicit_main_cruise_aol_mapping_is_not_disabled_by_longitudinal_gate():
  aol_button = spv.BUTTON_FUNCTIONS["AOL_TOGGLE"]

  # An explicit Galaxy mapping remains valid on both longitudinal paths.
  assert spv._main_cruise_aol_allowed(aol_button) is True


def test_jeep_brake_hold_scope_is_grand_cherokee_only():
  assert {str(car) for car in spv.CHRYSLER_JEEPS} == {
    "JEEP_GRAND_CHEROKEE",
    "JEEP_GRAND_CHEROKEE_2019",
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


def test_get_starpilot_toggles_uses_persisted_force_torque_request(monkeypatch):
  params = SimpleNamespace(get_bool=lambda key: key == "ForceTorqueController")
  monkeypatch.setattr(spv.get_starpilot_toggles, "_params", params, raising=False)

  payload = '{"force_torque_controller": false}'
  toggles = spv.get_starpilot_toggles(
    {"starpilotPlan": SimpleNamespace(starpilotToggles=payload)},
    read_persisted_force_params=True,
  )

  assert toggles.force_torque_controller is True


def test_get_starpilot_toggles_realtime_path_does_not_read_persisted_force_params(monkeypatch):
  class UnexpectedParamsRead:
    def get_bool(self, key):
      raise AssertionError(f"unexpected persisted param read: {key}")

  monkeypatch.setattr(spv.get_starpilot_toggles, "_params", UnexpectedParamsRead(), raising=False)

  payload = '{"force_offroad": false, "force_onroad": true, "force_torque_controller": false}'
  toggles = spv.get_starpilot_toggles({"starpilotPlan": SimpleNamespace(starpilotToggles=payload)})

  assert toggles.force_offroad is False
  assert toggles.force_onroad is True
  assert toggles.force_torque_controller is False


def test_get_starpilot_toggles_uses_live_rivian_angle_request(monkeypatch):
  params = SimpleNamespace(get_bool=lambda key: key == "RivianAngleControl")
  monkeypatch.setattr(spv.get_starpilot_toggles, "_params", params, raising=False)

  payload = '{"rivian_angle_control": false}'
  toggles = spv.get_starpilot_toggles(
    {"starpilotPlan": SimpleNamespace(starpilotToggles=payload)},
    read_persisted_force_params=True,
  )

  assert toggles.rivian_angle_control is True


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

  def get(self, key):
    if key in self.floats:
      return self.floats[key]
    if key in self.ints:
      return self.ints[key]
    return self.bools.get(key)

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


def test_ford_lkas_default_migrates_from_experimental_to_aol_toggle():
  params = _FakeParams(ints={"LKASButtonControl": spv.BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"]})

  assert spv.migrate_ford_lkas_button_default("ford", params) is True
  assert params.get_int("LKASButtonControl") == spv.BUTTON_FUNCTIONS["AOL_TOGGLE"]
  assert params.get_bool(spv.FORD_LKAS_MIGRATION_KEY) is True

  params.put_int("LKASButtonControl", spv.BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"])
  assert spv.migrate_ford_lkas_button_default("ford", params) is False
  assert params.get_int("LKASButtonControl") == spv.BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"]


def test_ford_lkas_default_migration_preserves_custom_mapping():
  params = _FakeParams(ints={"LKASButtonControl": spv.BUTTON_FUNCTIONS["BOOKMARK"]})

  assert spv.migrate_ford_lkas_button_default("ford", params) is True
  assert params.get_int("LKASButtonControl") == spv.BUTTON_FUNCTIONS["BOOKMARK"]


def test_ford_lkas_default_migration_ignores_other_brands():
  params = _FakeParams(ints={"LKASButtonControl": spv.BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"]})

  assert spv.migrate_ford_lkas_button_default("honda", params) is False
  assert params.get_int("LKASButtonControl") == spv.BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"]
  assert params.get_bool(spv.FORD_LKAS_MIGRATION_KEY) is False


def test_sync_reboot_marker_uses_manager_guard(tmp_path):
  params = _FakeParams()
  marker = tmp_path / "cache" / "use_HD"

  assert spv.sync_reboot_marker(marker, True, params) is True
  assert marker.is_file()
  assert params.get_bool("DoReboot") is True

  params.put_bool("DoReboot", False)
  assert spv.sync_reboot_marker(marker, True, params) is False
  assert params.get_bool("DoReboot") is False

  assert spv.sync_reboot_marker(marker, False, params) is True
  assert not marker.exists()
  assert params.get_bool("DoReboot") is True


def test_sync_stock_param_does_not_stomp_existing_custom_value_when_stock_missing():
  params = _FakeParams({"SteerDelay": 0.35, "SteerDelayStock": 0.0})
  variables = object.__new__(spv.StarPilotVariables)
  variables.params = params

  variables._sync_stock_param("SteerDelay", "SteerDelayStock", 0.10)

  assert params.get_float("SteerDelay") == 0.35
  assert params.get_float("SteerDelayStock") == 0.10


def test_steer_delay_mode_migration_converts_untouched_stock_value_to_full_auto_delay():
  params = _FakeParams({"SteerDelay": 0.11, "SteerDelayStock": 0.11})
  variables = object.__new__(spv.StarPilotVariables)
  variables.params = params
  variables.params_raw = params

  variables._migrate_steer_delay_mode(0.11)

  assert params.get_bool("UseAutoSteerDelay") is True
  assert params.get_float("SteerDelay") == 0.31
  assert params.get_bool(spv.STEER_DELAY_MODE_MIGRATION_KEY) is True


def test_steer_delay_mode_migration_preserves_existing_manual_full_delay():
  params = _FakeParams({"SteerDelay": 0.35, "SteerDelayStock": 0.11})
  variables = object.__new__(spv.StarPilotVariables)
  variables.params = params
  variables.params_raw = params

  variables._migrate_steer_delay_mode(0.11)

  assert params.get_bool("UseAutoSteerDelay") is False
  assert params.get_float("SteerDelay") == 0.35
  assert params.get_bool(spv.STEER_DELAY_MODE_MIGRATION_KEY) is True


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


def test_runtime_values_ignore_legacy_tuning_level_metadata():
  params = _FakeParams(ints={"LKASButtonControl": spv.BUTTON_FUNCTIONS["AOL_TOGGLE"]})
  variables = object.__new__(spv.StarPilotVariables)
  variables.params = params
  variables.default_values = {"LKASButtonControl": str(spv.BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"])}

  assert variables.get_value("LKASButtonControl", cast=int) == spv.BUTTON_FUNCTIONS["AOL_TOGGLE"]
  assert variables.get_button_function("LKASButtonControl") == spv.BUTTON_FUNCTIONS["AOL_TOGGLE"]


def test_missing_bounded_value_uses_explicit_default():
  variables = object.__new__(spv.StarPilotVariables)
  variables.params = _FakeParams()
  variables.default_values = {}

  value = variables.get_value("LaneChangeCloseGapSeconds", cast=float, default=1.0, min=0.5, max=3.0)

  assert value == 1.0


def test_get_longitudinal_modes_is_mutually_exclusive():
  # Hybrid wins when selected and CEM/CCM params are off.
  assert spv.get_longitudinal_modes(True, False, False, True) == (False, False, True)
  # CEM takes priority over the other modes when enabled.
  assert spv.get_longitudinal_modes(True, True, True, True) == (True, False, False)
  # CCM engages only when CEM is off.
  assert spv.get_longitudinal_modes(True, False, True, False) == (False, True, False)
  assert spv.get_longitudinal_modes(True, False, True, True) == (False, True, False)
  # Nothing engages without openpilot longitudinal.
  assert spv.get_longitudinal_modes(False, True, True, True) == (False, False, False)


def test_disabled_conditional_experimental_toggles_are_off(monkeypatch, tmp_path):
  params_cls = spv.Params

  def isolated_params(_path=None, memory=False, return_defaults=False):
    return params_cls(str(tmp_path / ("memory" if memory else "params")), return_defaults=return_defaults)

  monkeypatch.setattr(spv, "Params", isolated_params)
  params = isolated_params()
  params.put_bool("ConditionalExperimental", True)
  params.put_bool("CEStopLights", False)
  params.put_float("CEModelStopTime", 0.0)

  variables = spv.StarPilotVariables()
  toggles = variables.starpilot_toggles

  assert variables.params_raw.get_float("CEModelStopTime") == 0.0
  assert toggles.conditional_experimental_mode is False
  assert toggles.conditional_curves is False
  assert toggles.conditional_curves_lead is False
  assert toggles.conditional_lead is False
  assert toggles.conditional_open_road is False
  assert toggles.conditional_slower_lead is False
  assert toggles.conditional_stopped_lead is False
  assert toggles.conditional_limit == 0.0
  assert toggles.conditional_limit_lead == 0.0
  assert toggles.conditional_model_stop_time == 0.0
  assert toggles.conditional_signal == 0.0
  assert toggles.conditional_signal_lane_detection is False


def test_device_shutdown_hours_convert_directly_to_seconds():
  assert spv.device_shutdown_seconds(6) == 6 * 60 * 60
  assert spv.device_shutdown_seconds(0) == 60 * 60
  assert spv.device_shutdown_seconds(31) == 30 * 60 * 60


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


def test_speed_limit_controller_available_on_openpilot_longitudinal_or_redneck():
  assert spv.speed_limit_controller_available(openpilot_longitudinal=True, redneck_cruise=False) is True
  assert spv.speed_limit_controller_available(openpilot_longitudinal=False, redneck_cruise=True) is True
  assert spv.speed_limit_controller_available(openpilot_longitudinal=False, redneck_cruise=False) is False
