import json

from openpilot.common.params import ParamKeyType
from openpilot.starpilot.common.favorite_slots import (
  FAVORITE_ACTION_ACCEL_COUNTER,
  FAVORITE_ACTION_DECEL_COUNTER,
  FAVORITE_ACTION_DISTANCE_DECREASE,
  FAVORITE_ACTION_DISTANCE_INCREASE,
  FAVORITE_ACTION_TRAFFIC_MODE_COUNTER,
  FAVORITE_ACTION_TOGGLE_TRAFFIC_MODE,
  FAVORITE_SLOTS_PARAM,
  SETTINGS_CATALOG_PATH,
  build_favorite_slot_options,
  default_favorite_slots,
  execute_favorite_key,
  filter_favorite_slot_options,
  load_settings_catalog,
  load_favorite_slots,
  save_favorite_slots,
  toggle_favorite_slot,
  unassign_favorite_slot,
)


class FakeParams:
  def __init__(self):
    self.store = {}
    self.types = {
      FAVORITE_SLOTS_PARAM: ParamKeyType.JSON,
      "AlphaLongitudinalEnabled": ParamKeyType.BOOL,
      "ForceOffroad": ParamKeyType.BOOL,
      "RedneckCruise": ParamKeyType.BOOL,
      "NotBool": ParamKeyType.INT,
    }

  def get(self, key):
    return self.store.get(key)

  def get_bool(self, key):
    return bool(self.store.get(key, False))

  def put(self, key, value):
    self.store[key] = value

  def put_bool(self, key, value):
    self.store[key] = bool(value)

  def put_bool_nonblocking(self, key, value):
    self.put_bool(key, value)

  def get_int(self, key, default=0):
    return int(self.store.get(key, default))

  def put_int(self, key, value):
    self.store[key] = int(value)

  def put_int_nonblocking(self, key, value):
    self.put_int(key, value)

  def put_nonblocking(self, key, value):
    self.put(key, value)

  def get_type(self, key):
    return self.types.get(key, ParamKeyType.STRING)


def test_load_favorite_slots_defaults_on_empty_payload():
  params = FakeParams()

  assert load_favorite_slots(params) == default_favorite_slots()


def test_shared_settings_catalog_is_common_and_well_formed():
  catalog = load_settings_catalog()

  assert SETTINGS_CATALOG_PATH.is_file()
  assert catalog is not None
  assert all(isinstance(section.get("params", []), list) for section in catalog)
  params = [
    param
    for section in catalog
    for param in section.get("params", [])
    if isinstance(param, dict) and param.get("key")
  ]
  assert all("favorite_eligible" not in param for param in params)

  options = build_favorite_slot_options(lambda _key: True, alpha_longitudinal_available=True)
  keys = [str(option["key"]) for option in options]
  assert len(keys) == len(set(keys))


def test_galaxy_only_ford_controls_are_not_available_to_device_favorites():
  ford_keys = {
    "FordHumanTurnDetection",
    "FordHandsFreeCluster",
  }

  options = build_favorite_slot_options(lambda _key: True, alpha_longitudinal_available=True)

  assert ford_keys.isdisjoint({option["key"] for option in options})


def test_load_favorite_slots_filters_non_bool_keys():
  params = FakeParams()
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "NotBool", "label": "Bad"},
    {"enabled": True, "show_onroad": False, "key": "RedneckCruise", "label": "Redneck Cruise"},
  ])

  slots = load_favorite_slots(params)

  assert slots[0]["key"] is None
  assert slots[0]["enabled"] is True
  assert slots[1]["key"] == "RedneckCruise"
  assert slots[1]["show_onroad"] is False


def test_save_and_toggle_favorite_slot_respect_available_catalog_keys():
  params = FakeParams()
  params.put("RedneckCruise", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "RedneckCruise", "label": "Redneck Cruise"},
    {"enabled": True, "show_onroad": True, "key": "ForceOffroad", "label": "Force Offroad"},
  ])

  eligible_keys = {"RedneckCruise"}
  saved = save_favorite_slots(params.get(FAVORITE_SLOTS_PARAM), params, eligible_keys=eligible_keys)

  assert saved[0]["key"] == "RedneckCruise"
  assert saved[1]["key"] is None
  assert toggle_favorite_slot(0, params, FakeParams(), eligible_keys=eligible_keys) is True
  assert toggle_favorite_slot(1, params, FakeParams(), eligible_keys=eligible_keys) is False


def test_toggle_favorite_slot_ignores_disabled_slot():
  params = FakeParams()
  params.put("RedneckCruise", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": False, "show_onroad": True, "key": "RedneckCruise", "label": "Redneck Cruise"},
  ])

  assert toggle_favorite_slot(0, params, FakeParams()) is False
  assert params.get_bool("RedneckCruise") is False


def test_toggle_favorite_slot_flips_bool_and_requests_refresh():
  params = FakeParams()
  memory = FakeParams()
  params.put("RedneckCruise", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": False, "key": "RedneckCruise", "label": "Redneck Cruise"},
  ])

  assert toggle_favorite_slot(0, params, memory) is True
  assert params.get_bool("RedneckCruise") is True
  assert memory.get_bool("StarPilotTogglesUpdated") is True


def test_execute_favorite_key_uses_same_dispatch_without_a_visible_slot():
  params = FakeParams()
  memory = FakeParams()
  params.put("RedneckCruise", False)

  assert execute_favorite_key("RedneckCruise", params, memory, eligible_keys={"RedneckCruise"}) is True
  assert params.get_bool("RedneckCruise") is True
  assert memory.get_bool("StarPilotTogglesUpdated") is True
  assert execute_favorite_key("NotBool", params, memory, eligible_keys={"RedneckCruise"}) is False


def test_toggle_favorite_slot_blocks_alpha_longitudinal_onroad():
  params = FakeParams()
  params.put("IsOnroad", True)
  params.put("AlphaLongitudinalEnabled", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "AlphaLongitudinalEnabled", "label": "Alpha Longitudinal"},
  ])

  assert toggle_favorite_slot(0, params, FakeParams()) is False
  assert params.get_bool("AlphaLongitudinalEnabled") is False


def test_toggle_favorite_slot_leaves_force_offroad_unrestricted():
  params = FakeParams()
  params.put("IsOnroad", True)
  params.put("ForceOffroad", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "ForceOffroad", "label": "Force Offroad"},
  ])

  assert toggle_favorite_slot(0, params, FakeParams()) is True
  assert params.get_bool("ForceOffroad") is True


def test_toggle_favorite_slot_action_increments_virtual_button_counter():
  params = FakeParams()
  memory = FakeParams()
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": FAVORITE_ACTION_DISTANCE_INCREASE, "label": "Distance + / RES"},
  ])

  assert toggle_favorite_slot(0, params, memory) is True
  assert memory.get_int(FAVORITE_ACTION_ACCEL_COUNTER) == 1


def test_toggle_favorite_slot_action_increments_traffic_mode_counter():
  params = FakeParams()
  memory = FakeParams()
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": FAVORITE_ACTION_TOGGLE_TRAFFIC_MODE, "label": "Toggle Traffic Mode"},
  ])

  assert toggle_favorite_slot(0, params, memory) is True
  assert memory.get_int(FAVORITE_ACTION_TRAFFIC_MODE_COUNTER) == 1


def test_shared_favorite_option_catalog_uses_layout_metadata_and_capability_gates(tmp_path):
  layout_path = tmp_path / "device_settings_layout.json"
  layout_path.write_text(json.dumps([
    {
      "name": "Testing",
      "params": [
        {
          "key": "FeatureToggle",
          "label": "Feature Toggle",
          "description": "Visible",
          "picker_description": "Compact",
          "ui_type": "toggle",
          "data_type": "bool",
        },
        {"key": "UnsupportedToggle", "label": "Unsupported", "ui_type": "toggle", "data_type": "bool"},
        {"key": "AlphaLongitudinalEnabled", "label": "Alpha", "ui_type": "toggle", "data_type": "bool"},
        {"key": "RivianAngleControl", "label": "Rivian", "ui_type": "toggle", "data_type": "bool", "requires_capability": "HasRivianAngleHarness"},
      ],
    },
  ]))

  options = build_favorite_slot_options(
    lambda key: key in {"FeatureToggle", "AlphaLongitudinalEnabled", "RivianAngleControl"},
    alpha_longitudinal_available=False,
    layout_path=layout_path,
  )

  assert FAVORITE_ACTION_DISTANCE_DECREASE in {option["key"] for option in options}
  assert {option["key"] for option in options} >= {"FeatureToggle", "RivianAngleControl"}
  feature_option = next(option for option in options if option["key"] == "FeatureToggle")
  assert feature_option["description"] == "Visible"
  assert feature_option["picker_description"] == "Compact"
  assert "UnsupportedToggle" not in {option["key"] for option in options}
  assert "AlphaLongitudinalEnabled" not in {option["key"] for option in options}
  assert "RivianAngleControl" not in {
    option["key"] for option in filter_favorite_slot_options(options, {"HasRivianAngleHarness": False})
  }
  assert "RivianAngleControl" in {
    option["key"] for option in filter_favorite_slot_options(options, {"HasRivianAngleHarness": True})
  }


def test_unassign_favorite_slot_resets_slot_and_notifies_memory():
  params = FakeParams()
  memory = FakeParams()
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "RedneckCruise", "label": "Redneck Cruise"},
    {"enabled": True, "show_onroad": True, "key": "ForceOffroad", "label": "Force Offroad"},
  ])

  result = unassign_favorite_slot(0, params, memory, eligible_keys={"RedneckCruise", "ForceOffroad"})

  assert result is not None
  assert result[0] == {"enabled": False, "show_onroad": False, "key": None, "label": ""}
  assert result[1]["key"] == "ForceOffroad"
  assert params.get(FAVORITE_SLOTS_PARAM)[0] == {"enabled": False, "show_onroad": False, "key": None, "label": ""}
  assert memory.get_bool("StarPilotTogglesUpdated") is True


def test_unassign_favorite_slot_invalid_index_returns_none():
  params = FakeParams()
  memory = FakeParams()

  assert unassign_favorite_slot(-1, params, memory) is None
  assert unassign_favorite_slot(3, params, memory) is None


def test_cycle_enum_parameter_int_and_string_modulo():
  from openpilot.starpilot.common.favorite_slots import cycle_enum_parameter

  params = FakeParams()
  memory = FakeParams()
  params.types["AccelerationProfile"] = ParamKeyType.INT
  params.put_int("AccelerationProfile", 0)

  options = [
    {"value": 0, "label": "Standard"},
    {"value": 1, "label": "Eco"},
    {"value": 2, "label": "Sport"},
    {"value": 3, "label": "Sport+"},
  ]

  # 0 -> 1
  assert cycle_enum_parameter("AccelerationProfile", params, memory, options=options) is True
  assert params.get_int("AccelerationProfile") == 1
  assert memory.get_bool("StarPilotTogglesUpdated") is True

  # 1 -> 2
  assert cycle_enum_parameter("AccelerationProfile", params, memory, options=options) is True
  assert params.get_int("AccelerationProfile") == 2

  # 2 -> 3
  assert cycle_enum_parameter("AccelerationProfile", params, memory, options=options) is True
  assert params.get_int("AccelerationProfile") == 3

  # 3 -> 0 (wrap around modulo)
  assert cycle_enum_parameter("AccelerationProfile", params, memory, options=options) is True
  assert params.get_int("AccelerationProfile") == 0


def test_toggle_favorite_slot_polymorphic_dispatch():
  params = FakeParams()
  memory = FakeParams()
  params.types["AccelerationProfile"] = ParamKeyType.INT
  params.put_int("AccelerationProfile", 1)
  params.put("RedneckCruise", False)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "AccelerationProfile", "label": "Acceleration Profile"},
    {"enabled": True, "show_onroad": True, "key": FAVORITE_ACTION_DISTANCE_DECREASE, "label": "Distance -"},
    {"enabled": True, "show_onroad": True, "key": "RedneckCruise", "label": "Redneck Cruise"},
  ])

  # Slot 0: Dropdown cycle
  assert toggle_favorite_slot(0, params, memory) is True
  assert params.get_int("AccelerationProfile") == 2

  # Slot 1: Virtual action
  assert toggle_favorite_slot(1, params, memory) is True
  assert memory.get_int(FAVORITE_ACTION_DECEL_COUNTER) == 1

  # Slot 2: Boolean toggle
  assert toggle_favorite_slot(2, params, memory) is True
  assert params.get_bool("RedneckCruise") is True


def test_onroad_safety_gating_blocks_critical_keys():
  params = FakeParams()
  memory = FakeParams()
  params.put("AlphaLongitudinalEnabled", False)
  params.put("IsOnroad", True)
  params.put(FAVORITE_SLOTS_PARAM, [
    {"enabled": True, "show_onroad": True, "key": "AlphaLongitudinalEnabled", "label": "Alpha Long"},
  ])

  # Gated while onroad
  assert toggle_favorite_slot(0, params, memory) is False
  assert params.get_bool("AlphaLongitudinalEnabled") is False

  # Allowed when offroad
  params.put("IsOnroad", False)
  assert toggle_favorite_slot(0, params, memory) is True
  assert params.get_bool("AlphaLongitudinalEnabled") is True


def test_get_favorite_param_value_and_get_favorite_values():
  from openpilot.starpilot.common.favorite_slots import (
    get_favorite_enum_state,
    get_favorite_param_value,
    get_favorite_values,
  )

  params = FakeParams()
  params.types["AccelerationProfile"] = ParamKeyType.INT
  params.put_int("AccelerationProfile", 2)
  params.put("RedneckCruise", True)

  catalog_map = {
    "AccelerationProfile": {
      "key": "AccelerationProfile",
      "ui_type": "dropdown",
      "data_type": "int",
      "options": [
        {"value": 0, "label": "Standard"},
        {"value": 1, "label": "Eco"},
        {"value": 2, "label": "Sport"},
      ],
    },
    "RedneckCruise": {
      "key": "RedneckCruise",
      "ui_type": "toggle",
      "data_type": "bool",
    },
  }

  assert get_favorite_param_value("AccelerationProfile", params, catalog_map=catalog_map) == 2
  assert get_favorite_param_value("RedneckCruise", params, catalog_map=catalog_map) is True
  assert get_favorite_param_value(FAVORITE_ACTION_DISTANCE_DECREASE, params) is None

  values = get_favorite_values([
    {"key": "AccelerationProfile"},
    {"key": "RedneckCruise"},
    {"key": FAVORITE_ACTION_DISTANCE_DECREASE},
  ], params)
  assert values["AccelerationProfile"] == 2
  assert values["RedneckCruise"] is True
  assert FAVORITE_ACTION_DISTANCE_DECREASE not in values

  curr_val, active_idx, active_label, opts = get_favorite_enum_state("AccelerationProfile", params, catalog_map=catalog_map)
  assert curr_val == 2
  assert active_idx == 2
  assert active_label == "Sport"
  assert len(opts) == 3
