from openpilot.common.params import ParamKeyType
from openpilot.starpilot.common.favorite_slots import (
  FAVORITE_SLOTS_PARAM,
  default_favorite_slots,
  load_favorite_slots,
  toggle_favorite_slot,
)


class FakeParams:
  def __init__(self):
    self.store = {}
    self.types = {
      FAVORITE_SLOTS_PARAM: ParamKeyType.JSON,
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

  def get_type(self, key):
    return self.types.get(key, ParamKeyType.STRING)


def test_load_favorite_slots_defaults_on_empty_payload():
  params = FakeParams()

  assert load_favorite_slots(params) == default_favorite_slots()


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
